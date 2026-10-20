import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_bootstrap_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
READY = "Steam Console Client (c) Valve Corporation\nLoading Steam API...OK\nUnloading Steam API...OK\n"
LOCALIZE = 'ILocalize::AddFile() failed to load file "public/steambootstrapper_english.txt".'
SUCCESS = "Success! App '2278520' fully installed."


class InstallBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG
        manager.DATA_DIR = self.root / "data"
        manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
        manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
        self.exe = self.root / "Steamcmd" / "steamcmd.exe"
        self.exe.parent.mkdir()
        self.log = self.root / "server" / "logs" / "esm-steamcmd.log"
        cfg = manager.default_config()
        cfg["server_root"] = str(self.root / "Servers")
        cfg["instances"] = []
        cfg["selected_instance_id"] = ""
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        self.user = {"id": "admin", "username": "admin", "role": "admin"}
        self.addCleanup(self.restore)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(manager, "detect_existing_instance").start()
        mock.patch.object(manager, "notify_webhook_event").start()
        mock.patch.object(manager.time, "sleep").start()

    def restore(self):
        manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = self.paths
        manager.JOBS.clear()
        manager.SUPERVISORS.clear()
        self.temp.cleanup()

    def response(self, output, code=0):
        def run(command, **options):
            options["stdout"].write(output.encode())
            options["stdout"].flush()
            return subprocess.CompletedProcess(command, code)
        return run

    def inline_thread(self, target, **options):
        return SimpleNamespace(start=target)

    def test_fresh_bootstrap_exit_seven_is_relaunched_until_ready(self):
        responses = iter([(LOCALIZE + "\nUpdate complete, launching...", 7), (READY, 0)])

        def run(command, **options):
            self.assertEqual([str(self.exe), "+quit"], command)
            return self.response(*next(responses))(command, **options)

        status = mock.Mock()
        with mock.patch.object(manager.subprocess, "run", side_effect=run) as process:
            manager.prepare_steamcmd(self.exe, self.log, status=status)
        self.assertEqual(2, process.call_count)
        self.assertIn("Initializing SteamCMD (2/3)", status.call_args.args[0])
        self.assertIn(LOCALIZE, self.log.read_text())

    def test_bootstrap_retries_are_bounded(self):
        with mock.patch.object(manager.subprocess, "run", side_effect=self.response(LOCALIZE, 7)) as process:
            with self.assertRaisesRegex(manager.SteamCMDUpdateError, "initialization failed"):
                manager.prepare_steamcmd(self.exe, self.log)
        self.assertEqual(3, process.call_count)

    def test_fatal_error_is_reported_instead_of_localization_warning(self):
        output = "[----] !!! Fatal Error: Steamcmd needs to be online to update.\n" + LOCALIZE
        with mock.patch.object(manager.subprocess, "run", side_effect=self.response(output, 1)) as process:
            with self.assertRaises(manager.SteamCMDUpdateError) as caught:
                manager.prepare_steamcmd(self.exe, self.log)
        self.assertIn("needs to be online", str(caught.exception))
        self.assertNotIn("ILocalize", str(caught.exception))
        self.assertEqual(1, process.call_count)

    def test_zero_exit_without_client_ready_is_not_accepted(self):
        with mock.patch.object(manager.subprocess, "run", side_effect=self.response("Checking for updates...")) as process:
            with self.assertRaises(manager.SteamCMDUpdateError):
                manager.prepare_steamcmd(self.exe, self.log)
        self.assertEqual(3, process.call_count)

    def test_new_bootstrap_log_diagnostics_are_copied_but_old_errors_are_not(self):
        bootstrap = self.exe.parent / "logs" / "bootstrap_log.txt"
        bootstrap.parent.mkdir()
        bootstrap.write_text("old unrelated error\n")

        def run(command, **options):
            with bootstrap.open("a") as output:
                output.write("Error: Directory not writable.\n")
            return self.response(LOCALIZE, 7)(command, **options)

        with mock.patch.object(manager.subprocess, "run", side_effect=run):
            code, output = manager.steamcmd_execute([str(self.exe), "+quit"], self.log, stage="bootstrap")
        self.assertEqual(7, code)
        self.assertIn("Directory not writable", output)
        self.assertNotIn("old unrelated error", output)
        self.assertIn("bootstrap_log.txt", self.log.read_text())

    def test_bootstrap_timeout_has_a_bounded_actionable_error(self):
        with mock.patch.object(manager.subprocess, "run", side_effect=subprocess.TimeoutExpired([str(self.exe)], 180)) as process:
            with self.assertRaisesRegex(RuntimeError, "bootstrap timed out after 180"):
                manager.prepare_steamcmd(self.exe, self.log)
        self.assertEqual(180, process.call_args.kwargs["timeout"])

    def test_game_exit_seven_reinitializes_then_requires_actual_install_success(self):
        responses = iter([(LOCALIZE, 7), (READY, 0), (SUCCESS, 0)])

        def run(command, **options):
            return self.response(*next(responses))(command, **options)

        command = manager.steamcmd_update_command(self.exe, self.root / "server")
        with mock.patch.object(manager.subprocess, "run", side_effect=run) as process:
            manager.steamcmd_update_after_bootstrap(command, self.log)
        self.assertEqual([command, [str(self.exe), "+quit"], command], [call.args[0] for call in process.call_args_list])

    def test_fresh_server_install_bootstraps_before_game_download(self):
        responses = iter([(LOCALIZE, 7), (READY, 0), (SUCCESS, 0)])

        def run(command, **options):
            if "+app_update" in command:
                server = Path(command[command.index("+force_install_dir") + 1])
                (server / "enshrouded_server.exe").write_bytes(b"test executable")
            return self.response(*next(responses))(command, **options)

        with mock.patch.object(manager, "ensure_steamcmd", return_value=self.exe), \
                mock.patch.object(manager.subprocess, "run", side_effect=run) as process, \
                mock.patch.object(manager, "generate_initial_server_config"), \
                mock.patch.object(manager.threading, "Thread", side_effect=self.inline_thread):
            job_id = manager.start_install_job({"name": "Fresh Server", "queryPort": 15647}, self.user)
        job = manager.get_job(job_id)
        self.assertEqual("complete", job["status"])
        self.assertEqual("ready", manager.get_instance(job["instance_id"])["installation_status"])
        self.assertEqual([str(self.exe), "+quit"], process.call_args_list[0].args[0])
        self.assertEqual([str(self.exe), "+quit"], process.call_args_list[1].args[0])
        self.assertIn("+app_update", process.call_args_list[2].args[0])
        self.assertEqual(15647, manager.load_json(manager.instance_config_path(job["instance_id"]), {})["queryPort"])

    def test_failed_install_retry_reuses_instance_and_preserves_owner_limits(self):
        with mock.patch.object(manager, "run_update", side_effect=RuntimeError("bootstrap failed")), \
                mock.patch.object(manager.threading, "Thread", side_effect=self.inline_thread):
            failed_id = manager.start_install_job({"name": "Retry Server", "queryPort": 15647}, self.user)
        failed = manager.get_job(failed_id)
        instance = manager.get_instance(failed["instance_id"])
        self.assertEqual("failed", instance["installation_status"])
        self.assertEqual(15647, manager.public_instance(instance)["query_port"])

        with mock.patch.object(manager, "run_update"), \
                mock.patch.object(manager, "generate_initial_server_config"), \
                mock.patch.object(manager, "check_server_creation_allowed", side_effect=AssertionError("Retry must not consume another server allocation")), \
                mock.patch.object(manager.threading, "Thread", side_effect=self.inline_thread):
            retry_id = manager.start_install_job({}, self.user, retry_instance_id=instance["id"])
        self.assertEqual("complete", manager.get_job(retry_id)["status"])
        self.assertEqual(instance["id"], manager.get_job(retry_id)["instance_id"])
        self.assertEqual(instance["path"], manager.get_instance(instance["id"])["path"])
        self.assertEqual(1, len(manager.instances()))

    def test_retry_does_not_target_another_visible_server_when_id_is_unknown(self):
        manager.add_instance("Mine", self.root / "server", owner_user_id="owner")
        owner = {"id": "owner", "role": "server_owner", "permissions": ["setup"]}
        with self.assertRaises(PermissionError):
            manager.start_install_job({}, owner, retry_instance_id="somebody-else")
        self.assertEqual({}, manager.JOBS)

    def test_second_install_job_for_same_instance_is_rejected(self):
        with mock.patch.object(manager.threading, "Thread"):
            job_id = manager.start_install_job({"name": "Pending Server", "queryPort": 15647}, self.user)
            with self.assertRaisesRegex(ValueError, "already has an install"):
                manager.start_install_job({}, self.user, retry_instance_id=manager.get_job(job_id)["instance_id"])

    def test_interrupted_install_can_be_retried_after_manager_restart(self):
        instance = manager.add_instance("Interrupted", self.root / "server")
        (self.root / "server" / "enshrouded_server.exe").write_bytes(b"partially installed")
        manager.update_instance_metadata(instance["id"], installation_status="installing")
        self.assertEqual("failed", manager.public_instance(manager.get_instance(instance["id"]))["installation_status"])
        with mock.patch.object(manager.threading, "Thread"):
            job_id = manager.start_install_job({}, self.user, retry_instance_id=instance["id"])
        self.assertEqual(instance["id"], manager.get_job(job_id)["instance_id"])

    def test_successful_background_polling_is_quiet(self):
        handler = manager.Handler.__new__(manager.Handler)
        handler.command = "GET"
        handler.path = "/api/jobs?id=example"
        with mock.patch.object(manager.SimpleHTTPRequestHandler, "log_request") as log:
            handler.log_request(200)
        log.assert_not_called()

    def test_failed_polling_and_user_actions_still_log(self):
        handler = manager.Handler.__new__(manager.Handler)
        with mock.patch.object(manager.SimpleHTTPRequestHandler, "log_request") as log:
            handler.command = "GET"
            handler.path = "/api/jobs?id=example"
            handler.log_request(500)
            handler.command = "POST"
            handler.path = "/api/instances/retry-install"
            handler.log_request(200)
        self.assertEqual(2, log.call_count)


if __name__ == "__main__":
    unittest.main()
