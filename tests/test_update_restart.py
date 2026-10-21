import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("restart_tests", ROOT / "enshrouded_manager" / "manager.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
runtime = manager.update_runtime


class SessionAndSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG
        manager.DATA_DIR = Path(self.temp.name)
        manager.MANAGER_CONFIG = manager.DATA_DIR / "manager_config.json"
        manager.MANAGER_LOG = manager.DATA_DIR / "manager.log"
        manager.save_json(manager.MANAGER_CONFIG, manager.default_config())

    def tearDown(self):
        manager.DATA_DIR, manager.MANAGER_CONFIG, manager.MANAGER_LOG = self.original
        self.temp.cleanup()

    def test_sessions_survive_reload_without_storing_bearer_token(self):
        user = manager.primary_admin()
        token = manager.create_session(user)
        self.assertEqual(user["id"], manager.session_user(token)["id"])
        text = (manager.DATA_DIR / "sessions.json").read_text()
        self.assertNotIn(token, text)
        self.assertIn(hashlib.sha256(token.encode()).hexdigest(), text)
        self.assertNotIn(user["password_hash"], text)
        manager.revoke_session(token)
        self.assertIsNone(manager.session_user(token))

    def test_password_changes_and_expiry_invalidate_session(self):
        token = manager.create_session(manager.primary_admin())
        config = manager.config()
        config["users"][0]["password_hash"] = "changed"
        manager.save_json(manager.MANAGER_CONFIG, config)
        self.assertIsNone(manager.session_user(token))
        token = manager.create_session(manager.primary_admin())
        with mock.patch.object(manager.time, "time", return_value=time.time() + 90000):
            self.assertIsNone(manager.session_user(token))

    def test_busy_operations_do_not_pass_update_barrier(self):
        with mock.patch.object(manager, "ACTIVE_OPERATIONS", 1):
            with self.assertRaisesRegex(RuntimeError, "active server operation"):
                manager.wait_for_update_idle(timeout=0.01)
        manager.wait_for_update_idle(timeout=1)

    def test_file_replacement_preserves_data_and_rejects_wrong_destination(self):
        root = Path(self.temp.name)
        source = root / "source"
        source.mkdir()
        (source / "manager.py").write_text("# new")
        app = root / "enshrouded_manager"
        (app / "data").mkdir(parents=True)
        (app / "data" / "save.txt").write_text("keep")
        (app / "old.txt").write_text("old")
        runtime.replace_files(source, app)
        self.assertEqual("keep", (app / "data" / "save.txt").read_text())
        self.assertFalse((app / "old.txt").exists())
        with self.assertRaises(ValueError):
            runtime.replace_files(source, root)


class RealRestartTests(unittest.TestCase):
    def run_scenario(self, broken=False, browser=False, channel=None):
        target_version = manager.APP_VERSION[:-1] + ("b" if channel == "beta" else "a") if channel else "99.0.0"
        running_version = manager.APP_VERSION[:-1] + ("a" if channel == "beta" else "b") if channel else manager.APP_VERSION
        with tempfile.TemporaryDirectory(prefix="esm remote restart ") as temporary:
            root = Path(temporary)
            app = root / "enshrouded_manager"
            app.mkdir()
            for name in ("manager.py", "update_runtime.py"):
                shutil.copy2(ROOT / "enshrouded_manager" / name, app / name)
            # The beta branch also needs its existing EML module, but no game/mod binaries are run.
            eml = ROOT / "enshrouded_manager" / "eml_support.py"
            if eml.exists():
                shutil.copy2(eml, app / eml.name)
            shutil.copytree(ROOT / "enshrouded_manager" / "static", app / "static")
            if channel:
                source = (app / "manager.py").read_text().replace(
                    f'APP_VERSION = "{manager.APP_VERSION}"', f'APP_VERSION = "{running_version}"')
                (app / "manager.py").write_text(source)
            (app / "data").mkdir()
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            config = manager.default_config()
            password = config["initial_password"]
            config.update(port=port, allow_local_bypass=False, instances=[], selected_instance_id="",
                          server_root=str(root / "Servers"), backup_root=str(root / "Backups"))
            config["manager_updates"].update(enabled=False, update_available=True, latest_version="99.0.0", package_available=True)
            if channel:
                config["manager_updates"].update(channel="stable" if channel == "beta" else "beta",
                                                 update_available=False, latest_version="", package_available=False)
            config["users"].append(manager.default_user("reader", "reader-pass", role="user", permissions=["logs"]))
            (app / "data" / "manager_config.json").write_text(json.dumps(config))
            (app / "data" / "preserve.txt").write_text("keep")
            package = root / "release.zip"
            source = (app / "manager.py").read_text()
            source = source.replace(f'APP_VERSION = "{running_version}"', f'APP_VERSION = "{target_version}"')
            if broken:
                source = source.replace('    main()\n', '    raise RuntimeError("deliberate startup failure")\n')
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("enshrouded_manager/manager.py", source)
                for path in app.rglob("*"):
                    if path.is_file() and "data" not in path.parts and path.name != "manager.py":
                        archive.write(path, "enshrouded_manager/" + path.relative_to(app).as_posix())
            fixture = f'''
import importlib.util, shutil
spec=importlib.util.spec_from_file_location("fixture", {str(app / 'manager.py')!r})
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.latest_release_for_host=lambda *a,**k: {{"tag_name":"v{target_version}", "assets":[{{"name":"ESM-Z-PythonRequired-v{target_version}.zip"}}]}}
m.download_github_asset=lambda asset,destination,**k: shutil.copy2({str(package)!r},destination)
m.verify_release_checksum=lambda *a,**k: True
stage=m.install_manager_update
def install():
    plan=stage(); plan["health_timeout"]=3; return plan
m.install_manager_update=install
m.main()
'''
            base = f"http://127.0.0.1:{port}"
            console = (root / "console.log").open("wb")
            previous = subprocess.Popen([sys.executable, "-u", "-c", fixture], stdout=console, stderr=subprocess.STDOUT)
            sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cookie = ""

            def request(path, body=None):
                headers = {"Cookie": cookie, "Content-Type": "application/json"}
                data = json.dumps(body).encode() if body is not None else None
                with urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=headers), timeout=2) as response:
                    return json.load(response), response.headers

            try:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        old, _ = request("/api/health")
                        break
                    except OSError:
                        if previous.poll() is not None or time.monotonic() > deadline:
                            self.fail((root / "console.log").read_text())
                        time.sleep(0.1)
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    request("/api/manager/install-update", {})
                self.assertIn(denied.exception.code, (401, 403))
                _, headers = request("/api/auth/login", {"username": "admin", "password": password})
                cookie = headers["Set-Cookie"].split(";")[0]
                admin_cookie = cookie
                _, headers = request("/api/auth/login", {"username": "reader", "password": "reader-pass"})
                cookie = headers["Set-Cookie"].split(";")[0]
                with self.assertRaises(urllib.error.HTTPError) as forbidden:
                    request("/api/manager/install-update", {})
                self.assertEqual(403, forbidden.exception.code)
                with self.assertRaises(urllib.error.HTTPError) as forbidden:
                    request("/api/manager/update-status")
                self.assertEqual(403, forbidden.exception.code)
                cookie = admin_cookie
                if channel:
                    with self.assertRaises(urllib.error.HTTPError):
                        request("/api/manager/install-update", {"channel": channel})
                    checked, _ = request("/api/manager/check-update", {"channel": channel})
                    self.assertEqual(channel, checked["manager_updates"]["channel"])
                    self.assertEqual(target_version, checked["manager_updates"]["latest_version"])
                    self.assertTrue(checked["manager_updates"]["update_available"])
                    saved = runtime.read_json(app / "data" / "manager_config.json")
                    self.assertEqual(channel, saved["manager_updates"]["channel"])
                cross_origin = urllib.request.Request(base + "/api/manager/install-update", data=b"{}",
                    headers={"Cookie": cookie, "Origin": "https://wrong.invalid", "Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as forbidden:
                    urllib.request.urlopen(cross_origin, timeout=2)
                self.assertEqual(403, forbidden.exception.code)
                if browser:
                    expected = manager.APP_VERSION if broken else "99.0.0"
                    subprocess.run(["node", str(ROOT / "dist" / "verify_remote_update.cjs"), base, password, expected], check=True, timeout=60)
                else:
                    accepted, _ = request("/api/manager/install-update", {"channel": channel} if channel else {})
                    self.assertEqual("waiting", accepted["operation"]["phase"])
                deadline = time.monotonic() + 25
                result = None
                while time.monotonic() < deadline:
                    try:
                        status, _ = request("/api/manager/update-status")
                        if status["operation"].get("phase") in {"complete", "rolled_back", "error"}:
                            result = status
                            break
                    except OSError:
                        pass
                    time.sleep(0.2)
                self.assertIsNotNone(result, (root / "console.log").read_text())
                self.assertEqual("rolled_back" if broken else "complete", result["operation"]["phase"], result)
                self.assertEqual(running_version if broken else target_version, result["version"])
                self.assertNotEqual(old["boot_id"], result["boot_id"])
                auth, _ = request("/api/auth/state")
                self.assertTrue(auth["authenticated"])
                self.assertIsNone(sentinel.poll())
                self.assertEqual("keep", (app / "data" / "preserve.txt").read_text())
                previous.wait(timeout=5)
            finally:
                status = runtime.read_json(app / "data" / "manager_updates" / "status.json")
                pids = {status.get("pid")}
                for ready in (app / "data" / "manager_updates").glob("*/helper-ready.json"):
                    pids.add(runtime.read_json(ready).get("pid"))
                for pid in pids:
                    if isinstance(pid, int) and pid != os.getpid():
                        try:
                            os.kill(pid, signal.SIGTERM)
                        except OSError:
                            pass
                for process in (previous, sentinel):
                    if process.poll() is None:
                        process.terminate()
                    process.wait(timeout=10)
                console.close()
                time.sleep(0.3)

    def test_remote_update_restarts_and_keeps_session_and_other_process(self):
        self.run_scenario()

    def test_failed_start_restores_previous_version_and_session(self):
        self.run_scenario(broken=True)

    def test_check_beta_without_save_then_install_restarts_into_beta(self):
        self.run_scenario(channel="beta")

    def test_uncheck_beta_without_save_then_install_restarts_into_stable(self):
        self.run_scenario(channel="stable")
