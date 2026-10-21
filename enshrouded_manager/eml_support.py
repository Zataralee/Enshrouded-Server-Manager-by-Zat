"""ESM-Z adapter for the unmodified upstream EML command-line release.

The caller serializes all mutations with the instance supervisor lock and checks
that the dedicated server is stopped. No game client installation is used.
"""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile


EML_VERSION = "0.2.0"
EML_SHA256 = "b1133f6b8ea7000596cc7710901bd8307b48165b0e650c0487a611d90ea49305"
MAX_UPLOAD = 32 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_CONFIG = 256 * 1024
MOD_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
TEXT_SUFFIXES = {".json", ".lua", ".toml", ".ini", ".cfg", ".txt"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def contained(root, path):
    root, path = Path(root).resolve(), Path(path)
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escapes the managed mod directory")
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Linked directories are not supported for mods")
    return path


def validate_manifest(value):
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not MOD_ID.fullmatch(value["id"]):
        raise ValueError("mod.json needs an EML id (lowercase letter followed by letters, numbers, - or _)")
    if not isinstance(value.get("name"), str) or not value["name"].strip():
        raise ValueError("mod.json needs a name")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][a-zA-Z0-9.+-]+)?", str(value.get("version", ""))):
        raise ValueError("mod.json needs a semantic version, such as 1.0.0")
    if value.get("capabilities") != ["patch"]:
        raise ValueError("This beta supports upstream EML Lua patch mods only (capabilities: [\"patch\"])")
    if value.get("dependencies"):
        raise ValueError("Mod dependencies are not supported in this beta; install a self-contained patch mod")
    return value


class EML:
    def __init__(self, server, storage, tool):
        self.server = Path(server).resolve()
        self.storage = Path(storage)
        self.tool = Path(tool)
        self.state_path = self.storage / "state.json"
        self.kfc = self.server / "enshrouded_server.kfc"
        self.exe = self.server / "enshrouded_server.exe"
        self.backup = self.storage / "original.kfc"
        self.log_path = self.server / "logs" / "esm-eml.log"

    def state(self):
        if self.state_path.exists():
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            if value.get("server") != str(self.server):
                raise RuntimeError("The instance directory changed; restore its original EML installation first")
            return value
        return {"server": str(self.server), "enabled": False, "mods": {}, "baseline": {}, "patched": False}

    def save(self, state):
        write_json(self.state_path, state)

    def status(self):
        state = self.state()
        return {"version": EML_VERSION, "installed": self.tool.is_file(), "enabled": state["enabled"],
                "patched": state.get("patched", False), "recovery_required": state.get("recovery_required", False),
                "last_error": state.get("last_error", ""), "last_applied": state.get("last_applied", ""),
                "mods": list(state["mods"].values())}

    def check_tool(self):
        if not self.tool.is_file() or digest(self.tool) != EML_SHA256:
            raise RuntimeError("The bundled upstream EML tool is missing or failed SHA-256 verification. Reinstall the beta package.")

    def check_server(self):
        if not self.exe.is_file() or not self.kfc.is_file():
            raise RuntimeError("Install the dedicated server before enabling EML")
        for name in ("dbghelp.dll", "dinput8.dll", "winmm.dll", "powrprof.dll"):
            if (self.server / name).exists():
                raise RuntimeError(f"Existing {name} detected. Use a clean dedicated server for the EML beta.")
        contained(self.server, self.server / "mods")
        contained(self.server, self.server / ".cache")
        state = self.state()
        root = self.server / "mods"
        if root.exists():
            for child in root.iterdir():
                contained(root, child)
                if child.name not in state["mods"] or not state["mods"][child.name]["enabled"]:
                    raise RuntimeError(f"Unmanaged file in server mods directory: {child.name}. Use a clean mods directory.")
        for mod_id, mod in state["mods"].items():
            if mod["enabled"] and not (root / mod_id / "src/mod.lua").is_file():
                raise RuntimeError(f"Enabled mod {mod_id} is missing files. Disable and reinstall it before starting.")

    def command(self, arguments):
        self.check_tool()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("ab") as log:
            log.write(("\nESM-Z: emm " + " ".join(arguments) + "\n").encode())
            log.flush()
            result = subprocess.run([str(self.tool), *arguments, "-g", str(self.server),
                                     "--file-name", "enshrouded_server"], cwd=self.server,
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise RuntimeError(f"EML exited with code {result.returncode}. See the EML log.")
        # Some upstream CLI validation errors return exit code zero.
        lines = self.log_path.read_text(encoding="utf-8", errors="replace").split("ESM-Z: emm ")[-1]
        if re.search(r"\bERROR\b", lines):
            raise RuntimeError("EML reported an error. See the EML log.")
        if "--patch" in arguments and not re.search(r"Applied \d+ patches", lines):
            raise RuntimeError("EML did not confirm patch completion. See the EML log.")

    def ensure_baseline(self):
        state = self.state()
        if state.get("recovery_required"):
            raise RuntimeError("EML recovery is required. Run a Steam update/validate before starting this server.")
        if not state["baseline"]:
            if self.kfc.with_suffix(".kfc.bak").exists():
                raise RuntimeError("An existing EML backup was found. Start with a clean Steam-validated server.")
            self.storage.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.kfc, self.backup)
            state["baseline"] = {"exe": digest(self.exe), "kfc": digest(self.kfc)}
            self.save(state)
        elif digest(self.exe) != state["baseline"]["exe"]:
            raise RuntimeError("The server build changed outside ESM-Z. Run a Steam update/validate before applying mods.")

    def restore(self):
        state = self.state()
        if not state.get("patched"):
            return
        base = state["baseline"]
        if digest(self.exe) != base["exe"]:
            raise RuntimeError("Refusing to restore an EML backup from a different server build. Run a Steam update/validate.")
        if not self.backup.exists() or digest(self.backup) != base["kfc"]:
            raise RuntimeError("Original game backup failed verification. Run a Steam update/validate.")
        # The original index references the original data containers. EML's extra
        # containers may remain on disk but are no longer referenced by the game.
        temporary = self.kfc.with_suffix(".esm-restore.tmp")
        shutil.copy2(self.backup, temporary)
        temporary.replace(self.kfc)
        state.update(patched=False, last_error="")
        self.save(state)

    def prepare_update(self):
        state = self.state()
        if not state["baseline"]:
            return
        try:
            self.restore()
        except RuntimeError:
            # Steam validation is the recovery path; never restore stale assets.
            pass
        state = self.state()
        state["recovery_required"] = True
        self.save(state)

    def finish_update(self):
        state = self.state()
        if not state.get("recovery_required"):
            return
        upstream_backup = self.kfc.with_suffix(".kfc.bak")
        if upstream_backup.exists():
            retired = self.storage / ("retired-" + str(time.time_ns()) + ".kfc.bak")
            upstream_backup.replace(retired)
        state.update(baseline={}, patched=False, recovery_required=False, last_error="")
        self.save(state)

    def enable(self, enabled):
        self.check_server()
        if enabled:
            self.check_tool()
            self.ensure_baseline()
        else:
            self.restore()
        state = self.state()
        if not enabled and state.get("recovery_required"):
            raise RuntimeError("Run a Steam update/validate before disabling EML")
        state["enabled"] = bool(enabled)
        self.save(state)
        return self.status()

    def apply(self):
        state = self.state()
        if state.get("recovery_required"):
            raise RuntimeError("An interrupted EML/Steam update requires a successful Steam update/validate before starting")
        if not state["enabled"]:
            return
        self.check_server()
        self.ensure_baseline()
        self.restore()
        state = self.state()
        upstream_backup = self.kfc.with_suffix(".kfc.bak")
        if upstream_backup.exists() and digest(upstream_backup) != state["baseline"]["kfc"]:
            raise RuntimeError("EML's backup does not match this installation. Run a Steam update/validate.")
        if digest(self.kfc) != state["baseline"]["kfc"]:
            raise RuntimeError("Game assets changed outside ESM-Z. Run a Steam update/validate.")
        if not any(mod["enabled"] for mod in state["mods"].values()):
            return
        state["patched"] = True  # Persist before running; interrupted patches must be restored.
        self.save(state)
        try:
            self.command(["run", "--patch", "--force"])
            state = self.state()
            state.update(last_error="", last_applied=time.strftime("%Y-%m-%d %H:%M:%S"))
            self.save(state)
        except Exception as exc:
            try:
                self.restore()
            finally:
                state = self.state()
                state["last_error"] = str(exc)
                self.save(state)
            raise

    def import_zip(self, payload):
        if len(payload) > MAX_UPLOAD:
            raise ValueError("Mod ZIP is larger than 32 MiB")
        self.check_server()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive, tempfile.TemporaryDirectory(prefix="esm-mod-") as temporary:
            items = archive.infolist()
            if len(items) > 2000 or sum(item.file_size for item in items) > MAX_EXPANDED:
                raise ValueError("Mod ZIP exceeds the 2,000-file or 128 MiB expanded limit")
            names = set()
            for item in items:
                path = PurePosixPath(item.filename)
                components = path.parts
                if (not components or path.is_absolute() or "\\" in item.orig_filename or "\x00" in item.orig_filename
                        or any(part in {".", ".."} or ":" in part or part.endswith((".", " "))
                               or re.fullmatch(r"(?i)(con|prn|aux|nul|com\d|lpt\d)(\..*)?", part) for part in components)
                        or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1):
                    raise ValueError("Unsafe or unsupported ZIP path")
                key = item.filename.rstrip("/").casefold()
                if key in names:
                    raise ValueError("Duplicate ZIP path")
                names.add(key)
                if path.suffix.lower() in {".dll", ".exe", ".bat", ".cmd", ".ps1", ".com", ".msi"}:
                    raise ValueError("Native loaders and executable files are not accepted as Lua patch mods")
            manifests = [item for item in items if PurePosixPath(item.filename).name == "mod.json" and not item.is_dir()]
            if len(manifests) != 1:
                raise ValueError("Upload one EML mod per ZIP, containing exactly one mod.json")
            if manifests[0].file_size > MAX_CONFIG:
                raise ValueError("mod.json is too large")
            manifest = validate_manifest(json.loads(archive.read(manifests[0]).decode("utf-8-sig")))
            prefix = PurePosixPath(manifests[0].filename).parent
            entry = str(prefix / "src" / "mod.lua")
            if entry not in archive.namelist():
                raise ValueError("EML mod is missing src/mod.lua")
            stage = Path(temporary) / manifest["id"]
            stage.mkdir()
            for item in items:
                if item.is_dir():
                    continue
                source = PurePosixPath(item.filename)
                if not source.is_relative_to(prefix):
                    raise ValueError("ZIP includes files outside the mod folder")
                relative = source.relative_to(prefix)
                target = contained(stage, stage / str(relative))
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as incoming, target.open("wb") as output:
                    shutil.copyfileobj(incoming, output)
            state = self.state()
            mod_id = manifest["id"]
            if mod_id in state["mods"]:
                raise ValueError("This mod id is already installed. Remove it before installing a replacement.")
            destination = contained(self.storage, self.storage / "packages" / mod_id)
            if destination.exists() or (self.server / "mods" / mod_id).exists():
                raise ValueError("A folder already exists for this mod id")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage, destination)
            state["mods"][mod_id] = {"id": mod_id, "name": manifest["name"], "version": manifest["version"],
                                     "enabled": False, "multiplayer": "Unverified; check the author's client requirements",
                                     "sha256": hashlib.sha256(payload).hexdigest()}
            self.save(state)
        return self.status()

    def change_mod(self, mod_id, action):
        self.check_server()
        state = self.state()
        if mod_id not in state["mods"] or action not in {"enable", "disable", "remove"}:
            raise ValueError("Unknown mod or action")
        self.restore()
        state = self.state()
        source = contained(self.storage, self.storage / "packages" / mod_id)
        target = contained(self.server, self.server / "mods" / mod_id)
        if action == "enable":
            if target.exists():
                return self.status()
            # Reject locally introduced links as well as malicious ZIP entries.
            for path in source.rglob("*"):
                contained(source, path)
            shutil.copytree(source, target)
            state["mods"][mod_id]["enabled"] = True
        else:
            if target.exists():
                shutil.rmtree(target)
            state["mods"][mod_id]["enabled"] = False
            if action == "remove":
                shutil.rmtree(source)
                del state["mods"][mod_id]
        self.save(state)
        return self.status()

    def config_file(self, mod_id, relative=None, content=None):
        state = self.state()
        if mod_id not in state["mods"]:
            raise ValueError("Unknown mod")
        root = contained(self.storage, self.storage / "packages" / mod_id)
        files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
                 and p.suffix.lower() in TEXT_SUFFIXES and p.name != "mod.json" and p.stat().st_size <= MAX_CONFIG]
        if relative is None:
            return {"files": sorted(files)}
        if relative not in files:
            raise ValueError("Unknown or unsupported mod configuration file")
        target = contained(root, root / relative)
        if content is not None:
            if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_CONFIG:
                raise ValueError("Configuration exceeds 256 KiB")
            if target.suffix == ".json":
                json.loads(content)
            self.restore()
            target.write_text(content, encoding="utf-8")
            if state["mods"][mod_id]["enabled"]:
                active = contained(self.server, self.server / "mods" / mod_id / relative)
                active.write_text(content, encoding="utf-8")
        return {"files": sorted(files), "content": target.read_text(encoding="utf-8-sig")}

    def log(self):
        if not self.log_path.exists():
            return "No EML patch run yet. Enabled mods are applied before server start."
        with self.log_path.open("rb") as stream:
            stream.seek(max(0, self.log_path.stat().st_size - 32000))
            return stream.read().decode("utf-8", errors="replace")
