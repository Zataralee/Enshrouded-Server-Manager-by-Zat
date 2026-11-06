import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eml_update_manager", ROOT / "enshrouded_manager/manager.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
updates = manager.eml_updates


class EMLUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.updater = updates.Updater(self.root / "data", self.root / "vendor")
        self.updater.bundled.parent.mkdir(parents=True)
        self.updater.bundled.write_bytes(b"MZ bundled tool fixture")
        self.binary = b"MZ new upstream tool fixture"
        self.checksum = hashlib.sha256(self.binary).hexdigest()
        self.release = {"tag_name": "v0.3.0", "draft": False, "prerelease": False, "body": "Release notes",
                        "assets": [{"name": "emm.exe", "browser_download_url": updates.WEB + "/releases/download/v0.3.0/emm.exe",
                                    "digest": "sha256:" + self.checksum}]}
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("upstream-commit/LICENSE", "GNU GENERAL PUBLIC LICENSE fixture")
        self.source = data.getvalue()
        self.calls = []
        def fetch(url, maximum):
            self.calls.append(url)
            if url == updates.API + "/releases/latest": return json.dumps(self.release).encode()
            if url == updates.API + "/zipball/v0.3.0": return self.source
            if url == self.release["assets"][0]["browser_download_url"]: return self.binary
            raise AssertionError(url)
        patch = mock.patch.object(updates, "fetch", side_effect=fetch)
        patch.start(); self.addCleanup(patch.stop)
        patch = mock.patch.object(updates.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"emm 0.3.0\n--patch --force --game-directory --file-name", b""))
        self.probe = patch.start(); self.addCleanup(patch.stop)

    def test_check_is_cached_and_never_replaces_or_runs_tool(self):
        self.assertTrue(self.updater.check()["update_available"])
        self.assertTrue(self.updater.check()["install_available"])
        self.assertEqual(1, len(self.calls))
        self.assertFalse(self.updater.path.exists())
        self.probe.assert_not_called()

    def test_install_verified_tool_preserves_bundle_source_license_and_instance_data(self):
        instance = self.root / "data/eml/server/state.json"
        instance.parent.mkdir(parents=True); instance.write_text('{"enabled": true}')
        before = instance.read_bytes()
        status = self.updater.install("0.3.0")
        self.assertEqual("0.3.0", status["installed_version"])
        selected = self.updater.descriptor()
        self.assertEqual(self.binary, selected["tool"].read_bytes())
        self.assertEqual(self.source, selected["tool"].with_name("source.zip").read_bytes())
        self.assertIn(b"GENERAL PUBLIC LICENSE", selected["tool"].with_name("LICENSE").read_bytes())
        self.assertEqual(b"MZ bundled tool fixture", self.updater.bundled.read_bytes())
        self.assertEqual(before, instance.read_bytes())
        self.assertFalse(list(selected["tool"].parent.parent.glob("staging-*")))

    def test_bad_hash_never_selects_or_executes_download(self):
        self.binary += b"tamper"
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            self.updater.install("0.3.0")
        self.assertFalse(self.updater.path.exists())
        self.probe.assert_not_called()

    def test_failed_startup_keeps_current_tool_and_cleans_staging(self):
        self.probe.return_value = subprocess.CompletedProcess([], 1, b"", b"bad runtime")
        with self.assertRaisesRegex(RuntimeError, "startup check"):
            self.updater.install("0.3.0")
        self.assertFalse(self.updater.path.exists())
        self.assertFalse(list((self.updater.root / "releases").glob("staging-*")))

    def test_missing_digest_detected_but_not_installable(self):
        self.release["assets"][0].pop("digest")
        self.assertTrue(self.updater.check()["update_available"])
        self.assertFalse(self.updater.status()["install_available"])
        with self.assertRaisesRegex(RuntimeError, "SHA-256 digest"):
            self.updater.install("0.3.0")
        self.probe.assert_not_called()

    def test_incompatible_upstream_cli_does_not_replace_current_tool(self):
        self.probe.side_effect = [subprocess.CompletedProcess([], 0, b"emm 0.3.0", b""),
                                 subprocess.CompletedProcess([], 0, b"new incompatible CLI", b"")]
        with self.assertRaisesRegex(RuntimeError, "interface is incompatible"):
            self.updater.install("0.3.0")
        self.assertFalse(self.updater.path.exists())

    def test_changed_upstream_release_requires_fresh_user_selection(self):
        with self.assertRaisesRegex(RuntimeError, "release changed"):
            self.updater.install("0.4.0")
        self.probe.assert_not_called()

    def test_non_upstream_asset_and_prerelease_are_rejected(self):
        self.release["assets"][0]["browser_download_url"] = "https://other.invalid/emm.exe"
        with self.assertRaisesRegex(ValueError, "destination"):
            self.updater.install("0.3.0")
        self.release["prerelease"] = True
        with self.assertRaisesRegex(ValueError, "stable"):
            updates.release_info(self.release)

    def test_network_failure_retains_installed_tool_and_cached_release(self):
        self.updater.check()
        with mock.patch.object(updates, "fetch", side_effect=OSError("TLS verification failed")):
            status = self.updater.check(force=True)
        self.assertEqual("0.2.0", status["installed_version"])
        self.assertEqual("0.3.0", status["latest_version"])
        self.assertIn("TLS", status["last_error"])

    def test_rollback_uses_verified_bundle_and_rejects_tampering(self):
        self.updater.install("0.3.0")
        with self.assertRaisesRegex(RuntimeError, "verification"):
            self.updater.rollback()
        self.assertEqual("0.3.0", self.updater.status()["installed_version"])
        with mock.patch.object(updates, "EML_SHA256", hashlib.sha256(self.updater.bundled.read_bytes()).hexdigest()):
            self.assertEqual("0.2.0", self.updater.rollback()["installed_version"])

    def test_selected_tool_is_verified_at_execution_and_persists_after_reload(self):
        self.updater.install("0.3.0")
        selected = updates.Updater(self.root / "data", self.root / "vendor").descriptor()
        adapter = manager.EML(self.root / "server", self.root / "state", selected["tool"],
                              version=selected["version"], expected_sha256=selected["sha256"])
        adapter.check_tool()
        self.assertEqual("0.3.0", adapter.status()["version"])
        selected["tool"].write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError, "verification"):
            adapter.check_tool()


class EMLUpdateHTTPTests(unittest.TestCase):
    def test_only_admin_and_same_origin_can_check_or_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.multiple(manager, DATA_DIR=root, MANAGER_CONFIG=root / "config.json", MANAGER_LOG=root / "manager.log"), \
                    mock.patch.object(manager, "eml_updater") as updater:
                cfg = manager.default_config(); cfg["allow_local_bypass"] = True
                manager.save_json(manager.MANAGER_CONFIG, cfg)
                updater.return_value.check.return_value = {"installed_version": "0.2.0"}
                server = manager.ThreadingHTTPServer(("127.0.0.1", 0), manager.Handler)
                worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
                base = f"http://127.0.0.1:{server.server_port}"
                def post(origin=None):
                    headers = {"Content-Type": "application/json"}
                    if origin: headers["Origin"] = origin
                    return urllib.request.urlopen(urllib.request.Request(base + "/api/eml/check-update", data=b"{}", headers=headers), timeout=3)
                try:
                    with post() as response:self.assertEqual(200, response.status)
                    with self.assertRaises(urllib.error.HTTPError) as rejected:post("https://other.invalid")
                    self.assertEqual(403, rejected.exception.code)
                    with mock.patch.object(manager.Handler, "current_user", return_value={"role": "user", "permissions": ["logs"]}):
                        for path in ["/api/eml/updates", "/api/eml/check-update", "/api/eml/install-update", "/api/eml/rollback"]:
                            request = urllib.request.Request(base + path, data=None if path.endswith("updates") else b"{}", headers={"Content-Type":"application/json"})
                            with self.assertRaises(urllib.error.HTTPError) as rejected:urllib.request.urlopen(request, timeout=3)
                            self.assertEqual(403, rejected.exception.code)
                    self.assertEqual(1, updater.return_value.check.call_count)
                    updater.return_value.install.assert_not_called()
                    updater.return_value.rollback.assert_not_called()
                finally:
                    server.shutdown(); server.server_close(); worker.join(3)


if __name__ == "__main__":unittest.main()
