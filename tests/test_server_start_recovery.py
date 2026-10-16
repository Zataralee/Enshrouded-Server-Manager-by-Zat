import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manager_start_recovery_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class ServerStartRecoveryTests(unittest.TestCase):
    def test_failed_update_before_start_stops_retrying_and_records_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            server = temp / "server"
            server.mkdir()
            original = (manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
            manager.DATA_DIR = temp / "data"
            manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
            manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
            try:
                cfg = manager.default_config()
                instance = manager.default_instance("Update Failure", server)
                instance["desired_running"] = True
                instance["update_before_start"] = True
                cfg["instances"] = [instance]
                cfg["selected_instance_id"] = instance["id"]
                manager.save_json(manager.MANAGER_CONFIG, cfg)
                supervisor = manager.ServerSupervisor(instance["id"])

                update_error = subprocess.CalledProcessError(8, ["steamcmd"])
                with mock.patch.object(manager, "run_update", side_effect=update_error), \
                        mock.patch.object(manager, "notify_webhook_event"):
                    with self.assertRaisesRegex(RuntimeError, "SteamCMD exited with code 8"):
                        supervisor.start(update_first=True)

                saved = manager.get_instance(instance["id"])
                self.assertFalse(saved["desired_running"])
                self.assertIn("Disable update before start", saved["last_start_error"])
                self.assertEqual("idle", supervisor.status()["activity"])
            finally:
                manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = original

    def test_monitor_iteration_continues_after_one_server_fails(self):
        instances = [
            {"id": "broken", "name": "Broken Server"},
            {"id": "healthy", "name": "Healthy Server"},
        ]
        broken = mock.Mock()
        broken.monitor_once.side_effect = RuntimeError("update failed")
        healthy = mock.Mock()
        supervisors = {"broken": broken, "healthy": healthy}

        with mock.patch.object(manager, "instances", return_value=instances), \
                mock.patch.object(manager, "supervisor", side_effect=lambda instance_id: supervisors[instance_id]), \
                mock.patch.object(manager, "check_manager_updates"), \
                mock.patch.object(manager, "scheduled_restart_check") as restart_check, \
                mock.patch.object(manager, "scheduled_backup_check") as backup_check, \
                mock.patch.object(manager, "write_log") as write_log:
            manager.monitor_iteration()

        healthy.monitor_once.assert_called_once_with()
        restart_check.assert_called_once_with("healthy")
        backup_check.assert_called_once_with("healthy")
        self.assertIn("Broken Server", write_log.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
