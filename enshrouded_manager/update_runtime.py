"""Independent manager update runner. Copied into data before the manager exits."""
import ctypes
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request


ACTIVE_PHASES = {"waiting", "downloading", "verifying", "preparing", "restarting", "rolling_back"}


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {} if default is None else default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def set_status(path, phase, message, **values):
    state = read_json(path)
    state.update(phase=phase, message=message, updated_at=time.time(), **values)
    atomic_json(path, state)
    return state


def replace_files(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or not (source / "manager.py").is_file():
        raise ValueError("Invalid manager replacement source")
    if destination.name != "enshrouded_manager" or not (destination / "data").is_dir():
        raise ValueError("Invalid manager destination")
    for item in destination.iterdir():
        if item.name == "data":
            continue
        if item.is_symlink() or item.is_file():
            item.unlink()
        elif item.is_dir():
            if item.resolve().parent != destination:
                raise ValueError("Manager directory escapes the installation")
            shutil.rmtree(item)
    for item in source.iterdir():
        if item.name in {"data", "__pycache__"}:
            continue
        if item.is_symlink():
            raise ValueError("Update package contains a symbolic link")
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def parent_exited(pid, timeout=45):
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                return True
            raise OSError("Cannot monitor the previous manager process")
        try:
            return kernel.WaitForSingleObject(handle, int(timeout * 1000)) == 0
        finally:
            kernel.CloseHandle(handle)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.2)
    return False


def launch(plan):
    environment = dict(os.environ, ESM_UPDATE_RESTART="1")
    options = {"cwd": plan["root"], "stdin": subprocess.DEVNULL, "env": environment}
    if os.name == "nt":
        options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    with Path(plan["console_log"]).open("ab") as output:
        return subprocess.Popen(plan["command"], stdout=output, stderr=subprocess.STDOUT, **options)


def healthy(plan, process, version):
    deadline = time.monotonic() + plan.get("health_timeout", 60)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with opener.open(plan["health_url"], timeout=2) as response:
                data = json.load(response)
            if data.get("version") == version and data.get("pid") == process.pid and data.get("ready"):
                return True
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    return False


def run(plan):
    status = Path(plan["status"])
    app = Path(plan["app"]).resolve()
    data = app / "data"
    job = Path(plan["job"]).resolve()
    if not job.is_relative_to(data.resolve() / "manager_updates"):
        raise ValueError("Update job is outside manager data")
    for key in ("source", "backup"):
        if not Path(plan[key]).resolve().is_relative_to(job):
            raise ValueError("Update source or backup is outside its job")
    atomic_json(job / "helper-ready.json", {"pid": os.getpid()})
    if not parent_exited(plan["parent_pid"]):
        set_status(status, "error", "Previous manager did not exit; files were not replaced.")
        return
    process = None
    try:
        replace_files(plan["source"], app)
        process = launch(plan)
        set_status(status, "restarting", "Checking the updated manager's startup.", pid=process.pid)
        if not healthy(plan, process, plan["target_version"]):
            raise RuntimeError("The updated manager did not pass its startup health check")
        set_status(status, "complete", f"ESM-Z v{plan['target_version']} is running.", pid=process.pid)
    except Exception as error:
        set_status(status, "rolling_back", "Update startup failed; restoring the previous manager.", error=str(error))
        try:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            replace_files(plan["backup"], app)
            config_path = data / "manager_config.json"
            config = read_json(config_path)
            config.setdefault("manager_updates", {}).update(
                restart_required=False, installed_pending_version="", last_error=f"Update rolled back: {error}")
            atomic_json(config_path, config)
            process = launch(plan)
            set_status(status, "rolling_back", "Checking the restored manager's startup.", pid=process.pid)
            if not healthy(plan, process, plan["previous_version"]):
                raise RuntimeError("The previous manager could not be restarted; inspect update-console.log")
            set_status(status, "rolled_back", "The previous manager was restored and is running.", error=str(error), pid=process.pid)
        except Exception as rollback_error:
            set_status(status, "error", f"Update recovery needs attention: {rollback_error}", error=str(error))


if __name__ == "__main__":
    run(read_json(sys.argv[1]))
