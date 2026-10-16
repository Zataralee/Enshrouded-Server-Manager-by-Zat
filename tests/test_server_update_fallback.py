import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "enshrouded_manager" / "manager.py"
SPEC = importlib.util.spec_from_file_location("server_update_fallback_test_module", MODULE_PATH)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class FakeProcess:
    pid = 4321

    def poll(self):
        return None


class ServerUpdateFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.original_paths = (manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
        manager.DATA_DIR = self.temp_path / "data"
        manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
        manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"

        self.server_dir = self.temp_path / "server"
        self.server_dir.mkdir()
        (self.server_dir / "enshrouded_server.exe").write_bytes(b"test executable")
        instance = manager.default_instance("Test Server", self.server_dir)
        cfg = manager.default_config()
        cfg["instances"] = [instance]
        cfg["selected_instance_id"] = instance["id"]
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        self.instance_id = instance["id"]

    def tearDown(self):
        manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = self.original_paths
        self.temp_dir.cleanup()

    def test_failed_prestart_update_warns_and_starts_existing_server(self):
        supervisor = manager.ServerSupervisor(self.instance_id)
        update_error = subprocess.CalledProcessError(8, ["steamcmd", "+app_update"])

        with mock.patch.object(manager, "run_update", side_effect=update_error), \
                mock.patch.object(manager, "validate_instance_can_start"), \
                mock.patch.object(manager, "notify_webhook_event") as notify, \
                mock.patch.object(manager.subprocess, "Popen", return_value=FakeProcess()) as popen, \
                mock.patch.object(manager.time, "sleep"):
            supervisor.start(update_first=True)

        instance = manager.get_instance(self.instance_id)
        self.assertTrue(instance["desired_running"])
        self.assertEqual(4321, instance["pid"])
        self.assertIn("SteamCMD exited with code 8", instance["last_update_warning"])
        self.assertTrue(popen.called)
        notify.assert_called_once_with("server.started", self.instance_id, message="Test Server started.")

    def test_manual_update_failure_is_still_reported(self):
        steamcmd = self.temp_path / "steamcmd" / "steamcmd.exe"
        steamcmd.parent.mkdir()
        steamcmd.write_bytes(b"test executable")
        update_error = subprocess.CalledProcessError(8, [str(steamcmd), "+app_update"])

        with mock.patch.object(manager, "ensure_steamcmd", return_value=steamcmd), \
                mock.patch.object(manager, "steamcmd_update_attempt", side_effect=update_error), \
                mock.patch.object(manager, "notify_webhook_event"):
            with self.assertRaises(subprocess.CalledProcessError):
                manager.run_update(self.instance_id)

    def test_successful_update_clears_previous_warning(self):
        manager.update_instance_metadata(self.instance_id, last_update_warning="old warning")
        steamcmd = self.temp_path / "steamcmd" / "steamcmd.exe"
        steamcmd.parent.mkdir()
        steamcmd.write_bytes(b"test executable")

        with mock.patch.object(manager, "ensure_steamcmd", return_value=steamcmd), \
                mock.patch.object(manager, "steamcmd_update_attempt"), \
                mock.patch.object(manager, "notify_webhook_event"):
            manager.run_update(self.instance_id)

        instance = manager.get_instance(self.instance_id)
        self.assertEqual("", instance["last_update_warning"])
        self.assertTrue(instance["last_updated_at"])


if __name__ == "__main__":
    unittest.main()
