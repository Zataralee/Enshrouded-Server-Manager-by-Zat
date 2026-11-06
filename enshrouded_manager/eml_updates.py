"""Verified upstream EML releases, independent of manager and mod updates."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.request
import zipfile

from eml_support import EML_VERSION, EML_SHA256, digest, contained
from update_runtime import atomic_json

REPOSITORY = "Brabb3l/kfc-parser"
API = "https://api.github.com/repos/" + REPOSITORY
WEB = "https://github.com/" + REPOSITORY
CHECK_INTERVAL = 6 * 3600
LOCK = threading.RLock()
CURRENT = object()


def version(value):
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", str(value))
    if not match:
        raise ValueError("EML release must have a stable semantic version")
    return tuple(map(int, match.groups()))


def fetch(url, maximum):
    # Initial URLs are constructed or validated against the fixed upstream repo.
    request = urllib.request.Request(url, headers={"User-Agent": "ESM-Z-EML-updater", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.url.startswith("https://"):
            raise ValueError("EML download redirected away from HTTPS")
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("EML download exceeds the size limit")
    return data


def release_info(release):
    tag = release.get("tag_name", "")
    normalized = ".".join(map(str, version(tag)))
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Only published stable EML releases are supported")
    assets = [asset for asset in release.get("assets", []) if asset.get("name") == "emm.exe"]
    if len(assets) != 1:
        raise ValueError("Upstream release does not contain one Windows emm.exe")
    asset = assets[0]
    if asset.get("browser_download_url") != WEB + "/releases/download/" + tag + "/emm.exe":
        raise ValueError("Unexpected EML download destination")
    checksum = asset.get("digest", "") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", checksum):
        # Historic GitHub assets may lack a digest. Only the shipped pin is known.
        checksum = "sha256:" + EML_SHA256 if normalized == EML_VERSION else ""
    return {"version": normalized, "tag": tag, "release_url": WEB + "/releases/tag/" + tag,
            "download_url": asset["browser_download_url"], "sha256": checksum.removeprefix("sha256:"),
            "notes": str(release.get("body") or "")[:16000], "published_at": release.get("published_at", "")}


class Updater:
    def __init__(self, data, bundled):
        self.root = Path(data) / "eml_runtime"
        self.bundled = Path(bundled) / "eml-v0.2.0" / "emm.exe"
        self.path = self.root / "current.json"
        self.check_path = self.root / "check.json"

    def read(self, path):
        if not path.exists():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Invalid EML updater metadata")
        return value

    def descriptor(self, record=CURRENT):
        if record is CURRENT:
            record = self.read(self.path).get("active")
        if not record:
            return {"version": EML_VERSION, "sha256": EML_SHA256, "tool": self.bundled, "bundled": True}
        selected = ".".join(map(str, version(record["version"])))
        checksum = record.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid installed EML checksum")
        directory = contained(self.root, self.root / "releases" / (selected + "-" + checksum))
        return {"version": selected, "sha256": checksum, "tool": contained(self.root, directory / "emm.exe"), "bundled": False}

    def status(self):
        with LOCK:
            installed = self.descriptor()
            checked = self.read(self.check_path)
            candidate = checked.get("release", {})
            newer = bool(candidate and version(candidate["version"]) > version(installed["version"]))
            return {"installed_version": installed["version"], "bundled": installed["bundled"],
                    "latest_version": candidate.get("version", ""), "update_available": newer,
                    "install_available": newer and bool(candidate.get("sha256")),
                    "rollback_available": bool(self.read(self.path).get("active")),
                    "last_checked": checked.get("checked_at", 0), "last_error": checked.get("error", ""),
                    "release_url": candidate.get("release_url", WEB + "/releases"),
                    "notes": candidate.get("notes", ""), "check_interval_hours": CHECK_INTERVAL // 3600,
                    "verification_message": "" if not newer or candidate.get("sha256") else
                    "Upstream has not published a SHA-256 digest; installation is unavailable."}

    def check(self, force=False):
        with LOCK:
            cached = self.read(self.check_path)
            if not force and time.time() - cached.get("checked_at", 0) < CHECK_INTERVAL:
                return self.status()
            try:
                release = release_info(json.loads(fetch(API + "/releases/latest", 2 * 1024 * 1024)))
                atomic_json(self.check_path, {"checked_at": time.time(), "release": release, "error": ""})
            except Exception as error:
                atomic_json(self.check_path, {**cached, "checked_at": time.time(), "error": str(error)})
            return self.status()

    def install(self, expected_version):
        with LOCK:
            requested = ".".join(map(str, version(expected_version)))
            # Re-fetch metadata, rather than trusting a browser-supplied URL/hash.
            release = release_info(json.loads(fetch(API + "/releases/latest", 2 * 1024 * 1024)))
            if release["version"] != requested:
                raise RuntimeError("The upstream release changed. Check for EML updates again.")
            if version(requested) <= version(self.descriptor()["version"]):
                raise RuntimeError("There is no newer EML release to install")
            if not release["sha256"]:
                raise RuntimeError("Upstream has not published a SHA-256 digest for this EML binary")
            binary = fetch(release["download_url"], 64 * 1024 * 1024)
            if hashlib.sha256(binary).hexdigest() != release["sha256"]:
                raise RuntimeError("Downloaded EML tool failed SHA-256 verification")
            if not binary.startswith(b"MZ"):
                raise RuntimeError("Downloaded EML tool is not a Windows executable")
            source = fetch(API + "/zipball/" + release["tag"], 32 * 1024 * 1024)
            with zipfile.ZipFile(io.BytesIO(source)) as archive:
                licenses = [info for info in archive.infolist() if len(Path(info.filename).parts) == 2
                            and Path(info.filename).name == "LICENSE" and info.file_size < 1024 * 1024]
                if len(licenses) != 1:
                    raise RuntimeError("Upstream source archive does not contain its license")
                license_text = archive.read(licenses[0])
            releases = contained(self.root, self.root / "releases")
            releases.mkdir(parents=True, exist_ok=True)
            temporary = contained(self.root, releases / ("staging-" + secrets.token_hex(12)))
            temporary.mkdir()
            destination = contained(self.root, releases / (requested + "-" + release["sha256"]))
            try:
                (temporary / "emm.exe").write_bytes(binary)
                (temporary / "source.zip").write_bytes(source)
                (temporary / "LICENSE").write_bytes(license_text)
                atomic_json(temporary / "release.json", release)
                result = subprocess.run([str(temporary / "emm.exe"), "--version"], cwd=temporary,
                                        stdin=subprocess.DEVNULL, capture_output=True, timeout=15,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                output = result.stdout.decode("utf-8", errors="replace")
                if result.returncode or not re.search(r"(?<![\d.])" + re.escape(requested) + r"(?![\d.])", output):
                    raise RuntimeError("The downloaded EML tool failed its version startup check; current EML was preserved")
                help_result = subprocess.run([str(temporary / "emm.exe"), "run", "--help"], cwd=temporary,
                                             stdin=subprocess.DEVNULL, capture_output=True, timeout=15,
                                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                help_text = help_result.stdout.decode("utf-8", errors="replace")
                if help_result.returncode or any(flag not in help_text for flag in ["--patch", "--force", "--game-directory", "--file-name"]):
                    raise RuntimeError("The upstream EML command interface is incompatible with this manager; current EML was preserved")
                if destination.exists():
                    if digest(destination / "emm.exe") != release["sha256"]:
                        raise RuntimeError("An existing EML release directory failed verification")
                else:
                    temporary.rename(destination)
                current = self.read(self.path)
                atomic_json(self.path, {"active": {"version": requested, "sha256": release["sha256"]},
                                        "previous": current.get("active"), "installed_at": time.time()})
                atomic_json(self.check_path, {"checked_at": time.time(), "release": release, "error": ""})
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            return self.status()

    def rollback(self):
        with LOCK:
            current = self.read(self.path)
            if not current.get("active"):
                raise RuntimeError("The bundled EML tool is already selected")
            previous = self.descriptor(current.get("previous"))
            if not previous["tool"].is_file() or digest(previous["tool"]) != previous["sha256"]:
                raise RuntimeError("Previous EML tool failed SHA-256 verification")
            atomic_json(self.path, {"active": current.get("previous"), "previous": None,
                                    "rolled_back_at": time.time()})
            return self.status()
