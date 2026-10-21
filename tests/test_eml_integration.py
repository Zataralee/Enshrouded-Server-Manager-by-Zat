import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("eml_manager_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
from eml_support import EML, MAX_UPLOAD, digest


def package(extra=None, prefix="example/", manifest=None, script='print("test")'):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr(prefix + "mod.json", json.dumps(manifest or {
            "id": "example", "name": "Example", "version": "1.0.0", "capabilities": ["patch"]}))
        archive.writestr(prefix + "src/mod.lua", script)
        for name, content in (extra or {}).items():
            entry = zipfile.ZipInfo(name)
            entry.filename = name  # Preserve hostile backslashes on Windows too.
            archive.writestr(entry, content)
    return data.getvalue()


class EMLTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.server = self.root / "server"
        self.server.mkdir()
        (self.server / "enshrouded_server.exe").write_bytes(b"server build 1")
        (self.server / "enshrouded_server.kfc").write_bytes(b"original index")
        self.eml = EML(self.server, self.root / "state", self.root / "emm.exe")
        patcher = mock.patch.object(self.eml, "check_tool")
        patcher.start()
        self.addCleanup(patcher.stop)

    def install(self):
        self.eml.enable(True)
        self.eml.import_zip(package())
        self.eml.change_mod("example", "enable")

    def patch_game(self, arguments):
        self.eml.kfc.with_suffix(".kfc.bak").write_bytes(b"original index")
        self.eml.kfc.write_bytes(b"patched index")

    def test_import_accepts_normal_and_unwrapped_mods(self):
        for prefix in ("example/", "", "mods/example/"):
            with self.subTest(prefix=prefix):
                self.eml.import_zip(package(prefix=prefix))
                self.assertFalse(self.eml.status()["mods"][0]["enabled"])
                self.assertEqual(b"original index", self.eml.kfc.read_bytes())
                self.eml.change_mod("example", "remove")

    def test_rejects_unsafe_archives(self):
        for path in ("../escape", "/absolute", "C:/bad", "example/../bad", "example\\bad",
                     "example/file:stream", "example/con.txt", "example/trailing.", "example/load.dll"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.eml.import_zip(package({path: "bad"}))
        self.assertFalse(self.eml.status()["mods"])

    def test_rejects_symlink_case_collision_and_multiple_mods(self):
        for payload in (package({"example/MOD.JSON": "{}"}), package({"another/mod.json": "{}"})):
            with self.assertRaises(ValueError):
                self.eml.import_zip(payload)
        data = io.BytesIO(package())
        with zipfile.ZipFile(data, "a") as archive:
            entry = zipfile.ZipInfo("example/link")
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(entry, "../../outside")
        with self.assertRaises(ValueError):
            self.eml.import_zip(data.getvalue())

    def test_rejects_wrong_loader_and_bad_manifest(self):
        for updates in ({"capabilities": ["runtime"]}, {"capabilities": ["patch", "export"]},
                        {"id": "../escape"}, {"version": "junk"}, {"dependencies": ["missing"]}):
            manifest = {"id": "example", "name": "Example", "version": "1.0.0", "capabilities": ["patch"], **updates}
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.eml.import_zip(package(manifest=manifest))

    def test_rejects_oversized_upload(self):
        with self.assertRaises(ValueError):
            self.eml.import_zip(b"0" * (MAX_UPLOAD + 1))

    def test_duplicate_install_leaves_original_intact(self):
        self.eml.import_zip(package())
        with self.assertRaises(ValueError):
            self.eml.import_zip(package(script='error("replacement")'))
        text = self.eml.config_file("example", "src/mod.lua")["content"]
        self.assertEqual('print("test")', text)

    def test_apply_then_disable_restores_exact_original(self):
        self.install()
        with mock.patch.object(self.eml, "command", side_effect=self.patch_game):
            self.eml.apply()
        self.assertTrue(self.eml.status()["patched"])
        self.eml.enable(False)
        self.assertEqual(b"original index", self.eml.kfc.read_bytes())
        self.assertFalse(self.eml.status()["enabled"])

    def test_removing_last_mod_restores_original(self):
        self.install()
        with mock.patch.object(self.eml, "command", side_effect=self.patch_game):
            self.eml.apply()
        self.eml.change_mod("example", "remove")
        self.assertEqual(b"original index", self.eml.kfc.read_bytes())
        self.assertFalse(self.eml.status()["mods"])

    def test_partial_patch_failure_restores_and_reports_error(self):
        self.install()
        def failure(arguments):
            self.patch_game(arguments)
            raise RuntimeError("script failed")
        with mock.patch.object(self.eml, "command", side_effect=failure), self.assertRaises(RuntimeError):
            self.eml.apply()
        self.assertEqual(b"original index", self.eml.kfc.read_bytes())
        self.assertIn("script failed", self.eml.status()["last_error"])

    def test_unknown_build_never_restores_old_assets(self):
        self.install()
        with mock.patch.object(self.eml, "command", side_effect=self.patch_game):
            self.eml.apply()
        self.eml.exe.write_bytes(b"server build 2")
        self.eml.kfc.write_bytes(b"new build index")
        with self.assertRaises(RuntimeError):
            self.eml.restore()
        self.assertEqual(b"new build index", self.eml.kfc.read_bytes())

    def test_failed_steam_update_blocks_start_until_validated(self):
        self.install()
        with mock.patch.object(self.eml, "command", side_effect=self.patch_game):
            self.eml.apply()
        self.eml.prepare_update()
        with self.assertRaises(RuntimeError):
            self.eml.apply()
        self.eml.exe.write_bytes(b"server build 2")
        self.eml.kfc.write_bytes(b"new build index")
        self.eml.finish_update()
        self.assertFalse(self.eml.status()["recovery_required"])
        self.assertFalse(self.eml.kfc.with_suffix(".kfc.bak").exists())
        self.eml.ensure_baseline()
        self.assertEqual(digest(self.eml.kfc), self.eml.state()["baseline"]["kfc"])

    def test_unmanaged_loader_or_mods_are_not_overwritten(self):
        (self.server / "dbghelp.dll").write_bytes(b"another loader")
        with self.assertRaises(RuntimeError):
            self.eml.enable(True)
        (self.server / "dbghelp.dll").unlink()
        (self.server / "mods" / "unmanaged").mkdir(parents=True)
        with self.assertRaises(RuntimeError):
            self.eml.import_zip(package())

    def test_edit_config_is_contained_and_updates_enabled_copy(self):
        self.install()
        self.eml.config_file("example", "src/mod.lua", 'print("updated")')
        self.assertEqual('print("updated")', (self.server / "mods/example/src/mod.lua").read_text())
        with self.assertRaises(ValueError):
            self.eml.config_file("example", "../state.json", "bad")
        with self.assertRaises(ValueError):
            self.eml.config_file("example", "mod.json", "{}")

    def test_zero_exit_with_upstream_error_is_failure(self):
        def false_success(*args, **kwargs):
            kwargs["stdout"].write(b"ERROR Errors loading some mods\n")
            return mock.Mock(returncode=0)
        with mock.patch("eml_support.subprocess.run", side_effect=false_success), self.assertRaises(RuntimeError):
            self.eml.command(["run", "--patch"])


class ModHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.paths = mock.patch.multiple(manager, DATA_DIR=root / "data", MANAGER_CONFIG=root / "data/config.json", MANAGER_LOG=root / "data/log")
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.instance = manager.default_instance("HTTP Mod Test", root / "server")
        cfg = manager.default_config()
        cfg["instances"] = [self.instance]
        manager.save_json(manager.MANAGER_CONFIG, cfg)
        self.user = {"id": "admin", "role": "admin"}
        owner = self
        class TestHandler(manager.Handler):
            def current_user(self):
                return owner.user
            def log_message(self, *args):
                pass
        self.server = manager.ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.sup = manager.ServerSupervisor(self.instance["id"])
        self.eml = mock.Mock()
        self.eml.import_zip.return_value = {"installed": True}
        for patcher in (mock.patch.object(manager, "supervisor", return_value=self.sup),
                        mock.patch.object(manager, "eml_for_instance", return_value=self.eml)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def upload(self, headers=None):
        request = urllib.request.Request(f"http://127.0.0.1:{self.server.server_port}/api/mods/upload?instance_id={self.instance['id']}",
                                         data=package(), headers={"Content-Type": "application/zip", **(headers or {})})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def test_admin_remote_upload_reaches_selected_instance(self):
        self.assertTrue(self.upload()["installed"])
        self.eml.import_zip.assert_called_once()

    def test_nonadmin_cannot_upload(self):
        self.user = {"id": "user", "role": "user", "permissions": ["setup", "control", "settings"]}
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.upload()
        self.assertEqual(403, raised.exception.code)
        self.eml.import_zip.assert_not_called()

    def test_running_server_cannot_be_modified(self):
        self.sup.process = mock.Mock()
        self.sup.process.poll.return_value = None
        with self.assertRaises(urllib.error.HTTPError):
            self.upload()
        self.eml.import_zip.assert_not_called()

    def test_cross_origin_upload_is_forbidden(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.upload({"Origin": "https://other.invalid"})
        self.assertEqual(403, raised.exception.code)
        self.eml.import_zip.assert_not_called()

    def test_failed_patch_prevents_server_launch_and_restart_loop(self):
        server = Path(self.instance["path"])
        server.mkdir()
        (server / "enshrouded_server.exe").write_bytes(b"test server")
        self.eml.apply.side_effect = RuntimeError("mod failed")
        with mock.patch.object(manager, "validate_instance_can_start"), \
                mock.patch.object(manager.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(RuntimeError, "mod failed"):
                self.sup.start()
        launch.assert_not_called()
        self.assertFalse(manager.get_instance(self.instance["id"])["desired_running"])
        self.assertEqual("idle", self.sup.activity)

    def test_modded_instance_cannot_bypass_stable_guard_by_removal(self):
        self.eml.status.return_value = {"enabled": True, "patched": False, "recovery_required": False}
        with self.assertRaisesRegex(RuntimeError, "Disable EML"):
            manager.remove_instance(self.instance["id"])
        self.assertEqual(self.instance["id"], manager.get_instance(self.instance["id"])["id"])


if __name__ == "__main__":
    unittest.main()
