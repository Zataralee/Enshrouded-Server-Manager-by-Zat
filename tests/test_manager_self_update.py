import hashlib
import importlib.util
import io
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manager_self_update_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class ManagerSelfUpdateTests(unittest.TestCase):
    def test_stable_auto_channel_ignores_prereleases(self):
        releases = [
            {"tag_name": "v0.10.0-linux-alpha.3", "draft": False, "prerelease": True},
            {"tag_name": "v0.9.3", "draft": False, "prerelease": False},
        ]
        with mock.patch.object(manager, "github_json", return_value=releases):
            selected = manager.latest_release_for_host("owner/repo", channel="auto", current_version="0.9.2")

        self.assertEqual("v0.9.3", selected["tag_name"])

    def test_testing_channel_can_select_prerelease(self):
        releases = [
            {"tag_name": "v0.9.3", "draft": False, "prerelease": False},
            {"tag_name": "v0.10.0-linux-alpha.3", "draft": False, "prerelease": True},
        ]
        with mock.patch.object(manager, "github_json", return_value=releases):
            selected = manager.latest_release_for_host("owner/repo", channel="prerelease", current_version="0.9.2")

        self.assertEqual("v0.10.0-linux-alpha.3", selected["tag_name"])

    def test_update_checks_never_auto_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            original = (manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
            manager.DATA_DIR = temp / "data"
            manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
            manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
            try:
                cfg = manager.default_config()
                cfg["manager_updates"]["auto_install"] = True
                manager.save_json(manager.MANAGER_CONFIG, cfg)
                release = {
                    "tag_name": "v0.9.3",
                    "draft": False,
                    "prerelease": False,
                    "html_url": "https://example.invalid/release",
                    "assets": [{
                        "name": "ESM-Z-PythonRequired-v0.9.3.zip",
                        "browser_download_url": "https://example.invalid/update.zip",
                    }],
                }
                with mock.patch.object(manager, "latest_release_for_host", return_value=release), \
                        mock.patch.object(manager, "notify_webhook_event"), \
                        mock.patch.object(manager, "install_manager_update") as install:
                    result = manager.check_manager_updates(force=True)
            finally:
                manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = original

        self.assertTrue(result["update_available"])
        install.assert_not_called()

    def test_pending_restart_has_distinct_public_state(self):
        status = manager.public_manager_updates({
            "latest_version": "0.9.3",
            "package_available": True,
            "installed_pending_version": "0.9.3",
            "restart_required": True,
            "last_error": "",
        })

        self.assertEqual("installed_pending_restart", status["release_state"])
        self.assertFalse(status["update_available"])

    def test_safe_zip_extraction_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            archive = temp / "bad.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("../outside.txt", "bad")

            with self.assertRaises(ValueError):
                manager.safe_extract_zip(archive, temp / "extract")

    def test_release_checksum_is_verified_when_present(self):
        payload = b"verified update package"
        digest = hashlib.sha256(payload).hexdigest()
        release = {
            "assets": [{
                "name": "ESM-Z-PythonRequired-v0.9.3.zip.sha256",
                "browser_download_url": "https://example.invalid/update.sha256",
            }]
        }
        package_asset = {"name": "ESM-Z-PythonRequired-v0.9.3.zip"}
        response = io.BytesIO(f"{digest}  {package_asset['name']}\n".encode("ascii"))
        with tempfile.TemporaryDirectory() as temporary:
            package_path = Path(temporary) / package_asset["name"]
            package_path.write_bytes(payload)
            with mock.patch.object(manager, "urlopen_https", return_value=response):
                verified = manager.verify_release_checksum(release, package_asset, package_path)

        self.assertTrue(verified)

    def test_manual_install_preserves_data_and_marks_restart_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            app_dir = temp / "enshrouded_manager"
            data_dir = app_dir / "data"
            static_dir = app_dir / "static"
            static_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            (app_dir / "manager.py").write_text('APP_VERSION = "old"\n', encoding="utf-8")
            (app_dir / "old.txt").write_text("old", encoding="utf-8")
            (static_dir / "index.html").write_text("old", encoding="utf-8")
            (data_dir / "preserve.txt").write_text("keep", encoding="utf-8")

            package = temp / "release.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("enshrouded_manager/manager.py", 'APP_VERSION = "0.9.3"\n')
                archive.writestr("enshrouded_manager/static/index.html", "new")
                archive.writestr("enshrouded_manager/new.txt", "new")

            original = (manager.APP_DIR, manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG)
            manager.APP_DIR = app_dir
            manager.DATA_DIR = data_dir
            manager.MANAGER_CONFIG = data_dir / "manager_config.json"
            manager.MANAGER_LOG = data_dir / "manager.log"
            try:
                cfg = manager.default_config()
                cfg["manager_updates"]["update_available"] = True
                manager.save_json(manager.MANAGER_CONFIG, cfg)
                release = {
                    "tag_name": "v0.9.3",
                    "draft": False,
                    "prerelease": False,
                    "assets": [{
                        "name": "ESM-Z-PythonRequired-v0.9.3.zip",
                        "browser_download_url": "https://example.invalid/release.zip",
                    }],
                }

                def copy_package(asset, destination, token=""):
                    shutil.copy2(package, destination)

                with mock.patch.object(manager, "latest_release_for_host", return_value=release), \
                        mock.patch.object(manager, "download_github_asset", side_effect=copy_package), \
                        mock.patch.object(manager, "verify_release_checksum", return_value=True), \
                        mock.patch.object(manager, "notify_webhook_event"):
                    result = manager.install_manager_update()
            finally:
                manager.APP_DIR, manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = original

            self.assertEqual("keep", (data_dir / "preserve.txt").read_text(encoding="utf-8"))
            self.assertFalse((app_dir / "old.txt").exists())
            self.assertEqual("new", (app_dir / "new.txt").read_text(encoding="utf-8"))
            self.assertTrue(result["restart_required"])
            self.assertEqual("0.9.3", result["installed_pending_version"])


if __name__ == "__main__":
    unittest.main()
