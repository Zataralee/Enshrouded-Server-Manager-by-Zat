"""Scoped log discovery and bounded-memory downloads; never accept host paths."""
import datetime as dt
import os
import re
import stat
from pathlib import Path


CHUNK_SIZE = 256 * 1024
STEAM_TEXT_LOG = re.compile(r"(?:[a-z0-9_]+_log(?:_[0-9]+)?|system[a-z0-9_]+)\.txt", re.I)
JOB_ID = re.compile(r"[0-9a-f]{32}")


def _reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _directory(path):
    """Do not follow a log directory that has been replaced with a junction."""
    info = path.lstat()
    if _reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise PermissionError("Linked log directories are not available for download")


def _safe_file(root, relative):
    parts = relative.split("/")
    if any(not p or p in {".", ".."} or any(c in p for c in '\\:\x00\r\n') for p in parts):
        raise PermissionError("Invalid log identifier")
    _directory(root)
    path = root
    for part in parts[:-1]:
        path = path / part
        _directory(path)
    path = path / parts[-1]
    info = path.lstat()
    if _reparse(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise PermissionError("Only regular log files can be downloaded")
    path.resolve(strict=True).relative_to(root.resolve(strict=True))
    return path, info


def _server_log_name(name):
    return name.lower().endswith(".log") or bool(STEAM_TEXT_LOG.fullmatch(name))


class LogCatalog:
    def __init__(self, app_dir, server_dir=None, admin=False):
        self.app_dir = Path(app_dir)
        self.server_dir = Path(server_dir) if server_dir is not None else None
        self.admin = admin

    def resolve(self, log_id):
        if not isinstance(log_id, str) or len(log_id) > 512:
            raise PermissionError("Invalid log identifier")
        group, separator, name = log_id.partition(":")
        if not separator or not name:
            raise PermissionError("Invalid log identifier")
        if group in {"server", "archive"}:
            if self.server_dir is None or "/" in name or not _server_log_name(name):
                raise PermissionError("This server log is not available")
            root = self.server_dir / "logs"
            _directory(self.server_dir)
            return _safe_file(root, ("backup/" if group == "archive" else "") + name)
        if not self.admin:
            raise PermissionError("Manager logs require an administrator")
        _directory(self.app_dir)
        root = self.app_dir / "data"
        if group == "manager" and name == "manager.log":
            return _safe_file(root, name)
        if group == "updates" and name == "update-console.log":
            return _safe_file(root, "manager_updates/" + name)
        if group == "job":
            job, sep, filename = name.partition("/")
            if sep and JOB_ID.fullmatch(job) and filename == "helper.log":
                return _safe_file(root, "manager_updates/" + job + "/helper.log")
        raise PermissionError("This file is not an approved log")

    def list(self):
        items = []
        unavailable = []

        def add(log_id, label, scope):
            try:
                path, info = self.resolve(log_id)
            except FileNotFoundError:
                return
            except (OSError, ValueError):
                if scope not in unavailable:
                    unavailable.append(scope)
                return
            items.append({"id": log_id, "name": label, "scope": scope,
                          "size": info.st_size,
                          "modified": dt.datetime.fromtimestamp(info.st_mtime, dt.timezone.utc).isoformat()})

        def scan(root, group, scope, archived=False):
            try:
                _directory(root)
                with os.scandir(root) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False) and _server_log_name(entry.name):
                            add(group + ":" + entry.name,
                                ("backup/" if archived else "") + entry.name, scope)
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                if scope not in unavailable:
                    unavailable.append(scope)

        if self.server_dir is not None:
            scan(self.server_dir / "logs", "server", "Server")
            # Explicitly bounded depth: never recurse into saves, mods or update packages.
            try:
                _directory(self.server_dir / "logs")
                scan(self.server_dir / "logs" / "backup", "archive", "Archived server", True)
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                if "Archived server" not in unavailable:
                    unavailable.append("Archived server")
        if self.admin:
            add("manager:manager.log", "manager.log", "Manager")
            add("updates:update-console.log", "update-console.log", "Manager updates")
            root = self.app_dir / "data" / "manager_updates"
            try:
                _directory(self.app_dir)
                _directory(self.app_dir / "data")
                _directory(root)
                with os.scandir(root) as entries:
                    for entry in entries:
                        if JOB_ID.fullmatch(entry.name) and entry.is_dir(follow_symlinks=False):
                            add("job:" + entry.name + "/helper.log", entry.name + "/helper.log", "Manager updates")
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                if "Manager updates" not in unavailable:
                    unavailable.append("Manager updates")
        items.sort(key=lambda item: (item["modified"], item["id"]), reverse=True)
        return {"logs": items, "unavailable": unavailable}

    def open(self, log_id):
        path, before = self.resolve(log_id)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(descriptor)
            _, after = self.resolve(log_id)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino):
                raise PermissionError("The log changed during download preparation; refresh and retry")
            # A hard link must not turn an allowed log name into a sensitive file alias.
            if opened.st_nlink != 1:
                raise PermissionError("Linked log files are not available for download")
            return os.fdopen(descriptor, "rb"), opened.st_size, path.name
        except BaseException:
            os.close(descriptor)
            raise


def copy_snapshot(source, destination, size):
    """Send exactly the initial file length, ignoring later appends."""
    remaining = size
    while remaining:
        chunk = source.read(min(CHUNK_SIZE, remaining))
        if not chunk:
            raise OSError("The log was truncated during download; refresh and retry")
        destination.write(chunk)
        remaining -= len(chunk)
