import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manager_linux_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class LinuxRuntimeTests(unittest.TestCase):
    def test_linux_steamcmd_requests_windows_server_depot(self):
        with mock.patch.object(manager, "IS_WINDOWS", False):
            command = manager.steamcmd_update_command(Path("/tmp/steamcmd.sh"), Path("/tmp/server"))

        self.assertIn("+@sSteamCmdForcePlatformType", command)
        self.assertEqual(command[command.index("+@sSteamCmdForcePlatformType") + 1], "windows")
        self.assertLess(command.index("+force_install_dir"), command.index("+login"))

    def test_windows_steamcmd_command_remains_unchanged(self):
        with mock.patch.object(manager, "IS_WINDOWS", True):
            command = manager.steamcmd_update_command(Path("C:/SteamCMD/steamcmd.exe"), Path("C:/Servers/Test"))

        self.assertNotIn("+@sSteamCmdForcePlatformType", command)
        self.assertEqual(command[-4:], ["+app_update", manager.APP_ID, "validate", "+quit"])

    def test_linux_release_asset_does_not_select_windows_zip(self):
        release = {
            "assets": [
                {"name": "ESM-Z-PythonRequired-v0.10.0.zip"},
                {"name": "ESM-Z-Linux-PythonRequired-v0.10.0-alpha.1.tar.gz"},
            ]
        }

        selected = manager.find_release_asset(release, platform_name="linux")

        self.assertEqual("ESM-Z-Linux-PythonRequired-v0.10.0-alpha.1.tar.gz", selected["name"])

    def test_linux_update_check_can_select_prerelease_asset(self):
        releases = [
            {"tag_name": "v0.10.0-linux-alpha.1", "draft": False, "assets": [{"name": "ESM-Z-Linux-PythonRequired-v0.10.0-linux-alpha.1.tar.gz"}]},
            {"tag_name": "v0.9.1", "draft": False, "assets": [{"name": "ESM-Z-PythonRequired-v0.9.1.zip"}]},
        ]
        with mock.patch.object(manager, "IS_WINDOWS", False), mock.patch.object(manager, "github_json", return_value=releases):
            selected = manager.latest_release_for_host("owner/repo")

        self.assertEqual("v0.10.0-linux-alpha.1", selected["tag_name"])

    def test_alpha_revision_can_update_without_appearing_newer_than_stable(self):
        self.assertTrue(manager.is_newer_version("0.10.0-linux-alpha.2", "0.10.0-linux-alpha.1"))
        self.assertTrue(manager.is_newer_version("0.10.0", "0.10.0-linux-alpha.2"))

    def test_configured_proton_builds_isolated_launch_spec(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            proton = temp / "Steam" / "steamapps" / "common" / "Proton Experimental" / "proton"
            proton.parent.mkdir(parents=True)
            proton.write_text("#!/bin/sh\n", encoding="utf-8")
            server = temp / "Servers" / "test"
            server.mkdir(parents=True)
            (server / "enshrouded_server.exe").touch()

            original = (manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
            manager.DATA_DIR = temp / "data"
            manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
            manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
            try:
                with mock.patch.object(manager, "IS_WINDOWS", False), \
                        mock.patch.object(manager, "discover_proton_executable", return_value=None), \
                        mock.patch.object(manager, "discover_wine_executable", return_value=None):
                    cfg = manager.default_config()
                    cfg["linux_runtime"] = "proton"
                    cfg["linux_runtime_path"] = str(proton)
                    instance = manager.default_instance("Test", server)
                    cfg["instances"] = [instance]
                    cfg["selected_instance_id"] = instance["id"]
                    manager.save_json(manager.MANAGER_CONFIG, cfg)

                    spec = manager.server_launch_spec(instance["id"])
            finally:
                manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = original

        self.assertEqual("proton", spec["runtime"])
        self.assertEqual([str(proton.resolve()), "run", str((server / "enshrouded_server.exe").resolve())], spec["command"])
        self.assertTrue(spec["start_new_session"])
        self.assertIn("linux-runtime", spec["env"]["STEAM_COMPAT_DATA_PATH"])
        self.assertEqual(str((temp / "Steam").resolve()), spec["env"]["STEAM_COMPAT_CLIENT_INSTALL_PATH"])


if __name__ == "__main__":
    unittest.main()
