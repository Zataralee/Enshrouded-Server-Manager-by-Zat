import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("eml_stable_release_test", ROOT / "enshrouded_manager/manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
from eml_support import EML_SHA256


class EMLStableReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name)
        self.eml = mock.Mock()
        self.eml.status.return_value = {"enabled": True, "patched": False, "recovery_required": False}
        for patch in [mock.patch.object(manager, "instances", return_value=[{"id": "modded"}]),
                      mock.patch.object(manager, "eml_for_instance", return_value=self.eml)]:
            patch.start()
            self.addCleanup(patch.stop)

    def target_files(self):
        (self.target / "eml_support.py").write_text("# EML integration")
        tool = self.target / "vendor/eml-v0.2.0/emm.exe"
        tool.parent.mkdir(parents=True)
        tool.write_bytes(b"synthetic executable; never run")

    def test_active_mods_can_move_to_verified_eml_capable_stable_package(self):
        self.target_files()
        with mock.patch("eml_support.digest", return_value=EML_SHA256) as digest:
            manager.validate_eml_update_target(self.target)
        digest.assert_called_once()

    def test_target_without_eml_cannot_remove_active_integration(self):
        with self.assertRaisesRegex(RuntimeError, "does not include EML"):
            manager.validate_eml_update_target(self.target)

    def test_tampered_target_loader_is_rejected(self):
        self.target_files()
        with mock.patch("eml_support.digest", return_value="bad"), self.assertRaisesRegex(RuntimeError, "SHA-256"):
            manager.validate_eml_update_target(self.target)

    def test_unmodded_server_does_not_require_eml_in_target(self):
        self.eml.status.return_value = {"enabled": False, "patched": False, "recovery_required": False}
        manager.validate_eml_update_target(self.target)

    def test_fresh_stable_defaults_to_stable_channel(self):
        with mock.patch.object(manager, "APP_VERSION", "0.9.6.5a"):
            self.assertEqual("stable", manager.default_manager_updates()["channel"])
        with mock.patch.object(manager, "APP_VERSION", "0.9.6.5b"):
            self.assertEqual("beta", manager.default_manager_updates()["channel"])


if __name__ == "__main__":
    unittest.main()
