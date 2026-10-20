import importlib.util
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("steamcmd_recovery_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
STUCK = "Error! App '2278520' state is 0x6 after update job."
SUCCESS = "Success! App '2278520' fully installed."


class SteamCMDRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG
        manager.DATA_DIR = self.root / "data"
        manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
        manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
        self.server = self.root / "server"
        self.steamapps = self.server / "steamapps"
        self.steamapps.mkdir(parents=True)
        cfg = manager.default_config()
        self.instance = manager.default_instance("Recovery Test", self.server)
        cfg["instances"] = [self.instance]
        cfg["selected_instance_id"] = self.instance["id"]
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        self.exe = self.root / "Steamcmd" / "steamcmd.exe"
        self.exe.parent.mkdir()
        self.ensure = mock.patch.object(manager, "ensure_steamcmd", return_value=self.exe).start()
        mock.patch.object(manager, "prepare_steamcmd").start()
        self.notify = mock.patch.object(manager, "notify_webhook_event").start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(self.restore_paths)

    def restore_paths(self):
        manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = self.paths
        manager.SUPERVISORS.clear()
        self.temp.cleanup()

    def manifests(self):
        for app_id in ("2278520", "228980"):
            (self.steamapps / f"appmanifest_{app_id}.acf").write_text(f"original {app_id}", encoding="utf-8")

    def result(self, text, code=0):
        def run(command, **options):
            options["stdout"].write(text.encode("utf-8"))
            options["stdout"].flush()
            return subprocess.CompletedProcess(command, code)
        return run

    def test_stuck_update_backs_up_only_instance_manifests_and_recovers(self):
        self.manifests()
        save = self.server / "savegame" / "world"
        save.parent.mkdir()
        save.write_bytes(b"world data")
        config = self.server / "enshrouded_server.json"
        config.write_text("{}", encoding="utf-8")
        shared = self.exe.parent / "steamapps" / "appmanifest_2278520.acf"
        shared.parent.mkdir()
        shared.write_bytes(b"shared manifest")
        attempts = 0

        def run(command, **options):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return self.result(STUCK, 8)(command, **options)
            self.assertFalse((self.steamapps / "appmanifest_2278520.acf").exists())
            self.assertFalse((self.steamapps / "appmanifest_228980.acf").exists())
            (self.steamapps / "appmanifest_2278520.acf").write_text("fresh manifest", encoding="utf-8")
            return self.result(SUCCESS)(command, **options)

        with mock.patch.object(manager.subprocess, "run", side_effect=run):
            manager.run_update(self.instance["id"])

        backups = sorted((self.steamapps / "esm-manifest-backups").glob("*/*.acf"))
        self.assertEqual(2, len(backups))
        self.assertEqual({"original 2278520", "original 228980"}, {path.read_text() for path in backups})
        self.assertEqual("fresh manifest", (self.steamapps / "appmanifest_2278520.acf").read_text())
        self.assertEqual(b"world data", save.read_bytes())
        self.assertEqual("{}", config.read_text())
        self.assertEqual(b"shared manifest", shared.read_bytes())
        self.assertEqual(2, attempts)
        saved = manager.get_instance(self.instance["id"])
        self.assertEqual("", saved["last_update_warning"])
        self.assertTrue(saved["last_updated_at"])
        self.notify.assert_called_once_with("server.updated", self.instance["id"], message="Update check completed for Recovery Test.")
        output = (self.server / "logs" / "esm-steamcmd.log").read_text()
        self.assertIn(STUCK, output)
        self.assertIn(SUCCESS, output)

    def test_failed_retry_restores_missing_manifests_and_does_not_record_success(self):
        self.manifests()
        with mock.patch.object(manager.subprocess, "run", side_effect=self.result(STUCK, 8)) as run:
            with self.assertRaisesRegex(manager.SteamCMDUpdateError, "state is 0x6"):
                manager.run_update(self.instance["id"])
        self.assertEqual(2, run.call_count)
        self.assertEqual("original 2278520", (self.steamapps / "appmanifest_2278520.acf").read_text())
        self.assertEqual("original 228980", (self.steamapps / "appmanifest_228980.acf").read_text())
        saved = manager.get_instance(self.instance["id"])
        self.assertEqual("", saved["last_updated_at"])
        self.assertIn("esm-steamcmd.log", saved["last_update_warning"])
        self.assertEqual("server.update.failed", self.notify.call_args.args[0])

    def test_other_failures_do_not_reset_manifests_or_retry(self):
        self.manifests()
        for output in ("Error! App '2278520' state is 0x606 after update job.",
                       "Error! App '1007' state is 0x6 after update job.", "Connection failed"):
            with self.subTest(output=output), \
                    mock.patch.object(manager.subprocess, "run", side_effect=self.result(output, 8)) as run:
                with self.assertRaises(manager.SteamCMDUpdateError):
                    manager.run_update(self.instance["id"])
                self.assertEqual(1, run.call_count)
                self.assertFalse((self.steamapps / "esm-manifest-backups").exists())

    def test_zero_exit_with_error_is_not_treated_as_updated(self):
        with mock.patch.object(manager.subprocess, "run", side_effect=self.result("Error! Failed to install app 2278520 (Disk write failure)")):
            with self.assertRaisesRegex(manager.SteamCMDUpdateError, "Disk write failure"):
                manager.run_update(self.instance["id"])
        self.assertEqual("", manager.get_instance(self.instance["id"])["last_updated_at"])

    def test_already_up_to_date_is_successful(self):
        with mock.patch.object(manager.subprocess, "run", side_effect=self.result("Success! App '2278520' already up to date.")) as run:
            manager.run_update(self.instance["id"])
        self.assertEqual(1, run.call_count)
        self.assertTrue(manager.get_instance(self.instance["id"])["last_updated_at"])

    def test_old_success_in_log_cannot_hide_a_later_failure(self):
        log_path = self.server / "logs" / "esm-steamcmd.log"
        with mock.patch.object(manager.subprocess, "run", side_effect=self.result(SUCCESS)):
            manager.steamcmd_update_attempt([str(self.exe)], log_path)
        with mock.patch.object(manager.subprocess, "run", side_effect=self.result("Connection failed")):
            with self.assertRaises(manager.SteamCMDUpdateError):
                manager.steamcmd_update_attempt([str(self.exe)], log_path)

    def test_partial_manifest_backup_failure_restores_the_first_manifest(self):
        self.manifests()
        rename = Path.rename

        def move(path, destination):
            if path.name == "appmanifest_228980.acf":
                raise PermissionError("manifest is locked")
            return rename(path, destination)

        with mock.patch.object(Path, "rename", autospec=True, side_effect=move):
            with self.assertRaises(PermissionError):
                manager.reset_instance_steam_manifests(self.instance["id"])
        self.assertEqual("original 2278520", (self.steamapps / "appmanifest_2278520.acf").read_text())
        self.assertEqual("original 228980", (self.steamapps / "appmanifest_228980.acf").read_text())

    def test_prestart_update_recovers_and_then_launches_server(self):
        self.manifests()
        executable = self.server / "enshrouded_server.exe"
        executable.write_bytes(b"test executable")
        supervisor = manager.supervisor(self.instance["id"])
        process = mock.Mock(pid=4321)
        process.poll.return_value = None
        attempts = 0

        def run(command, **options):
            nonlocal attempts
            attempts += 1
            return self.result(STUCK if attempts == 1 else SUCCESS, 8 if attempts == 1 else 0)(command, **options)

        with mock.patch.object(manager.subprocess, "run", side_effect=run), \
                mock.patch.object(manager.subprocess, "Popen", return_value=process) as popen, \
                mock.patch.object(manager, "validate_instance_can_start"), \
                mock.patch.object(manager, "server_launch_spec", create=True, return_value={
                    "command": [str(executable)], "env": None, "runtime": "windows-native",
                }), \
                mock.patch.object(manager.time, "sleep"):
            supervisor.start(update_first=True)
        self.assertEqual(2, attempts)
        popen.assert_called_once()
        saved = manager.get_instance(self.instance["id"])
        self.assertTrue(saved["desired_running"])
        self.assertEqual("", saved["last_update_warning"])
        self.assertEqual(["server.updated", "server.started"], [call.args[0] for call in self.notify.call_args_list])

    def test_running_server_is_rejected_before_update_or_recovery(self):
        self.manifests()
        with mock.patch.object(manager, "supervisor") as sup:
            sup.return_value.status.return_value = {"running": True}
            with self.assertRaisesRegex(RuntimeError, "Stop this server"):
                manager.run_update(self.instance["id"])
        self.ensure.assert_not_called()
        self.assertFalse((self.steamapps / "esm-manifest-backups").exists())

    def test_two_requests_do_not_run_steamcmd_concurrently(self):
        entered = threading.Event()
        release = threading.Event()
        second_waiting = threading.Event()
        errors = []
        count = 0
        guard = threading.Lock()

        def run(command, **options):
            nonlocal count
            with guard:
                count += 1
                self.assertEqual(1, count)
            entered.set()
            self.assertTrue(release.wait(5))
            result = self.result(SUCCESS)(command, **options)
            with guard:
                count -= 1
            return result

        def worker():
            try:
                manager.run_update(self.instance["id"], status=lambda text: second_waiting.set() if text.startswith("Waiting") else None)
            except Exception as exc:
                errors.append(exc)

        with mock.patch.object(manager.subprocess, "run", side_effect=run):
            first = threading.Thread(target=worker)
            second = threading.Thread(target=worker)
            first.start()
            try:
                self.assertTrue(entered.wait(5))
                second_waiting.clear()
                second.start()
                self.assertTrue(second_waiting.wait(5))
            finally:
                release.set()
                first.join(5)
                if second.ident:
                    second.join(5)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual([], errors)

    def test_output_capture_with_real_subprocess(self):
        log_path = self.server / "logs" / "esm-steamcmd.log"
        manager.steamcmd_update_attempt([sys.executable, "-c", f"print({SUCCESS!r})"], log_path)
        self.assertIn(SUCCESS, log_path.read_text())


if __name__ == "__main__":
    unittest.main()
