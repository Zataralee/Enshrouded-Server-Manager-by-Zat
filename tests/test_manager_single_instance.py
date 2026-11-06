import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("single_instance_manager", ROOT / "enshrouded_manager/manager.py")
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
runtime = manager.update_runtime


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="esm-single-instance-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "enshrouded_manager"
        self.data = self.app / "data"; self.data.mkdir(parents=True)
        for name in ["manager.py", "eml_support.py", "eml_updates.py", "update_runtime.py", "log_downloads.py"]:
            shutil.copy2(ROOT / "enshrouded_manager" / name, self.app / name)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); self.port = sock.getsockname()[1]
        cfg = manager.default_config()
        cfg.update(bind_host="127.0.0.1", port=self.port, instances=[], backup_root=str(self.root / "backups"))
        cfg["manager_updates"]["enabled"] = False
        self.config = self.data / "manager_config.json"
        self.config.write_text(json.dumps(cfg))
        self.command = [sys.executable, "-u", "-c", f'''
import importlib.util
s=importlib.util.spec_from_file_location("fixture",{str(self.app / 'manager.py')!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.monitor_loop=lambda:None
m.eml_update_loop=lambda:None
m.main()
''']
        self.processes = []
        self.addCleanup(self.stop)

    def stop(self):
        for process in self.processes:
            if process.poll() is None:process.kill()
            process.wait(timeout=5)
            if process.stdout:process.stdout.close()

    def launch(self, **environment):
        env = dict(os.environ)
        for key in ["ESM_UPDATE_RESTART", "ESM_UPDATE_HANDOFF"]:env.pop(key, None)
        env.update(environment)
        process = subprocess.Popen(self.command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.processes.append(process)
        return process

    def test_overlapping_config_writes_leave_one_complete_document(self):
        original_dump = json.dump
        outer = {"users": ["owner"], "padding": "a" * 4000}
        inner = {"users": ["owner", "second"], "padding": "b" * 2000}
        observations = []
        before = self.config.read_bytes()
        def interleaved(value, stream, **kwargs):
            # Another writer publishes after this writer opens its temporary file.
            if value is outer:
                stream.write(" ")
                manager.save_json(self.config, inner)
                observations.append(json.loads(self.config.read_text()))
            else:
                self.assertEqual(before, self.config.read_bytes())
            original_dump(value, stream, **kwargs)
        with mock.patch.object(runtime.json, "dump", side_effect=interleaved):
            manager.save_json(self.config, outer)
        self.assertEqual([inner], observations)
        self.assertEqual(outer, json.loads(self.config.read_text()))
        self.assertFalse(list(self.data.glob("*.tmp")))

    def test_failed_config_serialization_preserves_last_good_file(self):
        before = self.config.read_bytes()
        with self.assertRaises(TypeError):
            manager.save_json(self.config, {"partial": "written", "unsupported": object()})
        self.assertEqual(before, self.config.read_bytes())
        self.assertFalse(list(self.data.glob("*.tmp")))

    def test_transient_windows_reader_lock_retries_atomic_replace(self):
        replace = os.replace
        busy = PermissionError('Windows file is open'); busy.winerror = 32
        attempts = []
        def blocked_then_ready(source, destination):
            attempts.append(source)
            if len(attempts) < 3:
                raise busy
            replace(source, destination)
        with mock.patch.object(runtime.os, 'replace', side_effect=blocked_then_ready), \
                mock.patch.object(runtime.time, 'sleep'):
            manager.save_json(self.config, {'saved': True})
        self.assertEqual(3, len(attempts))
        self.assertEqual({'saved': True}, json.loads(self.config.read_text()))

    def test_persistent_windows_lock_retains_last_good_config(self):
        before = self.config.read_bytes()
        busy = PermissionError('Windows file is open'); busy.winerror = 32
        with mock.patch.object(runtime.os, 'replace', side_effect=busy) as replace, \
                mock.patch.object(runtime.time, 'sleep'), self.assertRaises(PermissionError):
            manager.save_json(self.config, {'saved': True})
        self.assertEqual(20, replace.call_count)
        self.assertEqual(before, self.config.read_bytes())
        self.assertFalse(list(self.data.glob('*.tmp')))

    def ready(self, process):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:self.fail(process.stdout.read().decode())
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=1) as response:
                    health = json.load(response)
                if health["pid"] == process.pid:return health
            except OSError:pass
            time.sleep(.1)
        self.fail("Temporary manager did not start")

    def test_second_launch_exits_successfully_before_reading_or_mutating_config(self):
        first = self.launch(); self.ready(first)
        original = self.config.read_bytes()
        self.config.write_text("intentionally invalid config; duplicate must not read it")
        corrupt = self.config.read_bytes()
        duplicate = self.launch()
        output = duplicate.communicate(timeout=5)[0].decode()
        self.assertEqual(0, duplicate.returncode, output)
        self.assertIn("already running", output)
        self.assertIn(str(self.port), output)
        self.assertEqual(corrupt, self.config.read_bytes())
        self.assertIsNone(first.poll())
        self.config.write_bytes(original)

    def test_crash_releases_lock_without_deleting_stale_files(self):
        first = self.launch(); self.ready(first)
        first.kill(); first.wait(5)
        self.assertTrue((self.data / "manager.lock").exists())
        second = self.launch(); self.ready(second)
        self.assertNotEqual(first.pid, second.pid)

    def test_update_gate_blocks_manual_launch_but_allows_exact_handoff_token(self):
        gate = runtime.FileLease(self.data / "manager-update.lock").acquire()
        self.addCleanup(gate.close)
        runtime.atomic_json(self.data / "manager_updates/handoff.json", {"token": "exact-fixture-token"})
        blocked = self.launch(ESM_UPDATE_HANDOFF="wrong-token")
        output = blocked.communicate(timeout=5)[0].decode()
        self.assertEqual(0, blocked.returncode)
        self.assertIn("updating or starting", output)
        successor = self.launch(ESM_UPDATE_HANDOFF="exact-fixture-token")
        self.ready(successor)

    @unittest.skipUnless(os.name == "nt", "Windows exclusive address behavior")
    def test_exclusive_windows_listener_blocks_another_installation(self):
        server = manager.ManagerHTTPServer(("127.0.0.1", 0), manager.Handler)
        self.addCleanup(server.server_close)
        with self.assertRaises(OSError):
            duplicate = manager.ThreadingHTTPServer(server.server_address, manager.Handler)
            duplicate.server_close()

    def test_update_helper_holds_gate_during_replacement_and_until_health_check(self):
        job = self.data / "manager_updates/job"; job.mkdir(parents=True)
        plan = {"app": str(self.app), "job": str(job), "source": str(job / "source"),
                "backup": str(job / "backup"), "status": str(job / "status.json"),
                "parent_pid": 123, "target_version": "new", "previous_version": "old"}
        observed = []
        def guarded(*args):
            with self.assertRaises(runtime.AlreadyRunning):runtime.startup_gate(self.data)
            observed.append(True)
        def launch(selected):
            guarded()
            self.assertIsNone(runtime.startup_gate(self.data, selected["handoff_token"]))
            return mock.Mock(pid=456)
        with mock.patch.object(runtime, "parent_exited", return_value=True), \
                mock.patch.object(runtime, "replace_files", side_effect=guarded), \
                mock.patch.object(runtime, "launch", side_effect=launch), \
                mock.patch.object(runtime, "healthy", side_effect=lambda *args: (guarded() or True)):
            runtime.run(plan)
        self.assertEqual(3, len(observed))
        self.assertEqual("complete", runtime.read_json(plan["status"])["phase"])
        self.assertFalse((self.data / "manager_updates/handoff.json").exists())
        runtime.startup_gate(self.data).close()

    def test_lingering_parent_is_never_replaced_or_killed(self):
        job = self.data / "manager_updates/job"; job.mkdir(parents=True)
        plan = {"app": str(self.app), "job": str(job), "source": str(job / "source"),
                "backup": str(job / "backup"), "status": str(job / "status.json"), "parent_pid": 123}
        with mock.patch.object(runtime, "parent_exited", return_value=False), \
                mock.patch.object(runtime, "replace_files") as replace, mock.patch.object(runtime, "launch") as launch:
            runtime.run(plan)
        replace.assert_not_called(); launch.assert_not_called()
        self.assertIn("did not exit", runtime.read_json(plan["status"])["message"])


if __name__ == "__main__":unittest.main()
