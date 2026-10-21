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
    def test_checkbox_check_saves_only_channel_without_saving_manager_form(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.multiple(
                manager, DATA_DIR=Path(temporary), MANAGER_CONFIG=Path(temporary) / "config.json",
                MANAGER_LOG=Path(temporary) / "manager.log"):
            cfg = manager.default_config()
            cfg["manager_updates"].update(channel="stable", enabled=False)
            cfg["port"] = 18432
            manager.save_json(manager.MANAGER_CONFIG, cfg)
            release = {"tag_name": "v99.0.0.1b", "prerelease": True,
                       "assets": [{"name": "ESM-Z-PythonRequired-v99.0.0.1b.zip"}]}
            with mock.patch.object(manager, "latest_release_for_host", return_value=release) as lookup, \
                    mock.patch.object(manager, "notify_webhook_event"):
                result = manager.check_manager_updates(force=True, channel="beta")
            self.assertEqual("beta", lookup.call_args.kwargs["channel"])
            self.assertTrue(result["update_available"])
            saved = manager.config()
            self.assertEqual("beta", saved["manager_updates"]["channel"])
            self.assertEqual(18432, saved["port"])
            self.assertFalse(saved["manager_updates"]["enabled"])

    def test_old_channel_check_cannot_overwrite_new_channel_results(self):
        for fails in (False, True):
            with self.subTest(fails=fails), tempfile.TemporaryDirectory() as temporary, mock.patch.multiple(
                    manager, DATA_DIR=Path(temporary), MANAGER_CONFIG=Path(temporary) / "config.json",
                    MANAGER_LOG=Path(temporary) / "manager.log"):
                cfg = manager.default_config()
                cfg["manager_updates"]["channel"] = "stable"
                manager.save_json(manager.MANAGER_CONFIG, cfg)
                def concurrent_check(*args, **kwargs):
                    new = manager.config()
                    new["manager_updates"].update(channel="beta", latest_version="99.0.0.1b", last_error="")
                    manager.save_json(manager.MANAGER_CONFIG, new)
                    if fails:
                        raise RuntimeError("old channel lookup failed")
                    return {"tag_name": "v99.0.0.1a", "assets": []}
                with mock.patch.object(manager, "latest_release_for_host", side_effect=concurrent_check):
                    result = manager.check_manager_updates(force=True)
                self.assertEqual("beta", result["channel"])
                self.assertEqual("99.0.0.1b", result["latest_version"])
                self.assertEqual("", result["last_error"])

    def test_checkbox_rejects_unrelated_prerelease_channel(self):
        with self.assertRaises(ValueError):
            manager.check_manager_updates(force=True, channel="prerelease")

    def test_four_part_and_letter_versions_are_ordered(self):
        versions = ["0.9.6", "0.9.6.1a", "0.9.6.1b", "0.9.6.2a", "0.9.7", "0.10.0-linux-alpha.7", "0.10.0"]
        self.assertEqual(versions, sorted(reversed(versions), key=manager.version_parts))

    def test_beta_checkbox_channel_excludes_linux_alpha(self):
        releases = [
            {"tag_name": "v0.10.0-linux-alpha.7", "prerelease": True},
            {"tag_name": "v0.9.6.1a", "prerelease": False},
            {"tag_name": "v0.9.6.1b", "prerelease": True},
            {"tag_name": "v0.9.6.2b", "prerelease": True, "draft": True},
        ]
        with mock.patch.object(manager, "github_json", return_value=releases):
            self.assertEqual("v0.9.6.1b", manager.latest_release_for_host("owner/repo", channel="beta")["tag_name"])
            self.assertEqual("v0.9.6.1a", manager.latest_release_for_host("owner/repo", channel="stable")["tag_name"])

    def test_beta_is_excluded_even_if_github_prerelease_flag_is_missing(self):
        self.assertTrue(manager.release_is_prerelease({"tag_name": "v0.9.6.1b"}))
        self.assertFalse(manager.release_is_prerelease({"tag_name": "v0.9.6.1a"}))

    def test_explicit_return_to_paired_stable_is_available(self):
        self.assertEqual("available", manager.manager_release_state("0.9.6.1a", True, "0.9.6.1b", "stable"))
        self.assertEqual("local_newer", manager.manager_release_state("0.9.6.1a", True, "0.9.6.1b", "beta"))
        self.assertEqual("local_newer", manager.manager_release_state("0.9.5", True, "0.9.6.1b", "stable"))

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
                    "tag_name": "v99.0.0",
                    "draft": False,
                    "prerelease": False,
                    "html_url": "https://example.invalid/release",
                    "assets": [{
                        "name": "ESM-Z-PythonRequired-v99.0.0.zip",
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
            "latest_version": "99.0.0",
            "package_available": True,
            "installed_pending_version": "99.0.0",
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

    def test_update_staging_preserves_live_files_and_data(self):
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
                archive.writestr("enshrouded_manager/manager.py", 'APP_VERSION = "99.0.0"\n')
                archive.writestr("enshrouded_manager/static/index.html", "new")
                archive.writestr("enshrouded_manager/new.txt", "new")
                archive.writestr("enshrouded_manager/update_runtime.py", "# update helper\n")

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
                    "tag_name": "v99.0.0",
                    "draft": False,
                    "prerelease": False,
                    "assets": [{
                        "name": "ESM-Z-PythonRequired-v99.0.0.zip",
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
            self.assertTrue((app_dir / "old.txt").exists())
            self.assertFalse((app_dir / "new.txt").exists())
            self.assertEqual("new", (Path(result["source"]) / "new.txt").read_text())
            self.assertTrue((Path(result["backup"]) / "old.txt").is_file())
            self.assertEqual("99.0.0", result["target_version"])


if __name__ == "__main__":
    unittest.main()
