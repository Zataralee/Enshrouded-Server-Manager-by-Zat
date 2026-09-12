import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manager_branding_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class BrandingReleaseTests(unittest.TestCase):
    def test_primary_esm_z_asset_is_preferred_over_legacy_asset(self):
        release = {
            "assets": [
                {"name": "EnshroudedServerManager-PythonRequired-v0.9.1.zip"},
                {"name": "ESM-Z-PythonRequired-v0.9.1.zip"},
            ]
        }

        selected = manager.find_release_asset(release, platform_name="windows")

        self.assertEqual("ESM-Z-PythonRequired-v0.9.1.zip", selected["name"])

    def test_legacy_release_asset_remains_supported(self):
        release = {
            "assets": [
                {"name": "EnshroudedServerManager-PythonRequired-v0.9.1.zip"},
            ]
        }

        selected = manager.find_release_asset(release, platform_name="windows")

        self.assertEqual("EnshroudedServerManager-PythonRequired-v0.9.1.zip", selected["name"])

    def test_web_page_uses_esm_z_branding(self):
        page = (ROOT / "enshrouded_manager" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("<title>ESM-Z</title>", page)
        self.assertIn("<h1>ESM-Z</h1>", page)
        self.assertIn('id="managerInstalledVersion"', page)
        self.assertIn("Advanced update source", page)
        self.assertNotIn("<title>Enshrouded Server Manager</title>", page)

    def test_release_state_distinguishes_current_ahead_and_missing_package(self):
        self.assertEqual("current", manager.manager_release_state("0.9.1", True, "0.9.1"))
        self.assertEqual("local_newer", manager.manager_release_state("0.7.7", False, "0.9.1"))
        self.assertEqual("available", manager.manager_release_state("0.9.1", True, "0.9.0"))
        self.assertEqual("package_missing", manager.manager_release_state("0.9.1", False, "0.9.0"))

    def test_public_update_status_masks_saved_token(self):
        status = manager.public_manager_updates({
            "repo": manager.GITHUB_REPO,
            "github_token": "secret-token",
            "latest_version": "0.7.7",
            "package_available": False,
            "last_error": "",
        })

        self.assertEqual("********", status["github_token"])
        self.assertTrue(status["token_saved"])
        self.assertTrue(status["using_default_public_repository"])
        self.assertEqual("local_newer", status["release_state"])
        self.assertEqual(manager.APP_VERSION, status["installed_version"])


if __name__ == "__main__":
    unittest.main()
