import hashlib
import http.client
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manager_log_download_test", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
logs = manager.log_downloads


class LogDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "enshrouded_manager"
        self.data = self.app / "data"
        self.static = self.app / "static"
        self.data.mkdir(parents=True)
        self.static.mkdir()
        (self.static / "index.html").write_text("fixture")
        self.server_one = self.root / "one"
        self.server_two = self.root / "two"
        for path in (self.server_one, self.server_two):
            (path / "logs" / "backup").mkdir(parents=True)
            (path / "logs" / "enshrouded_server.log").write_bytes(b"first line\r\nlast line\r\n")
        (self.data / "manager.log").write_bytes(b"private manager history\n")
        (self.data / "manager_config.json").write_text('{"secret":"must not be downloaded"}')
        self.cfg = manager.default_config()
        self.cfg["instances"] = [manager.default_instance("One", self.server_one), manager.default_instance("Two", self.server_two)]
        self.one, self.two = self.cfg["instances"]
        self.cfg["selected_instance_id"] = self.one["id"]
        self.user = {"id": "owner", "role": "server_owner", "permissions": ["logs"],
                     "assigned_instance_ids": [self.one["id"]]}
        self.patches = mock.patch.multiple(manager, APP_DIR=self.app, DATA_DIR=self.data,
            MANAGER_CONFIG=self.data / "manager_config.json", MANAGER_LOG=self.data / "manager.log",
            ROOT=self.root, STATIC_DIR=self.static, config=mock.Mock(side_effect=lambda: self.cfg))
        self.patches.start()
        self.addCleanup(self.patches.stop)
        patch = mock.patch.object(manager.Handler, "current_user", new=lambda handler: self.user)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch.object(manager.Handler, "log_message")
        patch.start()
        self.addCleanup(patch.stop)
        self.http = manager.ThreadingHTTPServer(("127.0.0.1", 0), manager.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(3)

    def get(self, path, read=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.http.server_port, timeout=10)
        self.addCleanup(connection.close)
        connection.request("GET", path)
        response = connection.getresponse()
        return response, response.read() if read else None

    def endpoint(self, log_id, instance=None):
        return "/api/logs/download?" + urlencode({"log_id": log_id, "instance_id": instance or self.one["id"]})

    def test_full_large_download_preserves_exact_bytes_and_attachment_headers(self):
        payload = b"BEGIN\x00\xff\r\n" + bytes(range(256)) * 45000 + b"\nEND\n"
        (self.server_one / "logs" / "enshrouded_server.log").write_bytes(payload)
        response, _ = self.get(self.endpoint("server:enshrouded_server.log"), read=False)
        self.assertEqual(200, response.status)
        self.assertEqual(len(payload), int(response.getheader("Content-Length")))
        self.assertEqual("application/octet-stream", response.getheader("Content-Type"))
        self.assertIn("attachment;", response.getheader("Content-Disposition"))
        self.assertEqual("nosniff", response.getheader("X-Content-Type-Options"))
        self.assertEqual("no-store", response.getheader("Cache-Control"))
        digest = hashlib.sha256()
        count = 0
        while chunk := response.read(65536):
            digest.update(chunk)
            count += len(chunk)
        self.assertEqual(len(payload), count)
        self.assertEqual(hashlib.sha256(payload).digest(), digest.digest())

    def test_catalog_lists_only_logs_without_reading_contents_or_recursing(self):
        for name in ("connection_log_15637.txt", "systemmanager.txt", "empty.log"):
            (self.server_one / "logs" / name).write_bytes(b"")
        (self.server_one / "logs" / "credentials.txt").write_text("secret")
        (self.server_one / "logs" / "config.json").write_text("secret")
        (self.server_one / "logs" / "backup" / "old.log").write_text("archive")
        nested = self.data / "eml" / "packages"
        nested.mkdir(parents=True)
        (nested / "secret.log").write_text("not a manager log")
        with mock.patch.object(Path, "rglob", side_effect=AssertionError("must not recurse")), \
                mock.patch.object(Path, "open", side_effect=AssertionError("metadata only")):
            response, body = self.get("/api/logs?" + urlencode({"instance_id": self.one["id"]}))
        self.assertEqual(200, response.status)
        names = {item["name"] for item in json.loads(body)["logs"]}
        self.assertEqual({"enshrouded_server.log", "connection_log_15637.txt", "systemmanager.txt", "empty.log", "backup/old.log"}, names)

    def test_authentication_permissions_and_exact_server_scope_are_enforced(self):
        self.user = None
        self.assertEqual(401, self.get(self.endpoint("server:enshrouded_server.log"))[0].status)
        self.user = {"id": "restricted", "role": "user", "permissions": [], "assigned_instance_ids": [self.one["id"]]}
        self.assertEqual(403, self.get(self.endpoint("server:enshrouded_server.log"))[0].status)
        self.user["permissions"] = ["logs"]
        for log_id, instance in [("manager:manager.log", None), ("updates:update-console.log", None),
                                 ("server:enshrouded_server.log", self.two["id"])]:
            with self.subTest(log_id=log_id, instance=instance):
                self.assertEqual(403, self.get(self.endpoint(log_id, instance))[0].status)
        self.assertEqual(403, self.get("/api/logs?" + urlencode({"instance_id": self.two["id"]}))[0].status)

    def test_arbitrary_paths_old_preview_and_static_traversal_cannot_read_config(self):
        self.user = {"id": "admin", "role": "admin"}
        for log_id in ["manager:manager_config.json", "server:../../data/manager_config.json",
                       "server:..\\manager.log", "server:C:\\secret.log", "server:a.log:secret",
                       "job:" + "a" * 32 + "/../../manager_config.json", str(self.data / "manager_config.json")]:
            with self.subTest(log_id=log_id):
                response, body = self.get(self.endpoint(log_id))
                self.assertEqual(403, response.status)
                self.assertNotIn(b"must not be downloaded", body)
        response, body = self.get("/api/log?" + urlencode({"path": str(self.data / "manager_config.json")}))
        self.assertEqual(410, response.status)
        self.assertNotIn(b"must not be downloaded", body)
        for path in ["/%2e%2e/data/manager_config.json", "/%2e%2e%5cdata%5cmanager_config.json"]:
            self.assertEqual(404, self.get(path)[0].status)

    def test_static_windows_network_paths_are_rejected_before_filesystem_access(self):
        handler = manager.Handler.__new__(manager.Handler)
        with mock.patch.object(manager, "safe_child", side_effect=AssertionError("must not resolve network paths")):
            for path in ["/%5c%5cunknown-host%5cshare%5cfile", "/C:%5csecret", "/bad%00path"]:
                self.assertEqual(str(self.static / "__not_found__"), handler.translate_path(path))

    def test_admin_can_download_manager_update_and_job_logs_without_a_server(self):
        self.user = {"id": "admin", "role": "admin"}
        self.cfg["instances"] = []
        self.cfg["selected_instance_id"] = ""
        job = "a" * 32
        directory = self.data / "manager_updates" / job
        directory.mkdir(parents=True)
        (directory / "helper.log").write_bytes(b"job evidence")
        (directory.parent / "update-console.log").write_bytes(b"console evidence")
        response, body = self.get("/api/logs")
        self.assertEqual(200, response.status)
        self.assertEqual(3, len(json.loads(body)["logs"]))
        for log_id in ["manager:manager.log", "updates:update-console.log", "job:" + job + "/helper.log"]:
            self.assertEqual(200, self.get("/api/logs/download?" + urlencode({"log_id": log_id}))[0].status)

    def test_missing_rotated_log_returns_404_and_empty_log_downloads(self):
        self.assertEqual(404, self.get(self.endpoint("server:removed.log"))[0].status)
        (self.server_one / "logs" / "empty.log").touch()
        response, body = self.get(self.endpoint("server:empty.log"))
        self.assertEqual(200, response.status)
        self.assertEqual(b"", body)
        self.assertEqual("0", response.getheader("Content-Length"))

    def test_hardlink_cannot_alias_sensitive_configuration(self):
        os.link(self.data / "manager_config.json", self.server_one / "logs" / "secret.log")
        response, body = self.get(self.endpoint("server:secret.log"))
        self.assertEqual(403, response.status)
        self.assertNotIn(b"must not be downloaded", body)

    def test_symlink_cannot_escape_log_directory(self):
        try:
            (self.server_one / "logs" / "linked.log").symlink_to(self.data / "manager_config.json")
        except OSError:
            self.skipTest("Creating symlinks requires Windows developer mode or privilege")
        self.assertEqual(403, self.get(self.endpoint("server:linked.log"))[0].status)

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_windows_junction_cannot_redirect_archive_to_manager_data(self):
        archive = self.server_one / "logs" / "backup"
        archive.rmdir()
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(archive), str(self.data)],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(403, self.get(self.endpoint("archive:manager.log"))[0].status)
        listing = logs.LogCatalog(self.app, self.server_one).list()
        self.assertFalse(any(item["id"] == "archive:manager.log" for item in listing["logs"]))

    def test_status_polling_does_not_discover_logs(self):
        fake = mock.Mock()
        fake.status.return_value = {}
        with mock.patch.object(manager, "supervisor", return_value=fake), \
                mock.patch.object(manager, "load_json", return_value={}), \
                mock.patch.object(manager, "visible_jobs_for_user", return_value=[]), \
                mock.patch.object(manager, "public_config", return_value={}), \
                mock.patch.object(logs.LogCatalog, "list", side_effect=AssertionError("status must not list logs")), \
                mock.patch.object(Path, "rglob", side_effect=AssertionError("status must not recurse")):
            response, body = self.get("/api/status?" + urlencode({"instance_id": self.one["id"]}))
        self.assertEqual(200, response.status)
        self.assertNotIn("logs", json.loads(body))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_ignores_appends_and_reads_bounded_chunks(self):
        class Source(io.BytesIO):
            sizes = []
            def read(self, size=-1):
                self.sizes.append(size)
                return super().read(size)
        initial = logs.CHUNK_SIZE * 3 + 7
        source = Source(b"x" * initial + b"later append")
        output = io.BytesIO()
        logs.copy_snapshot(source, output, initial)
        self.assertEqual(b"x" * initial, output.getvalue())
        self.assertTrue(all(0 < n <= logs.CHUNK_SIZE for n in source.sizes))

    def test_truncation_is_an_interrupted_download_not_silent_success(self):
        with self.assertRaises(OSError):
            logs.copy_snapshot(io.BytesIO(b"short"), io.BytesIO(), 100)


if __name__ == "__main__":
    unittest.main()
