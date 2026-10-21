import base64
import datetime as dt
import ftplib
import hashlib
import hmac
import io
import json
import os
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
import ctypes
import re
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


APP_VERSION = "0.9.6.3a"
UPDATE_RESTART_PROTOCOL = 1
UPDATE_LOG = [
    {
        "version": "0.9.6.3a",
        "date": "2026-10-21",
        "changes": [
            "Check for Updates now uses and saves the beta checkbox directly, without saving unrelated Manager settings.",
            "Channel switches use the download, install, automatic restart, and browser reconnection flow.",
            "Prevented stale channel results from enabling installation of the wrong release.",
        ],
    },
    {
        "version": "0.9.6.2a",
        "date": "2026-10-21",
        "changes": [
            "Added remote one-click manager updates with automatic restart, browser reconnection, and startup-health rollback.",
            "Preserved remote login sessions across manager restarts and invalidated sessions after password changes or logout.",
            "Staged updates outside live code and waited for active server operations; game server processes remain online.",
        ],
    },
    {
        "version": "0.9.6.1a",
        "date": "2026-10-20",
        "changes": [
            "Added a Run beta version checkbox in Manager settings for the Windows beta channel.",
            "Added four-part version comparison and switching back from beta to its stable release.",
            "Kept EML integration exclusive to the beta package.",
        ],
    },
    {
        "version": "0.9.6",
        "date": "2026-10-19",
        "changes": [
            "Fixed fresh-install Missing configuration failures by loading Enshrouded's Steam app metadata before installing or updating.",
            "Added one bounded retry for Enshrouded metadata failures and included Steam content and app-info diagnostics in server logs.",
            "Stopped saves and backups polling without a selected server and cleared stale browser instance selections.",
        ],
    },
    {
        "version": "0.9.5",
        "date": "2026-10-19",
        "changes": [
            "Initialized SteamCMD separately before game downloads and handled its first-run exit code 7 with bounded retries.",
            "Included current SteamCMD bootstrap diagnostics in server logs and stopped reporting localization warnings as the main failure.",
            "Added Retry Install for failed or interrupted installs while reusing the existing instance, directory, and selected port.",
            "Made new install registration immediately visible and prevented duplicate install jobs for the same instance.",
            "Quieted successful background API polling in the console while retaining errors and install progress.",
        ],
    },
    {
        "version": "0.9.4",
        "date": "2026-10-16",
        "changes": [
            "Added automatic backup and one-time Steam manifest recovery for Enshrouded update failures with state 0x6.",
            "Serialized SteamCMD installs and updates to prevent competing jobs from sharing the same SteamCMD process data.",
            "Added per-server SteamCMD progress logs and detailed update errors; updates now require an explicit SteamCMD success confirmation.",
            "Required servers to be stopped before running a manual game update check.",
        ],
    },
    {
        "version": "0.9.3",
        "date": "2026-10-16",
        "changes": [
            "Changed update-before-start failures into visible warnings so an installed server can still start.",
            "Added a server update failed webhook event for failed SteamCMD checks.",
            "Added the running ESM-Z version to the persistent page header.",
        ],
    },
    {
        "version": "0.9.2",
        "date": "2026-10-16",
        "changes": [
            "Added a visible admin notice when a compatible ESM-Z update is available.",
            "Made manager updates manual-only and removed the automatic-install setting.",
            "Added stable and testing release channels, with stable releases selected by default.",
            "Added checksum verification, package validation, backup, and rollback protection to self-updates.",
            "Added an installed-pending-restart state so the UI does not claim the running process is already updated.",
        ],
    },
    {
        "version": "0.9.1",
        "date": "2026-09-08",
        "changes": [
            "Renamed the user-facing product to ESM-Z - Enshrouded Server Manager by Zat.",
            "Added a repository-specific Linux host support architecture analysis without changing server runtime behavior.",
            "Added compatibility for both ESM-Z and legacy manager release package names.",
            "Clarified installed and published manager versions and moved private GitHub credentials into advanced settings.",
            "Fixed misleading up-to-date messages when local files are newer than the latest published GitHub Release.",
        ],
    },
    {
        "version": "0.9.0",
        "date": "2026-09-08",
        "changes": [
            "Changed webhooks to a per-server list with support for multiple webhook destinations.",
            "Limited the Current Webhooks list to the server selected in the header.",
            "Added independent add, edit, test, enable/disable, and delete controls for each webhook.",
            "Added automatic migration for webhook settings saved by earlier manager versions.",
        ],
    },
    {
        "version": "0.8.2",
        "date": "2026-09-08",
        "changes": [
            "Added a current webhooks management list under Server Setup & Config.",
            "Improved GitHub update checks on Windows installs with missing local certificate authority data.",
        ],
    },
    {
        "version": "0.8.1",
        "date": "2026-09-08",
        "changes": [
            "Updated the default GitHub update-check repository after the project moved.",
        ],
    },
    {
        "version": "0.8.0",
        "date": "2026-09-08",
        "changes": [
            "Added per-server Discord/generic webhook notifications under Server Setup & Config.",
            "Added configurable manager update checks against GitHub releases.",
            "Added webhook notifications for manager update availability.",
        ],
    },
    {
        "version": "0.7.7",
        "date": "2026-09-01",
        "changes": [
            "Added shareable repository documentation for install, use, features, screenshots, and releases.",
            "Updated the Python-required release package to include repository docs and screenshots.",
        ],
    },
    {
        "version": "0.7.6",
        "date": "2026-08-19",
        "changes": [
            "Changed grouped navigation into true sub-tabs under Server Setup & Config and Account.",
            "Reduced the main tab bar to the primary areas while keeping related pages visible in a second-row sub-tab bar.",
        ],
    },
    {
        "version": "0.7.5",
        "date": "2026-08-19",
        "changes": [
            "Cleaned up navigation into Server Setup & Config and Account groups.",
            "New server installs now leave Instance name blank and auto-fill Directory from the chosen instance name.",
            "Added a default Friends game user group and removed the confusing public-server checkbox from basic server settings.",
        ],
    },
    {
        "version": "0.7.4",
        "date": "2026-08-19",
        "changes": [
            "Fixed auto-refresh resetting invite code type selections before code generation.",
            "Fixed auto-refresh resetting user-management edits before they are saved.",
            "Added broader UI edit guards so active settings stay in place while the manager refreshes status.",
        ],
    },
    {
        "version": "0.7.3",
        "date": "2026-08-18",
        "changes": [
            "Fixed save imports loading as fresh worlds by installing the selected local world into the server's primary save slot.",
            "Save imports now stop a running server before replacing the save files.",
        ],
    },
    {
        "version": "0.7.2",
        "date": "2026-08-18",
        "changes": [
            "Added local save-folder world grouping so users choose one Enshrouded world before importing.",
            "Added safeguards to prevent accidentally importing every world from a multi-save folder.",
        ],
    },
    {
        "version": "0.7.1",
        "date": "2026-08-18",
        "changes": [
            "Improved Windows server stop handling for detached persistent server processes.",
            "Manager Stop now clears desired-running state immediately so stopped servers are not restarted during shutdown delays.",
        ],
    },
    {
        "version": "0.7.0",
        "date": "2026-08-18",
        "changes": [
            "Added manager update log and version history packaging.",
            "Changed server launches to detached persistent processes so manager updates do not intentionally stop running servers.",
            "Added stored server lifecycle metadata including PID, last start, last stop, last restart, and last update timestamps.",
        ],
    },
    {
        "version": "0.6.0",
        "date": "2026-08-18",
        "changes": [
            "Added remote-user save folder import workflow.",
            "Added server owner creation limits and creation cooldowns.",
            "Improved install job visibility across users and admin sessions.",
        ],
    },
    {
        "version": "0.5.0",
        "date": "2026-08-18",
        "changes": [
            "Added adaptive Instructions tab.",
            "Added used invite cleanup.",
            "Added query port conflict checks before server start.",
        ],
    },
    {
        "version": "0.4.0",
        "date": "2026-08-17",
        "changes": [
            "Added invite URLs, invite titles and descriptions, server-owner invite generation, and invite cleanup tools.",
            "Moved manager users into role-based user management.",
        ],
    },
]


if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    STATIC_DIR = Path(getattr(sys, "_MEIPASS")) / "static"
else:
    ROOT = Path(__file__).resolve().parent.parent
    STATIC_DIR = ROOT / "enshrouded_manager" / "static"
SERVER_DIR = ROOT / "Enshrouded Dedicated Server"
STEAMCMD = ROOT / "Steamcmd" / "steamcmd.exe"
APP_DIR = ROOT / "enshrouded_manager"
sys.path.insert(0, str(APP_DIR))
import update_runtime
DATA_DIR = APP_DIR / "data"
MANAGER_CONFIG = DATA_DIR / "manager_config.json"
SERVER_CONFIG = SERVER_DIR / "enshrouded_server.json"
SERVER_EXE = SERVER_DIR / "enshrouded_server.exe"
BACKUP_DIR = DATA_DIR / "backups"
IMPORT_DIR = DATA_DIR / "imports"
MANAGER_LOG = DATA_DIR / "manager.log"
APP_ID = "2278520"
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
DEFAULT_QUERY_PORT = 15637
GITHUB_REPO = "Zataralee/Enshrouded-Server-Manager-by-Zat"
RELEASE_PACKAGE_PREFIXES = ("ESM-Z-PythonRequired", "EnshroudedServerManager-PythonRequired")
SAVE_WORLD_RE = re.compile(r"^([0-9a-fA-F]{8,16})(?:$|[-_].*)")
DEFAULT_SERVER_WORLD_ID = "3ad85aea"
KNOWN_WORLD_IDS = [
    "3ad85aea",
    "3bd85c7d",
    "38d857c4",
    "39d85957",
    "36d8549e",
    "37d85631",
    "34d85178",
    "35d8530b",
    "32d84e52",
    "33d84fe5",
]
ALL_PERMISSIONS = ["setup", "control", "settings", "accounts", "logs", "saves", "backups"]
WEBHOOK_EVENTS = {
    "server.started": "Server started",
    "server.stopped": "Server stopped",
    "server.restarted": "Server restarted",
    "server.crashed": "Server crashed",
    "server.failed": "Server failed to start",
    "server.updated": "Server update completed",
    "server.update.failed": "Server update failed",
    "server.backup.created": "Backup created",
    "server.backup.ftp": "FTP backup completed",
    "server.install.started": "Server install started",
    "server.install.completed": "Server install completed",
    "server.install.failed": "Server install failed",
    "manager.update.available": "Manager update available",
    "manager.update.installed": "Manager update installed",
    "manager.update.failed": "Manager update failed",
}
DEFAULT_WEBHOOK_EVENTS = [
    "server.started",
    "server.stopped",
    "server.restarted",
    "server.crashed",
    "server.failed",
    "server.updated",
    "server.update.failed",
    "server.backup.created",
    "server.backup.ftp",
    "server.install.completed",
    "server.install.failed",
    "manager.update.available",
]
INVITE_TYPES = {
    "basic_user": {"label": "Basic User", "role": "user", "permissions": ["logs", "saves", "backups"]},
    "server_manager": {"label": "Server Manager", "role": "user", "permissions": ["control", "settings", "accounts", "logs", "saves", "backups"]},
    "server_owner": {"label": "Server Owner", "role": "server_owner", "permissions": ALL_PERMISSIONS},
}


def now_iso():
    return dt.datetime.now().replace(microsecond=0).isoformat()


def write_log(message):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {message}\n"
    with MANAGER_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line)
    print(line, end="")


def default_config():
    salt = secrets.token_hex(16)
    password = secrets.token_urlsafe(12)
    return {
        "bind_host": "127.0.0.1",
        "port": 8080,
        "allow_local_bypass": True,
        "username": "admin",
        "password_salt": salt,
        "password_hash": hash_password(password, salt),
        "initial_password": password,
        "auto_restart": True,
        "start_on_manager_launch": False,
        "restart_check_interval_seconds": 5,
        "stop_timeout_seconds": 25,
        "server_root": str(ROOT / "Servers"),
        "backup_root": str(BACKUP_DIR),
        "min_backup_interval_minutes": 15,
        "max_backup_interval_minutes": 10080,
        "max_servers_per_owner": 0,
        "server_create_cooldown_minutes": 0,
        "manager_updates": default_manager_updates(),
        "update_before_start": False,
        "scheduled_restarts": [],
        "ftp_backup": {
            "enabled": False,
            "host": "",
            "port": 21,
            "username": "",
            "password": "",
            "remote_dir": "/",
            "passive": True,
        },
        "selected_instance_id": "",
        "instances": [],
        "removed_instances": [],
        "invite_profiles": default_invite_profiles(),
        "invite_codes": [],
        "users": [
            default_user(
                "admin",
                password,
                role="admin",
                permissions=ALL_PERMISSIONS,
                assigned_instance_ids=[],
                must_change_password=False,
            )
        ],
    }


def default_ftp_backup():
    return {
        "enabled": False,
        "host": "",
        "port": 21,
        "username": "",
        "password": "",
        "remote_dir": "/",
        "passive": True,
    }


def default_webhook(name="Webhook"):
    return {
        "id": secrets.token_hex(8),
        "name": name,
        "enabled": False,
        "mode": "discord",
        "url": "",
        "events": list(DEFAULT_WEBHOOK_EVENTS),
    }


def normalize_webhook(webhook, default_name="Webhook"):
    source = webhook if isinstance(webhook, dict) else {}
    mode = source.get("mode", "discord")
    if mode not in {"discord", "json"}:
        mode = "discord"
    events = source.get("events", DEFAULT_WEBHOOK_EVENTS)
    if not isinstance(events, list):
        events = list(DEFAULT_WEBHOOK_EVENTS)
    return {
        "id": str(source.get("id") or secrets.token_hex(8)),
        "name": str(source.get("name") or default_name).strip()[:80] or default_name,
        "enabled": bool(source.get("enabled", False)),
        "mode": mode,
        "url": str(source.get("url") or "").strip(),
        "events": [event for event in events if event in WEBHOOK_EVENTS],
    }


def default_manager_updates():
    return {
        "enabled": True,
        "repo": GITHUB_REPO,
        "interval_hours": 24,
        "channel": "stable",
        "github_token": "",
        "last_checked_at": "",
        "latest_version": "",
        "latest_url": "",
        "update_available": False,
        "package_available": False,
        "release_state": "unchecked",
        "latest_published_at": "",
        "last_error": "",
        "last_installed_at": "",
        "installed_pending_version": "",
        "restart_required": False,
        "checksum_verified": False,
    }


def manager_release_state(latest_version, package_available=False, current_version=APP_VERSION, channel="auto"):
    if not latest_version:
        return "unchecked"
    latest = version_parts(latest_version)
    current = version_parts(current_version)
    if latest > current or stable_channel_return(latest_version, current_version, channel):
        return "available" if package_available else "package_missing"
    if latest == current:
        return "current"
    return "local_newer"


def default_instance(name, path):
    instance_id = slugify(name) or secrets.token_hex(4)
    return {
        "id": instance_id,
        "name": name,
        "path": str(Path(path)),
        "auto_restart": True,
        "start_on_manager_launch": False,
        "update_before_start": False,
        "public_server": False,
        "owner_user_id": "",
        "scheduled_backup_enabled": False,
        "backup_interval_minutes": 1440,
        "last_backup_key": "",
        "scheduled_restarts": [],
        "ftp_backup": default_ftp_backup(),
        "webhooks": [],
        "created_at": now_iso(),
        "save_imports": [],
        "pid": 0,
        "desired_running": False,
        "last_started_at": "",
        "last_stopped_at": "",
        "last_restarted_at": "",
        "last_updated_at": "",
        "last_update_warning": "",
        "last_exit_code": None,
    }


def default_user(username, password, role="user", permissions=None, assigned_instance_ids=None, must_change_password=True):
    salt = secrets.token_hex(16)
    return {
        "id": slugify(username) or secrets.token_hex(4),
        "username": username,
        "role": role,
        "permissions": permissions or [],
        "assigned_instance_ids": assigned_instance_ids or [],
        "steam_name": "",
        "steam_email": "",
        "created_by_invite_code": "",
        "password_salt": salt,
        "password_hash": hash_password(password, salt),
        "must_change_password": must_change_password,
        "created_at": now_iso(),
    }


def default_invite_profiles():
    return {key: dict(value) for key, value in INVITE_TYPES.items()}


def slugify(value):
    chars = []
    for ch in value.lower().strip():
        if ch.isalnum():
            chars.append(ch)
        elif ch in {" ", "-", "_"} and (not chars or chars[-1] != "-"):
            chars.append("-")
    return "".join(chars).strip("-")[:40]


def default_server_config(name="Enshrouded Server", query_port=DEFAULT_QUERY_PORT):
    return {
        "name": name,
        "password": "",
        "saveDirectory": "./savegame",
        "logDirectory": "./logs",
        "ip": "0.0.0.0",
        "queryPort": int(query_port),
        "slotCount": 16,
        "tags": [],
        "voiceChatMode": "Proximity",
        "enableVoiceChat": False,
        "enableTextChat": False,
        "gameSettingsPreset": "Default",
        "gameSettings": {
            "playerHealthFactor": 1,
            "playerManaFactor": 1,
            "playerStaminaFactor": 1,
            "playerBodyHeatFactor": 1,
            "playerDivingTimeFactor": 1,
            "enableDurability": True,
            "enableStarvingDebuff": False,
            "foodBuffDurationFactor": 1,
            "fromHungerToStarving": 600000000000,
            "shroudTimeFactor": 1,
            "tombstoneMode": "AddBackpackMaterials",
            "enableGliderTurbulences": True,
            "weatherFrequency": "Normal",
            "fishingDifficulty": "Normal",
            "miningDamageFactor": 1,
            "plantGrowthSpeedFactor": 1,
            "resourceDropStackAmountFactor": 1,
            "factoryProductionSpeedFactor": 1,
            "perkUpgradeRecyclingFactor": 0.5,
            "perkCostFactor": 1,
            "experienceCombatFactor": 1,
            "experienceMiningFactor": 1,
            "experienceExplorationQuestsFactor": 1,
            "randomSpawnerAmount": "Normal",
            "aggroPoolAmount": "Normal",
            "enemyDamageFactor": 1,
            "enemyHealthFactor": 1,
            "enemyStaminaFactor": 1,
            "enemyPerceptionRangeFactor": 1,
            "bossDamageFactor": 1,
            "bossHealthFactor": 1,
            "threatBonus": 1,
            "pacifyAllEnemies": False,
            "tamingStartleRepercussion": "LoseSomeProgress",
            "dayTimeDuration": 1800000000000,
            "nightTimeDuration": 720000000000,
            "curseModifier": "Normal",
        },
        "userGroups": [
            {
                "name": "Admin",
                "password": "ChangeMeAdmin",
                "canKickBan": True,
                "canAccessInventories": True,
                "canEditWorld": True,
                "canEditBase": True,
                "canExtendBase": True,
                "reservedSlots": 0,
            },
            {
                "name": "Friends",
                "password": "",
                "canKickBan": False,
                "canAccessInventories": True,
                "canEditWorld": True,
                "canEditBase": True,
                "canExtendBase": True,
                "reservedSlots": 0,
            }
        ],
        "bannedAccounts": [],
    }


def signed_exit_code(code):
    if isinstance(code, int) and code > 2147483647:
        return code - 4294967296
    return code


def load_json(path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent="\t")
        fh.write("\n")
    tmp.replace(path)


def hash_password(password, salt):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 180000)
    return base64.b64encode(digest).decode("ascii")


def verify_password(password, salt, expected):
    return hmac.compare_digest(hash_password(password, salt), expected)


def safe_child(base, candidate):
    resolved = candidate.resolve()
    base_resolved = base.resolve()
    if resolved == base_resolved or base_resolved in resolved.parents:
        return resolved
    raise ValueError("Path escapes the allowed directory")


def process_is_running(pid):
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def update_instance_metadata(instance_id, **patch):
    with CONFIG_LOCK:
        cfg = config()
        for inst in cfg.get("instances", []):
            if inst["id"] == instance_id:
                inst.update(patch)
                save_json(MANAGER_CONFIG, cfg)
                return dict(inst)
    raise FileNotFoundError("Unknown server instance")


def stop_process_tree(pid, timeout=8):
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return None
    if pid <= 0 or not process_is_running(pid):
        return None
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + max(1, min(int(timeout or 8), 10))
        while time.time() < deadline:
            if not process_is_running(pid):
                return 0
            time.sleep(0.25)
        write_log(f"Graceful stop timed out for pid={pid}; forcing process tree stop")
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 1
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + max(1, int(timeout or 8))
    while time.time() < deadline:
        if not process_is_running(pid):
            return 0
        time.sleep(0.25)
    write_log(f"Graceful stop timed out for pid={pid}; killing process")
    os.kill(pid, signal.SIGKILL)
    return 1


class ServerSupervisor:
    def __init__(self, instance_id):
        self.instance_id = instance_id
        self.lock = threading.RLock()
        self.process = None
        self.intentional_stop = True
        self.started_at = None
        self.last_exit_code = None
        self.activity = "idle"
        self.last_scheduled_key = ""

    def status(self):
        with self.lock:
            inst = get_instance(self.instance_id)
            tracked_pid = int(inst.get("pid") or 0)
            running = self.process is not None and self.process.poll() is None
            external_running = False if running else process_is_running(tracked_pid)
            pid = self.process.pid if running else (tracked_pid if external_running else None)
            started_at = self.started_at or inst.get("last_started_at")
            desired_running = bool(inst.get("desired_running", False))
            return {
                "running": running or external_running,
                "pid": pid,
                "started_at": started_at,
                "uptime_seconds": int(time.time() - self._started_ts) if running and hasattr(self, "_started_ts") else 0,
                "intentional_stop": not desired_running,
                "last_exit_code": self.last_exit_code if self.last_exit_code is not None else inst.get("last_exit_code"),
                "activity": self.activity,
                "last_stopped_at": inst.get("last_stopped_at", ""),
                "last_restarted_at": inst.get("last_restarted_at", ""),
                "last_updated_at": inst.get("last_updated_at", ""),
                "last_update_warning": inst.get("last_update_warning", ""),
            }

    def start(self, update_first=False):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return
            inst = get_instance(self.instance_id)
            if process_is_running(inst.get("pid")):
                self.intentional_stop = False
                self.activity = "idle"
                update_instance_metadata(self.instance_id, desired_running=True)
                return
            self.intentional_stop = False
            self.activity = "updating" if update_first else "starting"
        if update_first:
            try:
                run_update(self.instance_id)
            except Exception as exc:
                if isinstance(exc, SteamCMDUpdateError):
                    detail = str(exc)
                elif isinstance(exc, subprocess.CalledProcessError):
                    detail = f"SteamCMD exited with code {exc.returncode}"
                else:
                    detail = str(exc) or exc.__class__.__name__
                warning = f"Update check failed: {detail}. Starting the existing server installation instead."
                write_log(warning)
                update_instance_metadata(self.instance_id, last_update_warning=warning)
                with self.lock:
                    self.activity = "starting"
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.activity = "idle"
                return
            exe = instance_exe_path(self.instance_id)
            server_dir = instance_path(self.instance_id)
            if not exe.exists():
                raise FileNotFoundError(f"Enshrouded server is not installed at {server_dir}")
            if not instance_config_path(self.instance_id).exists():
                inst = get_instance(self.instance_id)
                save_json(instance_config_path(self.instance_id), default_server_config(inst["name"], DEFAULT_QUERY_PORT))
                write_log(f"Created initial enshrouded_server.json for {inst['name']}")
            validate_instance_can_start(self.instance_id)
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                if hasattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB"):
                    creationflags |= subprocess.CREATE_BREAKAWAY_FROM_JOB
            self.process = subprocess.Popen(
                [str(exe)],
                cwd=str(server_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self._started_ts = time.time()
            self.started_at = now_iso()
            self.last_exit_code = None
            self.activity = "idle"
            update_instance_metadata(
                self.instance_id,
                pid=self.process.pid,
                desired_running=True,
                last_started_at=self.started_at,
                last_exit_code=None,
            )
            write_log(f"Started {get_instance(self.instance_id)['name']} pid={self.process.pid}")
            notify_webhook_event("server.started", self.instance_id, message=f"{get_instance(self.instance_id)['name']} started.")
        time.sleep(2)
        with self.lock:
            if self.process is not None:
                code = self.process.poll()
                if code is not None:
                    self.last_exit_code = code
                    self.process = None
                    update_instance_metadata(self.instance_id, pid=0, desired_running=False, last_exit_code=code)
                    signed = signed_exit_code(code)
                    hint = ""
                    if signed == -1:
                        hint = " This often means the configured query port is already in use or blocked."
                    notify_webhook_event(
                        "server.failed",
                        self.instance_id,
                        message=f"{get_instance(self.instance_id)['name']} failed to start.",
                        details={"exit_code": code, "signed_exit_code": signed},
                    )
                    raise RuntimeError(f"Enshrouded server exited immediately with code {code} ({signed}).{hint}")

    def stop(self):
        with self.lock:
            self.intentional_stop = True
            proc = self.process
            timeout = int(config().get("stop_timeout_seconds", 25))
            inst = get_instance(self.instance_id)
            tracked_pid = int(inst.get("pid") or 0)
            update_instance_metadata(self.instance_id, desired_running=False)
            if proc is None or proc.poll() is not None:
                if tracked_pid and process_is_running(tracked_pid):
                    stop_process_tree(tracked_pid, timeout=timeout)
                self.process = None
                update_instance_metadata(self.instance_id, pid=0, desired_running=False, last_stopped_at=now_iso())
                return
            self.activity = "stopping"
        write_log("Stopping Enshrouded server by manager request")
        if os.name == "nt":
            stop_process_tree(proc.pid, timeout=timeout)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        else:
            try:
                proc.terminate()
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                write_log("Stop timeout reached; killing Enshrouded server")
                proc.kill()
                proc.wait(timeout=10)
        with self.lock:
            self.last_exit_code = proc.returncode
            self.process = None
            self.activity = "idle"
            update_instance_metadata(self.instance_id, pid=0, desired_running=False, last_stopped_at=now_iso(), last_exit_code=proc.returncode)
            notify_webhook_event("server.stopped", self.instance_id, message=f"{get_instance(self.instance_id)['name']} stopped.")

    def restart(self, update_first=False):
        self.stop()
        self.start(update_first=update_first)
        update_instance_metadata(self.instance_id, last_restarted_at=now_iso())
        notify_webhook_event("server.restarted", self.instance_id, message=f"{get_instance(self.instance_id)['name']} restarted.")

    def monitor_once(self):
        inst = get_instance(self.instance_id)
        with self.lock:
            proc = self.process
            desired_running = bool(inst.get("desired_running", False))
            if proc is None:
                running = process_is_running(inst.get("pid"))
                should_start = desired_running and not running and not bool(inst.get("pid"))
                crashed = bool(inst.get("pid")) and not running and desired_running
                if crashed:
                    self.last_exit_code = inst.get("last_exit_code")
                    update_instance_metadata(self.instance_id, pid=0)
            else:
                code = proc.poll()
                crashed = code is not None
                should_start = False
                if crashed:
                    self.last_exit_code = code
                    self.process = None
                    update_instance_metadata(self.instance_id, pid=0, last_exit_code=code)
        if crashed:
            write_log(f"Enshrouded server exited with code {self.last_exit_code} ({signed_exit_code(self.last_exit_code)})")
            notify_webhook_event(
                "server.crashed",
                self.instance_id,
                message=f"{inst['name']} crashed with exit code {self.last_exit_code}.",
                details={"exit_code": self.last_exit_code, "signed_exit_code": signed_exit_code(self.last_exit_code)},
            )
            if inst.get("auto_restart", True) and desired_running:
                write_log("Auto-restart is enabled; starting server again")
                self.start(update_first=False)
            else:
                update_instance_metadata(self.instance_id, desired_running=False)
        elif should_start:
            self.start(update_first=inst.get("update_before_start", False))


SUPERVISORS = {}
CONFIG_LOCK = threading.RLock()
STEAMCMD_LOCK = threading.Lock()
JOBS = {}
JOBS_LOCK = threading.RLock()
SESSION_LOCK = threading.RLock()
UPDATE_LOCK = threading.Lock()
MAINTENANCE = threading.Event()
OPERATIONS = threading.Condition()
ACTIVE_OPERATIONS = 0
HTTP_SERVER = None
BOOT_ID = secrets.token_hex(16)


def session_user(token):
    key = hashlib.sha256(token.encode()).hexdigest()
    with SESSION_LOCK:
        records = update_runtime.read_json(DATA_DIR / "sessions.json")
        session = records.get(key, {})
        user = find_user(user_id=session.get("user_id")) if session else None
        if (not user or session.get("expires", 0) <= time.time()
                or session.get("credential") != hashlib.sha256(user.get("password_hash", "").encode()).hexdigest()):
            return None
        return user


def create_session(user):
    token = secrets.token_urlsafe(32)
    with SESSION_LOCK:
        path = DATA_DIR / "sessions.json"
        records = {key: value for key, value in update_runtime.read_json(path).items()
                   if value.get("expires", 0) > time.time()}
        records[hashlib.sha256(token.encode()).hexdigest()] = {
            "user_id": user["id"], "expires": time.time() + 86400,
            "credential": hashlib.sha256(find_user(user_id=user["id"])["password_hash"].encode()).hexdigest(),
        }
        update_runtime.atomic_json(path, records)
    return token


def revoke_session(token):
    with SESSION_LOCK:
        path = DATA_DIR / "sessions.json"
        records = update_runtime.read_json(path)
        records.pop(hashlib.sha256(token.encode()).hexdigest(), None)
        update_runtime.atomic_json(path, records)


def manager_update_status():
    return update_runtime.read_json(DATA_DIR / "manager_updates" / "status.json", {"phase": "idle"})


def update_status(phase, message, **values):
    return update_runtime.set_status(DATA_DIR / "manager_updates" / "status.json", phase, message, **values)


def wait_for_update_idle(timeout=600):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with OPERATIONS:
            requests_busy = ACTIVE_OPERATIONS > 0
        with JOBS_LOCK:
            jobs_busy = any(job.get("status") == "running" for job in JOBS.values())
        if not requests_busy and not jobs_busy and not STEAMCMD_LOCK.locked():
            return
        time.sleep(0.25)
    raise RuntimeError("An active server operation did not finish within 10 minutes. Retry the manager update later.")


def start_manager_update(expected_channel=None):
    if getattr(sys, "frozen", False):
        raise RuntimeError("Remote restart requires the Python-required release, not an executable build")
    if HTTP_SERVER is None:
        raise RuntimeError("The manager HTTP server is not ready")
    cfg = config()
    if (HTTP_SERVER.server_address[0] != cfg.get("bind_host", "127.0.0.1")
            or HTTP_SERVER.server_address[1] != int(cfg.get("port", 8080))):
        raise RuntimeError("Restart ESM-Z to apply pending listen-address or port changes before updating")
    if not UPDATE_LOCK.acquire(blocking=False):
        raise RuntimeError("A manager update is already in progress")
    MAINTENANCE.set()
    try:
        state = update_status("waiting", "Waiting for active server operations to finish.",
                              operation_id=secrets.token_hex(16), previous_boot_id=BOOT_ID,
                              target_version="", error="")
    except Exception:
        MAINTENANCE.clear()
        UPDATE_LOCK.release()
        raise

    def worker():
        handed_off = False
        try:
            wait_for_update_idle()
            if expected_channel is not None and manager_updates_config().get("channel") != expected_channel:
                raise RuntimeError("The update channel changed. Check for updates again before installing.")
            plan = install_manager_update()
            job = Path(plan["job"])
            helper = job / "update-helper.py"
            shutil.copy2(Path(update_runtime.__file__), helper)
            plan_path = job / "plan.json"
            update_runtime.atomic_json(plan_path, plan)
            options = {"cwd": str(ROOT), "stdin": subprocess.DEVNULL}
            if os.name == "nt":
                options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                options["start_new_session"] = True
            with (job / "helper.log").open("ab") as output:
                process = subprocess.Popen([sys.executable, "-u", str(helper), str(plan_path)],
                                           stdout=output, stderr=subprocess.STDOUT, **options)
            deadline = time.monotonic() + 10
            while not (job / "helper-ready.json").is_file():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("The independent update helper did not start; the current manager is still running")
                time.sleep(0.1)
            update_status("restarting", "Restarting ESM-Z. Running game servers remain online.")
            handed_off = True
            HTTP_SERVER.shutdown()
        except Exception as error:
            update_status("error", str(error), error=str(error))
            write_log(f"Manager update failed: {error}")
            notify_webhook_event("manager.update.failed", message=f"Manager update failed: {error}")
        finally:
            if not handed_off:
                MAINTENANCE.clear()
            UPDATE_LOCK.release()

    try:
        threading.Thread(target=worker, daemon=True).start()
    except Exception:
        MAINTENANCE.clear()
        UPDATE_LOCK.release()
        raise
    return state


def supervisor(instance_id=None):
    inst = get_instance(instance_id)
    if inst["id"] not in SUPERVISORS:
        SUPERVISORS[inst["id"]] = ServerSupervisor(inst["id"])
    return SUPERVISORS[inst["id"]]


def new_job(kind, **fields):
    job_id = secrets.token_hex(8)
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "kind": kind,
            "status": "running",
            "message": "Starting",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "result": None,
            "error": "",
            **fields,
        }
    return job_id


def update_job(job_id, message=None, status=None, result=None, error=None):
    with JOBS_LOCK:
        job = JOBS[job_id]
        if message is not None:
            job["message"] = message
        if status is not None:
            job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job["updated_at"] = now_iso()


def get_job(job_id):
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise FileNotFoundError("Unknown job")
        return dict(JOBS[job_id])


def visible_jobs_for_user(user):
    cutoff = dt.datetime.now() - dt.timedelta(hours=24)
    with JOBS_LOCK:
        jobs = []
        for job in JOBS.values():
            if job.get("kind") != "install_instance":
                continue
            if not is_admin(user) and job.get("owner_user_id") != user.get("id"):
                continue
            if user.get("id") in job.get("dismissed_by", []):
                continue
            try:
                updated = dt.datetime.fromisoformat(job.get("updated_at", ""))
            except ValueError:
                updated = dt.datetime.now()
            if job.get("status") != "running" and updated < cutoff:
                continue
            jobs.append(dict(job))
    return sorted(reversed(jobs), key=lambda item: item.get("updated_at", ""), reverse=True)


def get_job_for_user(job_id, user):
    job = get_job(job_id)
    if job.get("kind") == "install_instance" and not is_admin(user) and job.get("owner_user_id") != user.get("id"):
        raise PermissionError("Permission denied")
    return job


def dismiss_job_for_user(job_id, user):
    get_job_for_user(job_id, user)
    with JOBS_LOCK:
        job = JOBS[job_id]
        dismissed = set(job.get("dismissed_by", []))
        dismissed.add(user.get("id"))
        job["dismissed_by"] = sorted(dismissed)
        job["updated_at"] = now_iso()
    return True


def config():
    with CONFIG_LOCK:
        if not MANAGER_CONFIG.exists():
            cfg = default_config()
            detect_existing_instance(cfg)
            save_json(MANAGER_CONFIG, cfg)
            write_log(f"Created manager config. Initial remote login is admin / {cfg['initial_password']}")
        cfg = load_json(MANAGER_CONFIG, {})
        changed = migrate_config(cfg)
        if changed:
            save_json(MANAGER_CONFIG, cfg)
        return cfg


def detect_existing_instance(cfg):
    if SERVER_EXE.exists() and SERVER_CONFIG.exists() and not cfg.get("instances"):
        inst = default_instance("Default Server", SERVER_DIR)
        cfg["instances"] = [inst]
        cfg["selected_instance_id"] = inst["id"]


def migrate_config(cfg):
    changed = False
    if "server_root" not in cfg:
        cfg["server_root"] = str(ROOT / "Servers")
        changed = True
    if "backup_root" not in cfg:
        cfg["backup_root"] = str(BACKUP_DIR)
        changed = True
    if "min_backup_interval_minutes" not in cfg:
        cfg["min_backup_interval_minutes"] = 15
        changed = True
    if "max_backup_interval_minutes" not in cfg:
        cfg["max_backup_interval_minutes"] = 10080
        changed = True
    if "max_servers_per_owner" not in cfg:
        cfg["max_servers_per_owner"] = 0
        changed = True
    if "server_create_cooldown_minutes" not in cfg:
        cfg["server_create_cooldown_minutes"] = 0
        changed = True
    if "manager_updates" not in cfg:
        cfg["manager_updates"] = default_manager_updates()
        changed = True
    else:
        if "auto_install" in cfg["manager_updates"]:
            cfg["manager_updates"].pop("auto_install", None)
            changed = True
        defaults = default_manager_updates()
        for key, value in defaults.items():
            if key not in cfg["manager_updates"]:
                cfg["manager_updates"][key] = value
                changed = True
        pending_version = str(cfg["manager_updates"].get("installed_pending_version") or "")
        if pending_version and pending_version == APP_VERSION:
            cfg["manager_updates"]["installed_pending_version"] = ""
            cfg["manager_updates"]["restart_required"] = False
            changed = True
    if "removed_instances" not in cfg:
        cfg["removed_instances"] = []
        changed = True
    if "invite_profiles" not in cfg:
        cfg["invite_profiles"] = default_invite_profiles()
        changed = True
    else:
        for key, value in default_invite_profiles().items():
            if key not in cfg["invite_profiles"]:
                cfg["invite_profiles"][key] = value
                changed = True
    if "invite_codes" not in cfg:
        cfg["invite_codes"] = []
        changed = True
    if "users" not in cfg:
        cfg["users"] = [{
            "id": "admin",
            "username": cfg.get("username", "admin"),
            "role": "admin",
            "permissions": ALL_PERMISSIONS,
            "assigned_instance_ids": [],
            "steam_name": "",
            "steam_email": "",
            "created_by_invite_code": "",
            "password_salt": cfg.get("password_salt", ""),
            "password_hash": cfg.get("password_hash", ""),
            "must_change_password": False,
            "created_at": now_iso(),
        }]
        changed = True
    for user in cfg.get("users", []):
        for key, value in {"steam_name": "", "steam_email": "", "created_by_invite_code": ""}.items():
            if key not in user:
                user[key] = value
                changed = True
    if "instances" not in cfg:
        cfg["instances"] = []
        changed = True
    if not cfg["instances"]:
        before = len(cfg["instances"])
        detect_existing_instance(cfg)
        changed = changed or len(cfg["instances"]) != before
    if "selected_instance_id" not in cfg:
        cfg["selected_instance_id"] = cfg["instances"][0]["id"] if cfg["instances"] else ""
        changed = True
    for inst in cfg.get("instances", []):
        for key, value in {
            "auto_restart": cfg.get("auto_restart", True),
            "start_on_manager_launch": cfg.get("start_on_manager_launch", False),
            "update_before_start": cfg.get("update_before_start", False),
            "public_server": False,
            "owner_user_id": "",
            "scheduled_backup_enabled": False,
            "backup_interval_minutes": 1440,
            "last_backup_key": "",
            "scheduled_restarts": cfg.get("scheduled_restarts", []),
            "ftp_backup": cfg.get("ftp_backup", default_ftp_backup()),
            "webhooks": [],
            "created_at": now_iso(),
            "save_imports": [],
            "pid": 0,
            "desired_running": False,
            "last_started_at": "",
            "last_stopped_at": "",
            "last_restarted_at": "",
            "last_updated_at": "",
            "last_update_warning": "",
            "last_exit_code": None,
        }.items():
            if key not in inst:
                inst[key] = value
                changed = True
        legacy_webhook = inst.pop("webhook", None)
        if legacy_webhook is not None:
            if isinstance(legacy_webhook, dict) and (legacy_webhook.get("url") or legacy_webhook.get("enabled")):
                inst.setdefault("webhooks", []).insert(0, normalize_webhook(legacy_webhook, "Primary Webhook"))
            changed = True
        current_webhooks = inst.get("webhooks", [])
        if not isinstance(current_webhooks, list):
            current_webhooks = []
        normalized_webhooks = []
        used_webhook_ids = set()
        for index, webhook in enumerate(current_webhooks, start=1):
            normalized = normalize_webhook(webhook, f"Webhook {index}")
            while normalized["id"] in used_webhook_ids:
                normalized["id"] = secrets.token_hex(8)
            used_webhook_ids.add(normalized["id"])
            normalized_webhooks.append(normalized)
        if normalized_webhooks != inst.get("webhooks"):
            inst["webhooks"] = normalized_webhooks
            changed = True
    return changed


def users():
    return config().get("users", [])


def primary_admin():
    for user in users():
        if user.get("role") == "admin":
            return user
    raise FileNotFoundError("No admin user is configured")


def find_user(username=None, user_id=None):
    for user in users():
        if username is not None and user.get("username", "").lower() == username.lower():
            return user
        if user_id is not None and user.get("id") == user_id:
            return user
    return None


def user_public(user):
    item = dict(user)
    item.pop("password_hash", None)
    item.pop("password_salt", None)
    return item


def is_admin(user):
    return bool(user and user.get("role") == "admin")


def is_server_owner(user):
    return bool(user and user.get("role") == "server_owner")


def can_manage_invites(user):
    return is_admin(user) or is_server_owner(user)


def has_permission(user, permission):
    return is_admin(user) or permission in set(user.get("permissions", []))


def visible_instances_for_user(user):
    if is_admin(user):
        return instances()
    assigned = set(user.get("assigned_instance_ids", []))
    user_id = user.get("id")
    return [inst for inst in instances() if inst.get("owner_user_id") == user_id or inst.get("id") in assigned]


def removed_instances_for_user(user):
    removed = config().get("removed_instances", [])
    if is_admin(user):
        return removed
    assigned = set(user.get("assigned_instance_ids", []))
    user_id = user.get("id")
    return [inst for inst in removed if inst.get("owner_user_id") == user_id or inst.get("id") in assigned]


def visible_users_for_user(user):
    if is_admin(user):
        return [user_public(item) for item in config().get("users", [])]
    if not is_server_owner(user):
        return []
    owned_codes = {
        invite.get("code")
        for invite in config().get("invite_codes", [])
        if invite.get("created_by_user_id") == user.get("id")
    }
    return [
        user_public(item)
        for item in config().get("users", [])
        if item.get("created_by_invite_code") in owned_codes
    ]


def get_visible_managed_user(user, user_id):
    for item in visible_users_for_user(user):
        if item.get("id") == user_id:
            return item
    raise PermissionError("This account cannot manage that user")


def get_instance_for_user(user, instance_id=None):
    visible = visible_instances_for_user(user)
    wanted = instance_id or config().get("selected_instance_id")
    for inst in visible:
        if inst["id"] == wanted:
            return inst
    if visible:
        return visible[0]
    raise FileNotFoundError("No Enshrouded server instance is assigned to this account")


def require_permission(user, permission):
    if not has_permission(user, permission):
        raise PermissionError("This account does not have permission for that action")


def check_server_creation_allowed(user):
    if is_admin(user):
        return
    if not is_server_owner(user):
        return
    cfg = config()
    max_servers = int(cfg.get("max_servers_per_owner", 0) or 0)
    cooldown = int(cfg.get("server_create_cooldown_minutes", 0) or 0)
    owned = [
        inst for inst in cfg.get("instances", []) + cfg.get("removed_instances", [])
        if inst.get("owner_user_id") == user.get("id")
    ]
    if max_servers and len(owned) >= max_servers:
        raise ValueError(f"Server owner limit reached. This account can create up to {max_servers} server(s).")
    if cooldown and owned:
        newest = max(owned, key=lambda inst: inst.get("created_at", ""))
        try:
            created = dt.datetime.fromisoformat(newest.get("created_at", ""))
            available = created + dt.timedelta(minutes=cooldown)
            if dt.datetime.now() < available:
                wait = max(1, int((available - dt.datetime.now()).total_seconds() // 60) + 1)
                raise ValueError(f"Server creation cooldown is active. Try again in about {wait} minute(s).")
        except ValueError as exc:
            if "cooldown" in str(exc).lower():
                raise


def invite_type_allowed_for_user(user, code_type):
    if is_admin(user):
        return code_type in INVITE_TYPES
    if is_server_owner(user):
        return code_type in {"basic_user", "server_manager"}
    return False


def scoped_instance_ids_for_user(user, requested_ids):
    valid = {inst["id"] for inst in visible_instances_for_user(user)}
    if is_admin(user):
        valid = {inst["id"] for inst in instances()}
    scoped = [item for item in requested_ids if item in valid]
    if requested_ids and len(scoped) != len(requested_ids):
        raise PermissionError("One or more selected servers are outside this account's scope")
    return scoped


def instances():
    return config().get("instances", [])


def get_instance(instance_id=None):
    cfg = config()
    wanted = instance_id or cfg.get("selected_instance_id")
    for inst in cfg.get("instances", []):
        if inst["id"] == wanted:
            return inst
    if cfg.get("instances"):
        return cfg["instances"][0]
    raise FileNotFoundError("No Enshrouded server instance is configured")


def instance_path(instance_id=None):
    return Path(get_instance(instance_id)["path"])


def instance_config_path(instance_id=None):
    return instance_path(instance_id) / "enshrouded_server.json"


def instance_exe_path(instance_id=None):
    return instance_path(instance_id) / "enshrouded_server.exe"


def instance_save_path(instance_id=None):
    cfg = load_json(instance_config_path(instance_id), {})
    save_dir = cfg.get("saveDirectory", "./savegame")
    return safe_child(instance_path(instance_id), instance_path(instance_id) / save_dir)


def instance_query_port(instance_id=None):
    cfg = load_json(instance_config_path(instance_id), {})
    try:
        return int(cfg.get("queryPort", get_instance(instance_id).get("installation_query_port") or DEFAULT_QUERY_PORT))
    except (TypeError, ValueError):
        return DEFAULT_QUERY_PORT


def running_instance_for_query_port(query_port, exclude_instance_id=None):
    for inst in instances():
        if inst["id"] == exclude_instance_id:
            continue
        sup = SUPERVISORS.get(inst["id"])
        if not sup or not sup.status().get("running"):
            continue
        if instance_query_port(inst["id"]) == int(query_port):
            return inst
    return None


def instance_for_query_port(query_port, exclude_instance_id=None):
    for inst in instances():
        if inst["id"] == exclude_instance_id:
            continue
        if instance_query_port(inst["id"]) == int(query_port):
            return inst
    return None


def udp_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def validate_instance_can_start(instance_id):
    server_config = load_json(instance_config_path(instance_id), {})
    normalize_server_config(server_config, public_server=get_instance(instance_id).get("public_server", False))
    save_json(instance_config_path(instance_id), server_config)
    validate_server_config(server_config)
    port = instance_query_port(instance_id)
    other = running_instance_for_query_port(port, exclude_instance_id=instance_id)
    if other:
        raise RuntimeError(f"Query port {port} is already used by running instance '{other['name']}'. Choose a unique query port before starting this server.")
    other = instance_for_query_port(port, exclude_instance_id=instance_id)
    if other:
        raise RuntimeError(f"Query port {port} is already assigned to instance '{other['name']}'. Change this server's query port in Server Config before starting it.")
    if not udp_port_available(port):
        raise RuntimeError(f"UDP query port {port} is already in use. Choose a unique query port for this server instance.")


def validate_server_config(server_config):
    blank_groups = []
    for index, group in enumerate(server_config.get("userGroups", []), start=1):
        name = group.get("name") or f"Group {index}"
        if not str(group.get("password", "")).strip():
            blank_groups.append(name)
    if len(blank_groups) > 1:
        raise ValueError(f"Only one user group can be public/passwordless. These groups are blank: {', '.join(blank_groups)}")
    query_port = int(server_config.get("queryPort", DEFAULT_QUERY_PORT))
    if query_port < 1 or query_port > 65535:
        raise ValueError("queryPort must be between 1 and 65535")


def normalize_server_config(server_config, public_server=False):
    if public_server:
        server_config["password"] = False
    else:
        if server_config.get("password") is False:
            server_config["password"] = ""
        else:
            server_config.setdefault("password", "")
    return server_config


def public_config(user=None):
    cfg = dict(config())
    cfg.pop("password_hash", None)
    cfg.pop("password_salt", None)
    cfg.pop("initial_password", None)
    cfg["manager_updates"] = public_manager_updates(cfg.get("manager_updates"))
    if is_admin(user):
        cfg["manager_updates"]["operation"] = manager_update_status()
    ftp = dict(cfg.get("ftp_backup", {}))
    if ftp.get("password"):
        ftp["password"] = "********"
    cfg["ftp_backup"] = ftp
    cfg["instances"] = [public_instance(inst) for inst in visible_instances_for_user(user or primary_admin())]
    cfg["removed_instances"] = [public_removed_instance(inst) for inst in removed_instances_for_user(user or primary_admin())]
    visible_users = visible_users_for_user(user)
    if visible_users:
        cfg["users"] = visible_users
    else:
        cfg.pop("users", None)
    if can_manage_invites(user):
        cfg["invite_profiles"] = cfg.get("invite_profiles", default_invite_profiles()) if is_admin(user) else {}
        cfg["invite_codes"] = visible_invites_for_user(user)
        cfg["allowed_invite_types"] = list(INVITE_TYPES) if is_admin(user) else ["basic_user", "server_manager"]
    else:
        cfg.pop("invite_profiles", None)
        cfg.pop("invite_codes", None)
        cfg["allowed_invite_types"] = []
    cfg["steamcmd_installed"] = steamcmd_path().exists()
    cfg["setup_required"] = len(cfg["instances"]) == 0
    cfg["used_query_ports"] = sorted({instance_query_port(inst["id"]) for inst in instances()})
    cfg["app_version"] = APP_VERSION
    cfg["update_log"] = UPDATE_LOG
    cfg["webhook_events"] = WEBHOOK_EVENTS
    cfg["default_webhook_events"] = DEFAULT_WEBHOOK_EVENTS
    if user:
        cfg["current_user"] = user_public(user)
    return cfg


def update_config(patch):
    with CONFIG_LOCK:
        cfg = config()
        if "bind_host" in patch and patch["bind_host"] not in {"127.0.0.1", "0.0.0.0"}:
            raise ValueError("Listen address must be 127.0.0.1 or 0.0.0.0")
        if "port" in patch:
            port = int(patch["port"])
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
            patch["port"] = port
        for key in [
            "bind_host",
            "port",
            "allow_local_bypass",
            "auto_restart",
            "start_on_manager_launch",
            "update_before_start",
            "stop_timeout_seconds",
            "scheduled_restarts",
        ]:
            if key in patch:
                cfg[key] = patch[key]
        for key in ["server_root", "backup_root"]:
            if key in patch and str(patch[key]).strip():
                cfg[key] = str(Path(str(patch[key]).strip()))
        for key in ["min_backup_interval_minutes", "max_backup_interval_minutes", "max_servers_per_owner", "server_create_cooldown_minutes"]:
            if key in patch:
                cfg[key] = int(patch[key])
        if int(cfg.get("min_backup_interval_minutes", 15)) < 1:
            raise ValueError("Minimum backup interval must be at least 1 minute")
        if int(cfg.get("max_backup_interval_minutes", 10080)) < int(cfg.get("min_backup_interval_minutes", 15)):
            raise ValueError("Maximum backup interval must be greater than or equal to the minimum")
        if int(cfg.get("max_servers_per_owner", 0)) < 0:
            raise ValueError("Server owner limit cannot be negative")
        if int(cfg.get("server_create_cooldown_minutes", 0)) < 0:
            raise ValueError("Server creation cooldown cannot be negative")
        if "username" in patch and patch["username"].strip():
            cfg["username"] = patch["username"].strip()
            for user in cfg.get("users", []):
                if user.get("role") == "admin":
                    user["username"] = patch["username"].strip()
                    break
        if "password" in patch and patch["password"]:
            salt = secrets.token_hex(16)
            cfg["password_salt"] = salt
            cfg["password_hash"] = hash_password(patch["password"], salt)
            for user in cfg.get("users", []):
                if user.get("role") == "admin":
                    user["password_salt"] = salt
                    user["password_hash"] = cfg["password_hash"]
                    user["must_change_password"] = False
                    break
            cfg.pop("initial_password", None)
        if "ftp_backup" in patch:
            ftp = dict(cfg.get("ftp_backup", {}))
            incoming = patch["ftp_backup"]
            for key in ["enabled", "host", "port", "username", "remote_dir", "passive"]:
                if key in incoming:
                    ftp[key] = incoming[key]
            if incoming.get("password") and incoming.get("password") != "********":
                ftp["password"] = incoming["password"]
            cfg["ftp_backup"] = ftp
        if "manager_updates" in patch:
            updates = dict(cfg.get("manager_updates", default_manager_updates()))
            incoming = patch["manager_updates"]
            for key in ["enabled", "repo"]:
                if key in incoming:
                    updates[key] = incoming[key]
            if "channel" in incoming:
                channel = str(incoming.get("channel") or "auto").strip().lower()
                if channel not in {"auto", "stable", "prerelease", "beta"}:
                    raise ValueError("Manager update channel must be auto, stable, prerelease, or beta")
                if channel != updates.get("channel"):
                    updates.update(last_checked_at="", latest_version="", latest_url="", last_error="",
                                   package_available=False, update_available=False, release_state="unchecked")
                updates["channel"] = channel
            updates.pop("auto_install", None)
            if "interval_hours" in incoming:
                interval = int(incoming.get("interval_hours") or 24)
                if interval < 1:
                    raise ValueError("Manager update interval must be at least 1 hour")
                updates["interval_hours"] = interval
            if incoming.get("github_token") and incoming.get("github_token") != "********":
                updates["github_token"] = incoming["github_token"].strip()
            if "clear_github_token" in incoming and incoming.get("clear_github_token"):
                updates["github_token"] = ""
            repo = str(updates.get("repo") or "").strip()
            if "/" not in repo:
                raise ValueError("GitHub repository must use owner/repo format")
            updates["repo"] = repo
            cfg["manager_updates"] = updates
        cfg.pop("initial_password", None)
        save_json(MANAGER_CONFIG, cfg)
        write_log("Manager settings updated")
        return public_config(primary_admin())


def update_manager_user(user_id, patch):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for user in cfg.get("users", []):
            if user.get("id") == user_id:
                target = user
                break
        if target is None:
            raise FileNotFoundError("Unknown user")
        if "role" in patch and target.get("role") == "admin" and patch.get("role") != "admin":
            admins = [item for item in cfg.get("users", []) if item.get("role") == "admin"]
            if len(admins) <= 1:
                raise ValueError("At least one admin account is required")
        if "username" in patch and patch["username"].strip():
            wanted = patch["username"].strip()
            existing = find_user(username=wanted)
            if existing and existing.get("id") != user_id:
                raise ValueError("Username is already in use")
            target["username"] = wanted
        if "role" in patch:
            target["role"] = patch["role"] if patch["role"] in {"admin", "server_owner"} else "user"
            if target["role"] == "admin":
                target["permissions"] = ALL_PERMISSIONS
                target["assigned_instance_ids"] = []
        if "steam_name" in patch:
            target["steam_name"] = patch.get("steam_name", "").strip()
        if "steam_email" in patch:
            target["steam_email"] = patch.get("steam_email", "").strip()
        if target.get("role") != "admin":
            if "permissions" in patch:
                target["permissions"] = [p for p in patch["permissions"] if p in ALL_PERMISSIONS]
            if "assigned_instance_ids" in patch:
                valid = {inst["id"] for inst in cfg.get("instances", [])}
                target["assigned_instance_ids"] = [item for item in patch["assigned_instance_ids"] if item in valid]
        save_json(MANAGER_CONFIG, cfg)
    return user_public(target)


def create_manager_user(patch):
    username = patch.get("username", "").strip()
    password = patch.get("password", "")
    if not username or not password:
        raise ValueError("Username and initial password are required")
    with CONFIG_LOCK:
        cfg = config()
        if any(user.get("username", "").lower() == username.lower() for user in cfg.get("users", [])):
            raise ValueError("Username is already in use")
        base_id = slugify(username) or "user"
        used = {user["id"] for user in cfg.get("users", [])}
        user_id = base_id
        counter = 2
        while user_id in used:
            user_id = f"{base_id}-{counter}"
            counter += 1
        user = default_user(
            username,
            password,
            role=patch["role"] if patch.get("role") in {"admin", "server_owner"} else "user",
            permissions=ALL_PERMISSIONS if patch.get("role") == "admin" else [p for p in patch.get("permissions", []) if p in ALL_PERMISSIONS],
            assigned_instance_ids=patch.get("assigned_instance_ids", []),
            must_change_password=True,
        )
        user["id"] = user_id
        user["steam_name"] = patch.get("steam_name", "").strip()
        user["steam_email"] = patch.get("steam_email", "").strip()
        cfg.setdefault("users", []).append(user)
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Created manager user {username}")
    return user_public(user)


def reset_manager_user_password(user_id, password):
    if not password:
        raise ValueError("Password is required")
    with CONFIG_LOCK:
        cfg = config()
        for user in cfg.get("users", []):
            if user.get("id") == user_id:
                salt = secrets.token_hex(16)
                user["password_salt"] = salt
                user["password_hash"] = hash_password(password, salt)
                user["must_change_password"] = True
                save_json(MANAGER_CONFIG, cfg)
                write_log(f"Password reset for manager user {user['username']}")
                return user_public(user)
    raise FileNotFoundError("Unknown user")


def change_own_password(user, old_password, new_password):
    if not verify_password(old_password, user["password_salt"], user["password_hash"]):
        raise ValueError("Current password is incorrect")
    if not new_password:
        raise ValueError("New password is required")
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for item in cfg.get("users", []):
            if item.get("id") == user["id"]:
                target = item
                break
        if target is None:
            raise FileNotFoundError("Unknown user")
        salt = secrets.token_hex(16)
        target["password_salt"] = salt
        target["password_hash"] = hash_password(new_password, salt)
        target["must_change_password"] = False
        save_json(MANAGER_CONFIG, cfg)
    return user_public(target)


def delete_manager_user(user_id):
    with CONFIG_LOCK:
        cfg = config()
        target = find_user(user_id=user_id)
        if not target:
            raise FileNotFoundError("Unknown user")
        if target.get("role") == "admin" and len([u for u in cfg.get("users", []) if u.get("role") == "admin"]) <= 1:
            raise ValueError("At least one admin account is required")
        cfg["users"] = [user for user in cfg.get("users", []) if user.get("id") != user_id]
        for inst in cfg.get("instances", []):
            if inst.get("owner_user_id") == user_id:
                inst["owner_user_id"] = ""
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Deleted manager user {target['username']}")
    return True


def public_instance(inst):
    item = dict(inst)
    if item.get("installation_status") == "installing":
        with JOBS_LOCK:
            active = any(job.get("instance_id") == item["id"] and job.get("status") == "running" for job in JOBS.values())
        if not active:
            item["installation_status"] = "failed"
    ftp = dict(item.get("ftp_backup", {}))
    if ftp.get("password"):
        ftp["password"] = "********"
    item["ftp_backup"] = ftp
    webhooks = []
    for webhook in item.get("webhooks", []):
        public_webhook = dict(webhook)
        if public_webhook.get("url"):
            public_webhook["url"] = "********"
        webhooks.append(public_webhook)
    item["webhooks"] = webhooks
    item.pop("webhook", None)
    item["installed"] = (Path(inst["path"]) / "enshrouded_server.exe").exists()
    item["config_exists"] = (Path(inst["path"]) / "enshrouded_server.json").exists()
    item["query_port"] = instance_query_port(inst["id"])
    return item


def public_removed_instance(inst):
    item = dict(inst)
    item.pop("ftp_backup", None)
    item.pop("webhook", None)
    item.pop("webhooks", None)
    return item


def server_root_path():
    root = Path(config().get("server_root") or (ROOT / "Servers"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def backup_root_path():
    root = Path(config().get("backup_root") or BACKUP_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def managed_install_path(name):
    root = server_root_path()
    base = slugify(name) or "server"
    path = root / base
    counter = 2
    while path.exists():
        path = root / f"{base}-{counter}"
        counter += 1
    return path


def clamp_backup_interval(minutes):
    cfg = config()
    minimum = int(cfg.get("min_backup_interval_minutes", 15))
    maximum = int(cfg.get("max_backup_interval_minutes", 10080))
    value = int(minutes or minimum)
    if value < minimum or value > maximum:
        raise ValueError(f"Backup interval must be between {minimum} and {maximum} minutes")
    return value


def add_instance(name, path, select=True, owner_user_id=""):
    server_dir = Path(path)
    if not server_dir.exists():
        server_dir.mkdir(parents=True, exist_ok=True)
    if (server_dir / "enshrouded_server.exe").exists() and not (server_dir / "enshrouded_server.json").exists():
        write_log(f"Instance {name} has server exe but no config yet; Enshrouded will create one on first start")
    with CONFIG_LOCK:
        cfg = config()
        base_id = slugify(name) or "server"
        used = {inst["id"] for inst in cfg.get("instances", [])}
        instance_id = base_id
        counter = 2
        while instance_id in used:
            instance_id = f"{base_id}-{counter}"
            counter += 1
        inst = default_instance(name, server_dir)
        inst["id"] = instance_id
        inst["owner_user_id"] = owner_user_id
        cfg.setdefault("instances", []).append(inst)
        if select:
            cfg["selected_instance_id"] = inst["id"]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Added server instance {name} at {server_dir}")
    return inst


def select_instance(instance_id):
    with CONFIG_LOCK:
        cfg = config()
        if not any(inst["id"] == instance_id for inst in cfg.get("instances", [])):
            raise FileNotFoundError("Unknown server instance")
        cfg["selected_instance_id"] = instance_id
        save_json(MANAGER_CONFIG, cfg)
    return get_instance(instance_id)


def update_instance(instance_id, patch):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for inst in cfg.get("instances", []):
            if inst["id"] == instance_id:
                target = inst
                break
        if target is None:
            raise FileNotFoundError("Unknown server instance")
        for key in ["name", "auto_restart", "start_on_manager_launch", "update_before_start", "public_server", "scheduled_restarts", "last_backup_key"]:
            if key in patch:
                target[key] = patch[key]
        if "scheduled_backup_enabled" in patch:
            target["scheduled_backup_enabled"] = bool(patch["scheduled_backup_enabled"])
        if "backup_interval_minutes" in patch:
            target["backup_interval_minutes"] = clamp_backup_interval(patch["backup_interval_minutes"])
        if "path" in patch and patch["path"]:
            target["path"] = str(Path(patch["path"]))
        if "ftp_backup" in patch:
            ftp = dict(target.get("ftp_backup", default_ftp_backup()))
            incoming = patch["ftp_backup"]
            for key in ["enabled", "host", "port", "username", "remote_dir", "passive"]:
                if key in incoming:
                    ftp[key] = incoming[key]
            if incoming.get("password") and incoming.get("password") != "********":
                ftp["password"] = incoming["password"]
            target["ftp_backup"] = ftp
        if "webhook" in patch:
            incoming = dict(patch["webhook"])
            if target.get("webhooks"):
                incoming.setdefault("id", target["webhooks"][0].get("id"))
            upsert_webhook_on_instance(target, incoming, allow_empty_url=True)
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Updated server instance {instance_id}")
    return get_instance(instance_id)


def upsert_webhook_on_instance(instance, incoming, allow_empty_url=False):
    webhooks = instance.setdefault("webhooks", [])
    webhook_id = str(incoming.get("id") or "").strip()
    current = next((item for item in webhooks if item.get("id") == webhook_id), None)
    if webhook_id and current is None:
        raise FileNotFoundError("Unknown webhook for this server")
    creating = current is None
    if creating:
        current = default_webhook(f"Webhook {len(webhooks) + 1}")
        if webhook_id:
            current["id"] = webhook_id
        webhooks.append(current)

    if "name" in incoming:
        current["name"] = str(incoming.get("name") or "").strip()[:80]
    if not current.get("name"):
        current["name"] = f"Webhook {webhooks.index(current) + 1}"
    if "enabled" in incoming:
        current["enabled"] = bool(incoming["enabled"])
    if "mode" in incoming:
        current["mode"] = incoming["mode"] if incoming["mode"] in {"discord", "json"} else "discord"
    if "events" in incoming:
        current["events"] = [event for event in incoming.get("events", []) if event in WEBHOOK_EVENTS]
    incoming_url = str(incoming.get("url") or "").strip()
    if incoming_url and incoming_url != "********":
        parsed = urlparse(incoming_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Webhook URL must be a complete http:// or https:// URL")
        current["url"] = incoming_url
    if incoming.get("clear_url"):
        current["url"] = ""
    if not current.get("url") and not allow_empty_url:
        if creating:
            webhooks.remove(current)
        raise ValueError("Webhook URL is required")
    return current


def save_instance_webhook(instance_id, incoming):
    with CONFIG_LOCK:
        cfg = config()
        target = next((inst for inst in cfg.get("instances", []) if inst.get("id") == instance_id), None)
        if target is None:
            raise FileNotFoundError("Unknown server instance")
        webhook = upsert_webhook_on_instance(target, incoming)
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Saved webhook {webhook['name']} for server instance {instance_id}")
    return webhook


def delete_instance_webhook(instance_id, webhook_id):
    with CONFIG_LOCK:
        cfg = config()
        target = next((inst for inst in cfg.get("instances", []) if inst.get("id") == instance_id), None)
        if target is None:
            raise FileNotFoundError("Unknown server instance")
        webhooks = target.setdefault("webhooks", [])
        webhook = next((item for item in webhooks if item.get("id") == webhook_id), None)
        if webhook is None:
            raise FileNotFoundError("Unknown webhook for this server")
        target["webhooks"] = [item for item in webhooks if item.get("id") != webhook_id]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Deleted webhook {webhook.get('name', webhook_id)} from server instance {instance_id}")
    return True


def safe_delete_server_directory(server_path):
    target = Path(server_path).resolve()
    if not target.exists():
        return False
    if not target.is_dir():
        raise ValueError("Server path is not a directory")
    if target.parent == target:
        raise ValueError("Refusing to delete a drive root")
    if target == ROOT.resolve() or target == APP_DIR.resolve():
        raise ValueError("Refusing to delete the manager directory")
    markers = [
        target / "enshrouded_server.exe",
        target / "enshrouded_server.json",
        target / "steamapps",
    ]
    if not any(marker.exists() for marker in markers):
        raise ValueError("Refusing to delete a folder that does not look like an Enshrouded server install")
    shutil.rmtree(target)
    return True


def remove_instance(instance_id, delete_files=False):
    sup = SUPERVISORS.get(instance_id)
    if sup and sup.status().get("running"):
        raise RuntimeError("Stop the server before removing this instance")
    path_to_delete = None
    with CONFIG_LOCK:
        cfg = config()
        removed = None
        for inst in cfg.get("instances", []):
            if inst["id"] == instance_id:
                removed = dict(inst)
                break
        before = len(cfg.get("instances", []))
        cfg["instances"] = [inst for inst in cfg.get("instances", []) if inst["id"] != instance_id]
        if len(cfg["instances"]) == before:
            raise FileNotFoundError("Unknown server instance")
        if delete_files:
            path_to_delete = removed.get("path")
            cfg["removed_instances"] = [item for item in cfg.get("removed_instances", []) if item.get("id") != instance_id]
        else:
            removed["removed_at"] = now_iso()
            cfg.setdefault("removed_instances", [])
            cfg["removed_instances"] = [item for item in cfg["removed_instances"] if item.get("id") != instance_id]
            cfg["removed_instances"].append(removed)
        if cfg.get("selected_instance_id") == instance_id:
            cfg["selected_instance_id"] = cfg["instances"][0]["id"] if cfg["instances"] else ""
        save_json(MANAGER_CONFIG, cfg)
    SUPERVISORS.pop(instance_id, None)
    if path_to_delete:
        safe_delete_server_directory(path_to_delete)
        write_log(f"Removed server instance {instance_id} and deleted files at {path_to_delete}")
    else:
        write_log(f"Removed server instance {instance_id} from manager registry")
    return True


def restore_instance(instance_id):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for item in cfg.get("removed_instances", []):
            if item.get("id") == instance_id:
                target = dict(item)
                break
        if not target:
            raise FileNotFoundError("Unknown removed server")
        target.pop("removed_at", None)
        used = {inst["id"] for inst in cfg.get("instances", [])}
        if target["id"] in used:
            base_id = target["id"]
            counter = 2
            while target["id"] in used:
                target["id"] = f"{base_id}-restored-{counter}"
                counter += 1
        cfg.setdefault("instances", []).append(target)
        cfg["removed_instances"] = [item for item in cfg.get("removed_instances", []) if item.get("id") != instance_id]
        if not cfg.get("selected_instance_id"):
            cfg["selected_instance_id"] = target["id"]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Restored removed server instance {instance_id}")
    return target


def clear_removed_instances():
    with CONFIG_LOCK:
        cfg = config()
        cfg["removed_instances"] = []
        save_json(MANAGER_CONFIG, cfg)
    write_log("Cleared removed server history")


def delete_removed_instance_files(instance_id):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for item in cfg.get("removed_instances", []):
            if item.get("id") == instance_id:
                target = dict(item)
                break
        if not target:
            raise FileNotFoundError("Unknown removed server")
    deleted = safe_delete_server_directory(target.get("path", ""))
    with CONFIG_LOCK:
        cfg = config()
        cfg["removed_instances"] = [item for item in cfg.get("removed_instances", []) if item.get("id") != instance_id]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Deleted removed server files for {instance_id} at {target.get('path', '')}")
    return deleted


def invite_public(invite):
    item = dict(invite)
    item["status"] = invite_status(invite)
    return item


def invite_status(invite):
    if invite.get("invalidated_at"):
        return "expired"
    if invite.get("used_at"):
        return "used"
    expires_at = invite.get("expires_at")
    if expires_at:
        try:
            if dt.datetime.fromisoformat(expires_at) <= dt.datetime.now():
                return "expired"
        except ValueError:
            return "expired"
    return "generated"


def visible_invites_for_user(user):
    visible_ids = {inst["id"] for inst in visible_instances_for_user(user)}
    items = []
    for invite in config().get("invite_codes", []):
        if is_admin(user):
            items.append(invite_public(invite))
            continue
        if is_server_owner(user) and invite.get("created_by_user_id") == user.get("id"):
            items.append(invite_public(invite))
            continue
        if is_server_owner(user) and set(invite.get("assigned_instance_ids", [])) & visible_ids:
            items.append(invite_public(invite))
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def update_invite_profiles(patch):
    with CONFIG_LOCK:
        cfg = config()
        profiles = cfg.setdefault("invite_profiles", default_invite_profiles())
        for key in INVITE_TYPES:
            incoming = patch.get(key)
            if not incoming:
                continue
            profile = profiles.setdefault(key, dict(INVITE_TYPES[key]))
            profile["label"] = INVITE_TYPES[key]["label"]
            profile["role"] = INVITE_TYPES[key]["role"]
            profile["permissions"] = [p for p in incoming.get("permissions", profile.get("permissions", [])) if p in ALL_PERMISSIONS]
        save_json(MANAGER_CONFIG, cfg)
    return cfg["invite_profiles"]


def generate_invite_code(body, creator):
    if not can_manage_invites(creator):
        raise PermissionError("Permission denied")
    code_type = body.get("code_type", "basic_user")
    if not invite_type_allowed_for_user(creator, code_type):
        raise PermissionError("This account cannot generate that invite type")
    requested_ids = body.get("assigned_instance_ids", [])
    assigned_ids = scoped_instance_ids_for_user(creator, requested_ids)
    if not assigned_ids and not is_admin(creator):
        assigned_ids = [inst["id"] for inst in visible_instances_for_user(creator)]
    if not assigned_ids and not is_admin(creator):
        raise ValueError("Server owners must scope invite codes to one of their servers")
    never_expires = bool(body.get("never_expires", False))
    expires_at = ""
    if not never_expires:
        amount = int(body.get("duration_amount", 1))
        unit = body.get("duration_unit", "days")
        if amount < 1:
            raise ValueError("Invite duration must be at least 1")
        minutes = amount if unit == "minutes" else amount * 24 * 60
        expires_at = (dt.datetime.now() + dt.timedelta(minutes=minutes)).replace(microsecond=0).isoformat()
    profile = config().get("invite_profiles", default_invite_profiles()).get(code_type, INVITE_TYPES[code_type])
    code = secrets.token_urlsafe(12)
    title = str(body.get("title", "")).strip()[:120]
    description = str(body.get("description", "")).strip()[:240]
    invite = {
        "id": secrets.token_hex(8),
        "code": code,
        "code_type": code_type,
        "title": title,
        "description": description,
        "label": profile.get("label", INVITE_TYPES[code_type]["label"]),
        "role": profile.get("role", INVITE_TYPES[code_type]["role"]),
        "permissions": [p for p in profile.get("permissions", []) if p in ALL_PERMISSIONS],
        "assigned_instance_ids": assigned_ids,
        "created_by_user_id": creator.get("id"),
        "created_by_username": creator.get("username"),
        "created_at": now_iso(),
        "expires_at": expires_at,
        "never_expires": never_expires,
        "used_at": "",
        "used_by_user_id": "",
        "used_by_username": "",
        "invalidated_at": "",
    }
    with CONFIG_LOCK:
        cfg = config()
        cfg.setdefault("invite_codes", []).append(invite)
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Generated {invite['label']} invite code by {creator.get('username')}")
    return invite_public(invite)


def invalidate_invite_code(invite_id, user):
    with CONFIG_LOCK:
        cfg = config()
        for invite in cfg.get("invite_codes", []):
            if invite.get("id") == invite_id:
                if not is_admin(user) and invite.get("created_by_user_id") != user.get("id"):
                    raise PermissionError("Permission denied")
                if invite.get("used_at"):
                    raise ValueError("Used invite codes cannot be invalidated")
                invite["invalidated_at"] = now_iso()
                save_json(MANAGER_CONFIG, cfg)
                write_log(f"Invalidated invite code {invite_id}")
                return invite_public(invite)
    raise FileNotFoundError("Unknown invite code")


def can_clear_invite(invite, user):
    if is_admin(user):
        return True
    return is_server_owner(user) and invite.get("created_by_user_id") == user.get("id")


def clear_expired_invite_code(invite_id, user):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for invite in cfg.get("invite_codes", []):
            if invite.get("id") == invite_id:
                target = invite
                break
        if target is None:
            raise FileNotFoundError("Unknown invite code")
        if invite_status(target) != "expired":
            raise ValueError("Only expired invite codes can be cleared")
        if not can_clear_invite(target, user):
            raise PermissionError("Permission denied")
        cfg["invite_codes"] = [invite for invite in cfg.get("invite_codes", []) if invite.get("id") != invite_id]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Cleared expired invite code {invite_id}")
    return True


def clear_expired_invite_codes(user):
    with CONFIG_LOCK:
        cfg = config()
        before = len(cfg.get("invite_codes", []))
        cfg["invite_codes"] = [
            invite for invite in cfg.get("invite_codes", [])
            if invite_status(invite) != "expired" or not can_clear_invite(invite, user)
        ]
        removed = before - len(cfg["invite_codes"])
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Cleared {removed} expired invite code(s)")
    return removed


def clear_used_invite_code(invite_id, user):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for invite in cfg.get("invite_codes", []):
            if invite.get("id") == invite_id:
                target = invite
                break
        if target is None:
            raise FileNotFoundError("Unknown invite code")
        if invite_status(target) != "used":
            raise ValueError("Only used invite codes can be cleared")
        if not can_clear_invite(target, user):
            raise PermissionError("Permission denied")
        cfg["invite_codes"] = [invite for invite in cfg.get("invite_codes", []) if invite.get("id") != invite_id]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Cleared used invite code {invite_id}")
    return True


def clear_used_invite_codes(user):
    with CONFIG_LOCK:
        cfg = config()
        before = len(cfg.get("invite_codes", []))
        cfg["invite_codes"] = [
            invite for invite in cfg.get("invite_codes", [])
            if invite_status(invite) != "used" or not can_clear_invite(invite, user)
        ]
        removed = before - len(cfg["invite_codes"])
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Cleared {removed} used invite code(s)")
    return removed


def redeem_invite_code(body):
    code = body.get("code", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    steam_name = body.get("steam_name", "").strip()
    steam_email = body.get("steam_email", "").strip()
    if not code or not username or not password or not steam_name or not steam_email:
        raise ValueError("Code, username, password, Steam name, and Steam email are required")
    with CONFIG_LOCK:
        cfg = config()
        invite = None
        for item in cfg.get("invite_codes", []):
            if item.get("code") == code:
                invite = item
                break
        if invite is None:
            raise ValueError("Invite code was not found")
        if invite_status(invite) != "generated":
            raise ValueError("Invite code is no longer valid")
        if any(user.get("username", "").lower() == username.lower() for user in cfg.get("users", [])):
            raise ValueError("Username is already in use")
        user = default_user(
            username,
            password,
            role=invite.get("role", "user"),
            permissions=[p for p in invite.get("permissions", []) if p in ALL_PERMISSIONS],
            assigned_instance_ids=invite.get("assigned_instance_ids", []),
            must_change_password=False,
        )
        user["steam_name"] = steam_name
        user["steam_email"] = steam_email
        user["created_by_invite_code"] = invite.get("code")
        base_id = slugify(username) or "user"
        used = {item["id"] for item in cfg.get("users", [])}
        user_id = base_id
        counter = 2
        while user_id in used:
            user_id = f"{base_id}-{counter}"
            counter += 1
        user["id"] = user_id
        cfg.setdefault("users", []).append(user)
        invite["used_at"] = now_iso()
        invite["used_by_user_id"] = user["id"]
        invite["used_by_username"] = user["username"]
        save_json(MANAGER_CONFIG, cfg)
    write_log(f"Invite code redeemed by {username}")
    return user_public(user)


def steamcmd_path():
    return ROOT / "Steamcmd" / "steamcmd.exe"


def safe_extract_zip(archive_path, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            safe_child(destination, destination / member.filename)
        archive.extractall(destination)


def ensure_steamcmd(status=None):
    exe = steamcmd_path()
    if exe.exists():
        if status:
            status("SteamCMD already installed")
        return exe
    target = exe.parent
    target.mkdir(parents=True, exist_ok=True)
    archive = DATA_DIR / "steamcmd.zip"
    write_log(f"Downloading SteamCMD from {STEAMCMD_URL}")
    if status:
        status("Downloading SteamCMD")
    urllib.request.urlretrieve(STEAMCMD_URL, archive)
    if status:
        status("Extracting SteamCMD")
    safe_extract_zip(archive, target)
    archive.unlink(missing_ok=True)
    if not exe.exists():
        raise FileNotFoundError("SteamCMD download completed, but steamcmd.exe was not found")
    write_log(f"Installed SteamCMD to {target}")
    return exe


def install_instance(name, install_dir=None, query_port=None, status=None, owner_user_id="", folder_name=None, instance_id=None):
    if instance_id:
        inst = get_instance(instance_id)
        target = Path(inst["path"])
        name = inst["name"]
    else:
        target = Path(install_dir) if install_dir else managed_install_path(folder_name or name)
        target.mkdir(parents=True, exist_ok=True)
        if status:
            status(f"Registering instance at {target}")
        inst = add_instance(name, target, select=True, owner_user_id=owner_user_id)
    update_instance_metadata(inst["id"], installation_status="installing", installation_query_port=query_port or DEFAULT_QUERY_PORT)
    try:
        run_update(inst["id"], status=status)
        cfg_path = instance_config_path(inst["id"])
        if not cfg_path.exists():
            if status:
                status("Creating enshrouded_server.json with selected query port")
            save_json(cfg_path, default_server_config(name, query_port or DEFAULT_QUERY_PORT))
        if status:
            status("Starting server once to validate enshrouded_server.json")
        generate_initial_server_config(inst["id"], status=status)
        if cfg_path.exists():
            cfg = load_json(cfg_path, {})
            if query_port:
                cfg["queryPort"] = int(query_port)
            cfg.setdefault("name", name)
            save_json(cfg_path, cfg)
            if status:
                status("enshrouded_server.json created; server is ready for configuration")
        write_log(f"Installed Enshrouded dedicated server instance {name} at {target}")
        return update_instance_metadata(inst["id"], installation_status="ready")
    except Exception:
        update_instance_metadata(inst["id"], installation_status="failed")
        raise


def save_server_config(server_config, instance_id=None, restart_if_running=False, public_server=None):
    inst = get_instance(instance_id)
    if public_server is not None:
        inst = update_instance(inst["id"], {"public_server": bool(public_server)})
    server_config = normalize_server_config(server_config, public_server=inst.get("public_server", False))
    validate_server_config(server_config)
    sup = supervisor(inst["id"])
    was_running = sup.status().get("running", False)
    if was_running and not restart_if_running:
        raise RuntimeError("Server is running. Confirm restart before saving config changes.")
    if was_running:
        write_log(f"Restarting {inst['name']} to apply config changes")
        sup.stop()
    save_json(instance_config_path(inst["id"]), server_config)
    write_log(f"Enshrouded server JSON config updated for {inst['name']}")
    if was_running:
        sup.start(update_first=False)
        return {"restarted": True}
    return {"restarted": False}


def version_parts(version):
    cleaned = str(version or "").strip().lstrip("vV")
    base, separator, prerelease = cleaned.partition("-")
    parts = []
    for chunk in base.split(".")[:4]:
        match = re.match(r"\d+", chunk)
        parts.append(int(match.group(0)) if match else 0)
    while len(parts) < 4:
        parts.append(0)
    prerelease_numbers = [int(value) for value in re.findall(r"\d+", prerelease)]
    stable_rank = 1 if not separator else 0
    prerelease_revision = prerelease_numbers[-1] if prerelease_numbers else 0
    suffix = re.search(r"([ab])$", base)
    suffix_rank = {"a": 1, "b": 2}.get(suffix.group(1), 0) if suffix else 0
    return tuple(parts + [suffix_rank, stable_rank, prerelease_revision])


def stable_channel_return(candidate, current, channel):
    # Only allow an explicit return from our Windows beta to its paired stable build.
    return channel == "stable" and str(current).endswith("b") and candidate == str(current)[:-1] + "a"


def public_manager_updates(source=None):
    updates = dict(source or default_manager_updates())
    token_saved = bool(updates.get("github_token"))
    if token_saved:
        updates["github_token"] = "********"
    package_available = bool(updates.get("package_available", False))
    pending_version = str(updates.get("installed_pending_version") or "")
    pending_restart = bool(updates.get("restart_required") and pending_version)
    if updates.get("last_error"):
        release_state = "error"
    elif pending_restart and pending_version != APP_VERSION:
        release_state = "installed_pending_restart"
    else:
        release_state = manager_release_state(updates.get("latest_version", ""), package_available,
                                              channel=updates.get("channel", "auto"))
    updates.update({
        "installed_version": APP_VERSION,
        "release_state": release_state,
        "update_available": release_state in {"available", "package_missing"},
        "package_available": package_available,
        "token_saved": token_saved,
        "using_default_public_repository": str(updates.get("repo") or GITHUB_REPO).strip().lower() == GITHUB_REPO.lower(),
    })
    return updates


def is_newer_version(candidate, current=APP_VERSION):
    return version_parts(candidate) > version_parts(current)


def github_headers(token=""):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ESM-Z/{APP_VERSION}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def https_context(allow_unverified=False):
    if allow_unverified:
        return ssl._create_unverified_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def urlopen_https(req, timeout=20):
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=https_context(False))
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        verify_failed = isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
        if not verify_failed:
            raise
        write_log("HTTPS certificate verification failed; retrying GitHub request with certificate verification disabled. Update Windows/Python certificates when possible.")
        return urllib.request.urlopen(req, timeout=timeout, context=https_context(True))


def github_json(url, token=""):
    req = urllib.request.Request(url, headers=github_headers(token))
    with urlopen_https(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def find_release_asset(release):
    assets = release.get("assets", [])
    for prefix in RELEASE_PACKAGE_PREFIXES:
        for asset in assets:
            name = asset.get("name", "")
            if name.startswith(prefix) and name.endswith(".zip"):
                return asset
    return None


def release_is_prerelease(release):
    tag = str(release.get("tag_name") or "").strip().lstrip("vV")
    return bool(release.get("prerelease")) or "-" in tag or bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+b", tag))


def latest_release_for_host(repo, token="", channel="auto", current_version=APP_VERSION):
    channel = str(channel or "auto").strip().lower()
    include_prereleases = channel in {"prerelease", "beta"} or (channel == "auto" and "-" in str(current_version))
    releases = github_json(f"https://api.github.com/repos/{repo}/releases?per_page=50", token=token)
    candidates = []
    for release in releases if isinstance(releases, list) else []:
        if release.get("draft") or not release.get("tag_name"):
            continue
        if channel == "beta":
            tag = str(release["tag_name"]).lstrip("vV")
            if release_is_prerelease(release) and not re.fullmatch(r"\d+\.\d+\.\d+\.\d+b", tag):
                continue
        if release_is_prerelease(release) and not include_prereleases:
            continue
        candidates.append(release)
    if not candidates:
        raise RuntimeError("No published GitHub release matches the selected update channel")
    return max(candidates, key=lambda item: version_parts(item.get("tag_name", "")))


def find_checksum_asset(release, package_asset):
    expected_name = f"{package_asset.get('name', '')}.sha256"
    return next((asset for asset in release.get("assets", []) if asset.get("name") == expected_name), None)


def manager_updates_config():
    return config().get("manager_updates", default_manager_updates())


def check_manager_updates(force=False, channel=None):
    if channel is not None and channel not in {"stable", "beta"}:
        raise ValueError("Select the stable or beta update channel")
    with CONFIG_LOCK:
        cfg = config()
        updates = cfg.setdefault("manager_updates", default_manager_updates())
        if channel is not None and channel != updates.get("channel"):
            updates.update(channel=channel, last_checked_at="", latest_version="", latest_url="",
                           last_error="", package_available=False, update_available=False, release_state="unchecked")
            save_json(MANAGER_CONFIG, cfg)
        if not updates.get("enabled", True) and not force:
            return dict(updates)
        interval_hours = max(1, int(updates.get("interval_hours", 24) or 24))
        if not force and updates.get("last_checked_at"):
            try:
                last_checked = dt.datetime.fromisoformat(updates["last_checked_at"])
                if dt.datetime.now() - last_checked < dt.timedelta(hours=interval_hours):
                    return dict(updates)
            except ValueError:
                pass
        repo = str(updates.get("repo") or GITHUB_REPO).strip()
        token = str(updates.get("github_token") or "").strip()
        channel = str(updates.get("channel") or "auto").strip()
    try:
        release = latest_release_for_host(repo, token=token, channel=channel)
        tag = str(release.get("tag_name") or "").lstrip("v")
        asset = find_release_asset(release)
        release_state = manager_release_state(tag, bool(asset), channel=channel)
        update_available = release_state in {"available", "package_missing"}
        latest_url = asset.get("browser_download_url", "") if asset else release.get("html_url", "")
        with CONFIG_LOCK:
            cfg = config()
            updates = cfg.setdefault("manager_updates", default_manager_updates())
            if updates.get("channel", "auto") != channel or updates.get("repo", GITHUB_REPO) != repo:
                return dict(updates)
            was_available = bool(updates.get("update_available", False))
            pending_restart = bool(
                updates.get("restart_required")
                and str(updates.get("installed_pending_version") or "") == tag
                and tag != APP_VERSION
            )
            if pending_restart:
                release_state = "installed_pending_restart"
                update_available = False
            updates.update({
                "last_checked_at": now_iso(),
                "latest_version": tag,
                "latest_url": latest_url,
                "update_available": update_available,
                "package_available": bool(asset),
                "release_state": release_state,
                "latest_published_at": str(release.get("published_at") or ""),
                "last_error": "",
            })
            save_json(MANAGER_CONFIG, cfg)
        if update_available and not was_available:
            notify_webhook_event(
                "manager.update.available",
                message=f"ESM-Z v{tag} is available. Current version is v{APP_VERSION}.",
                details={"latest_version": tag, "current_version": APP_VERSION, "url": latest_url},
            )
        return dict(manager_updates_config())
    except Exception as exc:
        with CONFIG_LOCK:
            cfg = config()
            updates = cfg.setdefault("manager_updates", default_manager_updates())
            if updates.get("channel", "auto") != channel or updates.get("repo", GITHUB_REPO) != repo:
                return dict(updates)
            updates.update({"last_checked_at": now_iso(), "release_state": "error", "last_error": str(exc)})
            save_json(MANAGER_CONFIG, cfg)
            return dict(updates)


def download_github_asset(asset, destination, token=""):
    req = urllib.request.Request(asset["browser_download_url"], headers=github_headers(token))
    with urlopen_https(req, timeout=60) as response, Path(destination).open("wb") as fh:
        shutil.copyfileobj(response, fh)


def verify_release_checksum(release, package_asset, package_path, token=""):
    checksum_asset = find_checksum_asset(release, package_asset)
    if not checksum_asset:
        return False
    req = urllib.request.Request(checksum_asset["browser_download_url"], headers=github_headers(token))
    with urlopen_https(req, timeout=20) as response:
        checksum_text = response.read().decode("ascii", errors="strict").strip()
    expected = checksum_text.split()[0].lower() if checksum_text else ""
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError("The release checksum file is not valid")
    actual = hashlib.sha256(Path(package_path).read_bytes()).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise RuntimeError("The downloaded update package failed SHA-256 verification")
    return True


def packaged_manager_version(manager_dir):
    manager_file = Path(manager_dir) / "manager.py"
    if not manager_file.is_file() or not (Path(manager_dir) / "static" / "index.html").is_file():
        raise RuntimeError("Downloaded update package is missing required ESM-Z files")
    match = re.search(r'^APP_VERSION = "([^"]+)"', manager_file.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise RuntimeError("Downloaded update package does not declare an ESM-Z version")
    return match.group(1)


def install_manager_update():
    updates = manager_updates_config()
    if updates.get("restart_required"):
        raise RuntimeError("An ESM-Z update is already installed. Restart the manager before installing another update.")
    if not updates.get("update_available"):
        raise RuntimeError("No manager update is currently available")
    repo = str(updates.get("repo") or GITHUB_REPO).strip()
    token = str(updates.get("github_token") or "").strip()
    channel = str(updates.get("channel") or "auto").strip()
    release = latest_release_for_host(repo, token=token, channel=channel)
    release_version = str(release.get("tag_name") or "").lstrip("v")
    if not (is_newer_version(release_version) or stable_channel_return(release_version, APP_VERSION, channel)):
        raise RuntimeError("The selected GitHub release is not newer than the running ESM-Z version")
    asset = find_release_asset(release)
    if not asset:
        raise RuntimeError("Latest GitHub release does not include a Python-required zip asset")
    update_status("downloading", f"Downloading ESM-Z v{release_version}.", target_version=release_version)
    package_dir = DATA_DIR / "manager_updates" / secrets.token_hex(16)
    package_dir.mkdir(parents=True, exist_ok=True)
    if Path(asset["name"]).name != asset["name"] or "\\" in asset["name"]:
        raise ValueError("Invalid release asset filename")
    package_path = package_dir / asset["name"]
    extract_dir = package_dir / "extract"
    backup_dir = package_dir / f"before-{APP_VERSION}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup_manager = backup_dir / "enshrouded_manager"
    try:
        download_github_asset(asset, package_path, token=token)
        update_status("verifying", "Verifying the downloaded package.")
        checksum_verified = verify_release_checksum(release, asset, package_path, token=token)
        if not checksum_verified:
            raise RuntimeError("This release has no SHA-256 checksum; remote installation was not started")
        safe_extract_zip(package_path, extract_dir)
        extracted_manager = extract_dir / "enshrouded_manager"
        if not extracted_manager.exists():
            raise RuntimeError("Downloaded update package does not contain enshrouded_manager")
        package_version = packaged_manager_version(extracted_manager)
        if package_version != release_version:
            raise RuntimeError(f"Update package version v{package_version} does not match release v{release_version}")
        if not (extracted_manager / "update_runtime.py").is_file():
            raise RuntimeError("This package predates remote restart support; install it manually instead")
        for source in extracted_manager.glob("*.py"):
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
        update_status("preparing", "Backing up manager files before restart.")
        if APP_DIR.exists():
            shutil.copytree(APP_DIR, backup_manager, ignore=shutil.ignore_patterns("data", "__pycache__"))
        cfg = config()
        host = cfg.get("bind_host", "127.0.0.1")
        host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(host, host)
        if ":" in host:
            host = f"[{host}]"
        return {
            "job": str(package_dir.resolve()), "app": str(APP_DIR.resolve()), "root": str(ROOT.resolve()),
            "source": str(extracted_manager.resolve()), "backup": str(backup_manager.resolve()),
            "status": str((DATA_DIR / "manager_updates" / "status.json").resolve()),
            "command": [sys.executable, "-u", str((APP_DIR / "manager.py").resolve())],
            "console_log": str((DATA_DIR / "manager_updates" / "update-console.log").resolve()),
            "parent_pid": os.getpid(), "target_version": release_version, "previous_version": APP_VERSION,
            "health_url": f"http://{host}:{int(cfg.get('port', 8080))}/api/health",
        }
    except Exception as exc:
        with CONFIG_LOCK:
            cfg = config()
            updates = cfg.setdefault("manager_updates", default_manager_updates())
            updates["last_error"] = str(exc)
            save_json(MANAGER_CONFIG, cfg)
        raise


def webhook_targets(event, instance_id=None):
    targets = []
    if instance_id:
        candidates = [get_instance(instance_id)]
    else:
        candidates = instances()
    seen = set()
    for inst in candidates:
        for webhook in inst.get("webhooks", []):
            url = webhook.get("url", "").strip()
            if not webhook.get("enabled") or not url or event not in webhook.get("events", []):
                continue
            key = (url, webhook.get("mode", "discord"))
            if key in seen:
                continue
            seen.add(key)
            targets.append((inst, dict(webhook)))
    return targets


def post_webhook(webhook, payload):
    mode = webhook.get("mode", "discord")
    if mode == "discord":
        body = {
            "username": "ESM-Z",
            "content": payload.get("message") or payload.get("event_label") or payload.get("event"),
        }
        if payload.get("server_name") or payload.get("details"):
            fields = []
            if payload.get("server_name"):
                fields.append({"name": "Server", "value": payload["server_name"], "inline": True})
            fields.append({"name": "Event", "value": payload.get("event_label", payload["event"]), "inline": True})
            if payload.get("details", {}).get("error"):
                fields.append({"name": "Error", "value": str(payload["details"]["error"])[:1000], "inline": False})
            body["embeds"] = [{"title": payload.get("event_label", payload["event"]), "fields": fields, "timestamp": payload["timestamp"]}]
    else:
        body = payload
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(webhook["url"], data=data, headers={"Content-Type": "application/json", "User-Agent": f"ESM-Z/{APP_VERSION}"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status


def send_webhook_event(event, instance_id=None, message="", details=None):
    if event not in WEBHOOK_EVENTS:
        return []
    sent = []
    for inst, webhook in webhook_targets(event, instance_id=instance_id):
        payload = {
            "event": event,
            "event_label": WEBHOOK_EVENTS[event],
            "timestamp": now_iso(),
            "server_id": inst.get("id", ""),
            "server_name": inst.get("name", ""),
            "message": message or WEBHOOK_EVENTS[event],
            "details": details or {},
            "manager_version": APP_VERSION,
        }
        try:
            status = post_webhook(webhook, payload)
            sent.append({"server_id": inst.get("id", ""), "webhook_id": webhook.get("id", ""), "status": status})
        except Exception as exc:
            write_log(f"Webhook delivery failed for {inst.get('name', 'manager')}: {exc}")
            sent.append({"server_id": inst.get("id", ""), "error": str(exc)})
    return sent


def notify_webhook_event(event, instance_id=None, message="", details=None):
    threading.Thread(target=send_webhook_event, args=(event, instance_id, message, details or {}), daemon=True).start()


def test_webhook(instance_id, webhook_id):
    inst = get_instance(instance_id)
    webhook = next((dict(item) for item in inst.get("webhooks", []) if item.get("id") == webhook_id), None)
    if webhook is None:
        raise FileNotFoundError("Unknown webhook for this server")
    if not webhook.get("url"):
        raise RuntimeError("No webhook URL is configured for this server")
    payload = {
        "event": "webhook.test",
        "event_label": "Webhook test",
        "timestamp": now_iso(),
        "server_id": inst.get("id", ""),
        "server_name": inst.get("name", ""),
        "message": f"Test webhook from ESM-Z for {inst['name']}.",
        "details": {"test": True},
        "manager_version": APP_VERSION,
    }
    status = post_webhook(webhook, payload)
    return [{"server_id": inst.get("id", ""), "webhook_id": webhook.get("id", ""), "status": status}]


class SteamCMDUpdateError(subprocess.CalledProcessError):
    def __init__(self, returncode, cmd, output=None, stage="update"):
        super().__init__(returncode, cmd, output=output)
        self.stage = stage

    def __str__(self):
        lines = (self.output or "").splitlines()
        errors = [line.strip() for line in lines
                  if re.search(r"error!|error:|failed to|not writable|access.*denied", line, re.IGNORECASE)
                  and "ilocalize::addfile" not in line.lower()]
        fatal = [line for line in errors if re.search(r"fatal|error!|error:|not writable|access.*denied", line, re.IGNORECASE)]
        detail = f" {(fatal or errors)[-1][:400]}" if errors else ""
        if self.stage == "bootstrap":
            result = f"SteamCMD initialization failed (exit code {self.returncode})."
            detail += " Check Steam connectivity and write permissions in the Steamcmd folder."
        else:
            result = (f"SteamCMD exited with code {self.returncode}." if self.returncode
                      else "SteamCMD did not confirm a successful install/update.")
        return f"{result}{detail} See Logs > esm-steamcmd.log for details."


def steamcmd_update_command(exe, target_dir):
    # A fresh anonymous session can reach app_update before this app's metadata is loaded.
    return [str(exe), "+force_install_dir", str(target_dir), "+login", "anonymous",
            "+app_info_update", "1", "+app_info_print", APP_ID,
            "+app_update", APP_ID, "validate", "+quit"]


def steamcmd_execute(command, log_path, stage="update", timeout=None):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sources = [Path(command[0]).parent / "logs" / name for name in
               ("bootstrap_log.txt", "stderr.txt", "content_log.txt", "appinfo_log.txt")]
    previous = {}
    for path in sources:
        if path.is_file():
            info = path.stat()
            previous[path] = (info.st_ino, info.st_size, info.st_mtime_ns)
    # Redirect directly to disk so progress is readable while SteamCMD is running.
    with log_path.open("ab") as output:
        output.write(f"\n[{now_iso()}] SteamCMD {stage} attempt\n".encode("utf-8"))
        output.flush()
        offset = output.tell()
        try:
            result = subprocess.run(command, cwd=str(Path(command[0]).parent), stdin=subprocess.DEVNULL,
                                    stdout=output, stderr=subprocess.STDOUT, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"SteamCMD {stage} timed out after {timeout} seconds. See Logs > esm-steamcmd.log.") from exc
    with log_path.open("rb") as output:
        output.seek(max(offset, log_path.stat().st_size - 32768))
        tail = output.read().decode("utf-8", errors="replace")
    for path in sources:
        if not path.is_file():
            continue
        info = path.stat()
        before = previous.get(path)
        if before == (info.st_ino, info.st_size, info.st_mtime_ns):
            continue
        start = before[1] if before and before[0] == info.st_ino and info.st_size >= before[1] else 0
        with path.open("rb") as source:
            source.seek(max(start, info.st_size - 16384))
            text = source.read(16384).decode("utf-8", errors="replace")
        diagnostic = f"\n--- SteamCMD {path.name} ({stage}) ---\n{text}"
        with log_path.open("ab") as output:
            output.write(diagnostic.encode("utf-8"))
        tail += diagnostic
    return result.returncode, tail


def prepare_steamcmd(exe, log_path, status=None):
    command = [str(exe), "+quit"]
    for attempt in range(3):
        message = f"Initializing SteamCMD ({attempt + 1}/3); SteamCMD may download its own updates before the game"
        write_log(message)
        if status:
            status(message)
        code, output = steamcmd_execute(command, log_path, stage="bootstrap", timeout=180)
        ready = "Steam Console Client" in output and re.search(r"Loading Steam API\.\.\..*?\bOK\b", output, re.DOTALL)
        if code == 0 and ready:
            return
        error = SteamCMDUpdateError(code, command, output=output, stage="bootstrap")
        if attempt == 2 or code not in {0, 7}:
            raise error
        write_log("SteamCMD initialization requested another launch; retrying initialization")
        time.sleep(1)


def steamcmd_update_attempt(command, log_path):
    code, tail = steamcmd_execute(command, log_path)
    success = re.search(rf"Success!\s+App\s+'{APP_ID}'\s+(?:fully installed|already up to date)", tail, re.IGNORECASE)
    if code or not success:
        raise SteamCMDUpdateError(code, command, output=tail)


def steamcmd_update_after_bootstrap(command, log_path, status=None):
    try:
        steamcmd_update_attempt(command, log_path)
    except SteamCMDUpdateError as exc:
        missing_config = re.search(
            rf"Failed to install app\s+'{APP_ID}'\s+\(Missing configuration\)",
            exc.output or "", re.IGNORECASE)
        if exc.returncode != 7 and not missing_config:
            raise
        message = ("SteamCMD could not load Enshrouded's app metadata; refreshing it and retrying the install once"
                   if missing_config else
                   "SteamCMD exited during its self-update; reinitializing it and retrying the game install once")
        write_log(message)
        if status:
            status(message)
        if not missing_config:
            prepare_steamcmd(Path(command[0]), log_path, status=status)
        steamcmd_update_attempt(command, log_path)


def reset_instance_steam_manifests(instance_id):
    target = instance_path(instance_id).resolve()
    steamapps = safe_child(target, target / "steamapps")
    manifests = [safe_child(target, steamapps / f"appmanifest_{app_id}.acf")
                 for app_id in (APP_ID, "228980")]
    backup = safe_child(target, steamapps / "esm-manifest-backups" /
                        f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}")
    moved = []
    try:
        for manifest in manifests:
            if manifest.is_file():
                backup.mkdir(parents=True, exist_ok=True)
                destination = backup / manifest.name
                manifest.rename(destination)
                moved.append((manifest, destination))
                write_log(f"Backed up Steam manifest to {destination}")
    except Exception:
        restore_instance_steam_manifests(moved)
        raise
    return moved


def restore_instance_steam_manifests(moved):
    for manifest, backup in moved:
        if not manifest.exists():
            shutil.copy2(backup, manifest)


def run_update(instance_id=None, status=None):
    inst = get_instance(instance_id)
    if status:
        status("Waiting for SteamCMD; other server installs or updates may be running")
    with STEAMCMD_LOCK:
        if supervisor(inst["id"]).status().get("running"):
            raise RuntimeError("Stop this server before running its SteamCMD update check.")
        try:
            exe = ensure_steamcmd(status=status)
            target_dir = instance_path(inst["id"])
            log_path = safe_child(target_dir, target_dir / "logs" / "esm-steamcmd.log")
            prepare_steamcmd(exe, log_path, status=status)
            command = steamcmd_update_command(exe, target_dir)
            write_log(f"Running SteamCMD app_update {APP_ID} validate for {inst['name']}; output: {log_path}")
            if status:
                status("Installing/updating Enshrouded Dedicated Server; progress is in Logs > esm-steamcmd.log")
            try:
                steamcmd_update_after_bootstrap(command, log_path, status=status)
            except SteamCMDUpdateError as exc:
                stuck_state = re.search(rf"App\s+'{APP_ID}'\s+state is\s+0x6\s+after update job", exc.output or "", re.IGNORECASE)
                if not stuck_state:
                    raise
                if supervisor(inst["id"]).status().get("running"):
                    raise RuntimeError("Server started during the update check; stop it before retrying.") from exc
                message = "SteamCMD reported state 0x6; backing up this server's Steam manifests and retrying once"
                write_log(message)
                if status:
                    status(message)
                moved = reset_instance_steam_manifests(inst["id"])
                try:
                    steamcmd_update_attempt(command, log_path)
                except Exception:
                    restore_instance_steam_manifests(moved)
                    raise
        except Exception as exc:
            warning = f"Update check failed: {exc}"
            update_instance_metadata(inst["id"], last_update_warning=warning)
            write_log(f"{warning} Server: {inst['name']}")
            notify_webhook_event("server.update.failed", inst["id"],
                                 message=f"Update check failed for {inst['name']}.", details={"error": str(exc)})
            raise
        write_log(f"SteamCMD update check completed for {inst['name']}")
        update_instance_metadata(inst["id"], last_updated_at=now_iso(), last_update_warning="")
        notify_webhook_event("server.updated", inst["id"], message=f"Update check completed for {inst['name']}.")
        if status:
            status("SteamCMD install/update completed")


def generate_initial_server_config(instance_id, status=None, timeout_seconds=180):
    config_path = instance_config_path(instance_id)
    if config_path.exists():
        if status:
            status("enshrouded_server.json exists; validating server start")
        sup = supervisor(instance_id)
        sup.start(update_first=False)
        time.sleep(6)
        proc_status = sup.status()
        if not proc_status.get("running"):
            code = proc_status.get("last_exit_code")
            raise RuntimeError(f"Server stopped during validation start with code {code} ({signed_exit_code(code)})")
        if status:
            status("Validation start succeeded; stopping server")
        sup.stop()
        return
    sup = supervisor(instance_id)
    sup.start(update_first=False)
    deadline = time.time() + timeout_seconds
    last_notice = 0
    while time.time() < deadline:
        if config_path.exists():
            if status:
                status("enshrouded_server.json created; stopping first-start server")
            sup.stop()
            return
        elapsed = int(timeout_seconds - (deadline - time.time()))
        if status and elapsed - last_notice >= 5:
            last_notice = elapsed
            status(f"Waiting for enshrouded_server.json ({elapsed}s)")
        time.sleep(1)
    sup.stop()
    raise TimeoutError("Timed out waiting for enshrouded_server.json to be created")


def start_install_job(body, user, retry_instance_id=None):
    if retry_instance_id:
        candidate = get_instance_for_user(user, retry_instance_id)
        if candidate["id"] != retry_instance_id:
            raise PermissionError("This server is not assigned to your account.")
        if supervisor(candidate["id"]).status().get("running"):
            raise ValueError("Stop this server before retrying its install.")
    with CONFIG_LOCK:
        if retry_instance_id:
            inst = get_instance_for_user(user, retry_instance_id)
            if inst["id"] != retry_instance_id:
                raise PermissionError("This server is not assigned to your account.")
            with JOBS_LOCK:
                if any(job.get("instance_id") == inst["id"] and job.get("status") == "running" for job in JOBS.values()):
                    raise ValueError("This server already has an install in progress.")
            if inst.get("installation_status") not in {"failed", "installing"} and instance_exe_path(inst["id"]).exists():
                raise ValueError("This server is already installed. Use Update Check instead.")
            query_port = (instance_query_port(inst["id"]) if instance_config_path(inst["id"]).exists()
                          else int(inst.get("installation_query_port") or DEFAULT_QUERY_PORT))
        else:
            check_server_creation_allowed(user)
            inst = None
            query_port = int(body.get("queryPort") or DEFAULT_QUERY_PORT)
        if query_port < 1 or query_port > 65535:
            raise ValueError("Query port must be between 1 and 65535")
        if any(instance_query_port(item["id"]) == query_port for item in instances() if not inst or item["id"] != inst["id"]):
            raise ValueError("Port in use. Select a new port")
        if inst is None:
            name = body.get("name") or body.get("folder_name") or "Enshrouded Server"
            target = Path(body["path"]) if body.get("path") else managed_install_path(body.get("folder_name") or name)
            if any(Path(item["path"]).resolve() == target.resolve() for item in instances()):
                raise ValueError("This directory is already registered. Use Retry Install for that instance.")
            inst = add_instance(name, target, select=True, owner_user_id=user.get("id", ""))
        update_instance_metadata(inst["id"], installation_status="installing", installation_query_port=query_port)
        job_id = new_job(
            "install_instance",
            owner_user_id=user.get("id", ""),
            owner_username=user.get("username", ""),
            instance_id=inst["id"],
            instance_name=inst["name"],
            folder_name=body.get("folder_name") or "",
            query_port=query_port,
        )
    def runner():
        try:
            def status(message):
                update_job(job_id, message=message)
                write_log(f"Install job {job_id}: {message}")

            inst = install_instance(
                get_job(job_id)["instance_name"],
                query_port=query_port,
                status=status,
                instance_id=get_job(job_id)["instance_id"],
            )
            update_job(
                job_id,
                status="complete",
                message="Server installed and ready for configuration",
                result={"instance": public_instance(inst)},
            )
            notify_webhook_event(
                "server.install.completed",
                inst["id"],
                message=f"{inst['name']} installed and is ready for configuration.",
                details={"job_id": job_id, "query_port": query_port},
            )
        except Exception as exc:
            update_job(job_id, status="failed", message="Install failed", error=str(exc))
            write_log(f"Install job {job_id} failed: {exc}")

    threading.Thread(target=runner, daemon=True).start()
    return job_id


def list_logs(instance_id=None):
    logs = []
    inst_dir = instance_path(instance_id)
    for base in [inst_dir / "logs", MANAGER_LOG.parent]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in [".log", ".txt"]:
                stat = path.stat()
                try:
                    name = str(path.relative_to(ROOT))
                except ValueError:
                    name = str(path)
                logs.append({
                    "name": name,
                    "size": stat.st_size,
                    "modified": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                })
    return sorted(logs, key=lambda item: item["modified"], reverse=True)


def list_logs_no_instance():
    logs = []
    if MANAGER_LOG.parent.exists():
        for path in MANAGER_LOG.parent.glob("*.log"):
            stat = path.stat()
            logs.append({
                "name": str(path.relative_to(ROOT)),
                "size": stat.st_size,
                "modified": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            })
    return sorted(logs, key=lambda item: item["modified"], reverse=True)


def read_tail(path_name, instance_id=None, max_bytes=80000):
    raw = Path(path_name)
    if raw.is_absolute():
        path = safe_child(instance_path(instance_id), raw)
    else:
        candidate = ROOT / path_name
        if candidate.exists():
            path = safe_child(ROOT, candidate)
        else:
            path = safe_child(instance_path(instance_id), instance_path(instance_id) / path_name)
    if not path.is_file():
        raise FileNotFoundError(path_name)
    with path.open("rb") as fh:
        if path.stat().st_size > max_bytes:
            fh.seek(-max_bytes, os.SEEK_END)
        data = fh.read()
    return data.decode("utf-8", errors="replace")


def backup_name(prefix="backup"):
    return f"{prefix}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"


def instance_backup_dir(instance_id=None):
    backup_dir = backup_root_path() / get_instance(instance_id)["id"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(push_ftp=False, instance_id=None):
    inst = get_instance(instance_id)
    backup_dir = instance_backup_dir(inst["id"])
    archive = backup_dir / backup_name(slugify(inst["name"]) or "enshrouded")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        config_path = instance_config_path(inst["id"])
        if config_path.exists():
            zf.write(config_path, "enshrouded_server.json")
        save_dir = instance_save_path(inst["id"])
        if save_dir.exists():
            for path in save_dir.rglob("*"):
                if path.is_file():
                    zf.write(path, Path("savegame") / path.relative_to(save_dir))
    write_log(f"Created local backup {archive.name}")
    notify_webhook_event("server.backup.created", inst["id"], message=f"Backup created for {inst['name']}: {archive.name}", details={"backup": archive.name})
    if push_ftp:
        push_backup_to_ftp(archive, inst["id"])
        notify_webhook_event("server.backup.ftp", inst["id"], message=f"FTP backup completed for {inst['name']}: {archive.name}", details={"backup": archive.name})
    return archive


def scheduled_backup_check(instance_id):
    inst = get_instance(instance_id)
    if not inst.get("scheduled_backup_enabled", False):
        return
    interval = clamp_backup_interval(inst.get("backup_interval_minutes", 1440))
    now = dt.datetime.now()
    slot = int(now.timestamp() // (interval * 60))
    key = f"{interval}:{slot}"
    if inst.get("last_backup_key") == key:
        return
    update_instance(instance_id, {"last_backup_key": key})
    write_log(f"Scheduled backup triggered for {inst['name']} every {interval} minutes")
    create_backup(push_ftp=bool(inst.get("ftp_backup", {}).get("enabled", False)), instance_id=instance_id)


def push_backup_to_ftp(path, instance_id=None):
    ftp_cfg = get_instance(instance_id).get("ftp_backup", {})
    if not ftp_cfg.get("enabled"):
        raise RuntimeError("FTP backup is not enabled")
    with ftplib.FTP() as ftp:
        ftp.connect(ftp_cfg["host"], int(ftp_cfg.get("port", 21)), timeout=30)
        ftp.login(ftp_cfg.get("username", ""), ftp_cfg.get("password", ""))
        ftp.set_pasv(bool(ftp_cfg.get("passive", True)))
        remote_dir = ftp_cfg.get("remote_dir") or "/"
        ftp.cwd(remote_dir)
        with path.open("rb") as fh:
            ftp.storbinary(f"STOR {path.name}", fh)
    write_log(f"Pushed backup {path.name} to FTP")


def save_import_history(instance_id):
    return list(get_instance(instance_id).get("save_imports", []))


def record_save_import(instance_id, source_name, source_path, previous_backup):
    with CONFIG_LOCK:
        cfg = config()
        target = None
        for inst in cfg.get("instances", []):
            if inst["id"] == instance_id:
                target = inst
                break
        if target is None:
            raise FileNotFoundError("Unknown server instance")
        item = {
            "source_name": source_name,
            "source_path": source_path,
            "previous_backup": previous_backup,
            "imported_at": now_iso(),
        }
        imports = [item] + list(target.get("save_imports", []))
        target["save_imports"] = imports[:25]
        save_json(MANAGER_CONFIG, cfg)
    return item


def replace_save_dir_from_directory(source_dir, instance_id):
    source = Path(source_dir)
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError("Selected save folder was not found")
    backup = create_backup(push_ftp=False, instance_id=instance_id)
    save_dir = instance_save_path(instance_id)
    if save_dir.exists():
        shutil.rmtree(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        target = safe_child(save_dir, save_dir / item.relative_to(source))
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    return backup.name


def save_world_id(filename):
    name = Path(str(filename).replace("\\", "/")).name
    match = SAVE_WORLD_RE.match(name)
    return match.group(1).lower() if match else ""


def describe_save_world(world_id, files, base_path=""):
    stats = []
    total = 0
    modified = 0
    sample_names = []
    for item in files:
        path = item if isinstance(item, Path) else Path(item.get("filename", ""))
        sample_names.append(path.name)
        if isinstance(item, Path):
            try:
                stat = item.stat()
            except OSError:
                continue
            total += stat.st_size
            modified = max(modified, stat.st_mtime)
        else:
            data = item.get("data", b"")
            total += len(data)
            modified = time.time()
    sample_names = sorted(set(sample_names))[:6]
    return {
        "id": base64.urlsafe_b64encode(f"{base_path}|{world_id}".encode("utf-8")).decode("ascii"),
        "world_id": world_id,
        "name": f"World files {world_id}",
        "path": str(base_path),
        "file_count": len(files),
        "size": total,
        "modified": dt.datetime.fromtimestamp(modified).isoformat(timespec="seconds") if modified else "",
        "files": sample_names,
    }


def group_save_world_paths(path):
    groups = {}
    try:
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            world_id = save_world_id(item.name)
            if world_id:
                groups.setdefault(world_id, []).append(item)
    except OSError:
        return {}
    return groups


def server_target_world_id(save_dir):
    groups = group_save_world_paths(save_dir) if save_dir.exists() else {}
    for world_id in KNOWN_WORLD_IDS:
        if world_id in groups:
            return world_id
    return DEFAULT_SERVER_WORLD_ID


def rename_world_relative(relative, source_world_id, target_world_id):
    relative = Path(relative)
    name = relative.name
    if name.lower().startswith(source_world_id.lower()):
        name = target_world_id + name[len(source_world_id):]
    return relative.parent / name


def stop_server_for_save_import(instance_id):
    sup = supervisor(instance_id)
    if sup.status().get("running"):
        write_log(f"Stopping {get_instance(instance_id)['name']} before save import")
        sup.stop()


def copy_save_world_files(files, base_dir, instance_id, source_world_id):
    stop_server_for_save_import(instance_id)
    backup = create_backup(push_ftp=False, instance_id=instance_id)
    save_dir = instance_save_path(instance_id)
    target_world_id = server_target_world_id(save_dir)
    if save_dir.exists():
        shutil.rmtree(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    imported = 0
    for item in files:
        relative = rename_world_relative(item.relative_to(base_dir), source_world_id, target_world_id)
        target = safe_child(save_dir, save_dir / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        imported += 1
    return backup.name, imported, target_world_id


def import_savegame(file_item, instance_id=None, source_name="Uploaded ZIP"):
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = IMPORT_DIR / backup_name("incoming")
    staging = IMPORT_DIR / backup_name("zip_extract")
    with tmp.open("wb") as fh:
        shutil.copyfileobj(file_item.file, fh)
    try:
        staging.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp, "r") as zf:
            for info in zf.infolist():
                target = safe_child(staging, staging / info.filename)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info, "r") as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
        groups = group_save_world_paths(staging)
        if len(groups) > 1:
            choices = ", ".join(sorted(groups))
            raise ValueError(f"That ZIP contains multiple Enshrouded worlds ({choices}). Use Choose Save Folder From This PC so you can select one world.")
        if not groups:
            raise ValueError("No Enshrouded world save files were found in that ZIP.")
        world_id, files = next(iter(groups.items()))
        backup, imported, target_world_id = copy_save_world_files(files, staging, instance_id, world_id)
        record_save_import(instance_id, f"{source_name}: world {world_id} as {target_world_id} ({imported} files)", "uploaded zip", backup)
        write_log(f"Imported savegame zip world {world_id} as {target_world_id}; previous save backed up as {backup}")
        return backup
    finally:
        tmp.unlink(missing_ok=True)
        if staging.exists():
            shutil.rmtree(staging)


def known_save_roots():
    roots = []
    env = os.environ
    for key in ["USERPROFILE", "LOCALAPPDATA", "APPDATA"]:
        value = env.get(key)
        if value:
            roots.append(Path(value))
    roots.extend([
        Path.home(),
        Path("C:/Program Files (x86)/Steam/userdata"),
        Path("C:/Program Files/Steam/userdata"),
    ])
    users_dir = Path("C:/Users")
    if users_dir.exists():
        try:
            user_dirs = list(users_dir.iterdir())
        except OSError:
            user_dirs = []
        for user_dir in user_dirs:
            if user_dir.is_dir():
                roots.extend([
                    user_dir / "AppData" / "Roaming",
                    user_dir / "AppData" / "Local",
                    user_dir / "Saved Games",
                    user_dir / "Documents",
                ])
    unique = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def save_candidate_from_path(path):
    if not path.exists() or not path.is_dir():
        return None
    groups = group_save_world_paths(path)
    if not groups:
        return None
    worlds = [describe_save_world(world_id, files, str(path)) for world_id, files in groups.items()]
    worlds.sort(key=lambda item: item["modified"], reverse=True)
    return worlds


def discover_local_savegames():
    patterns = [
        Path("Steam/userdata/*/1203620/remote"),
        Path("userdata/*/1203620/remote"),
        Path("1203620/remote"),
        Path("Goldberg SteamEmu Saves/1203620/remote"),
        Path("Enshrouded"),
    ]
    candidates = {}
    for root in known_save_roots():
        if not root.exists():
            continue
        for pattern in patterns:
            try:
                matches = list(root.glob(str(pattern)))
            except OSError:
                matches = []
            for path in matches:
                for candidate in save_candidate_from_path(path) or []:
                    candidates[f"{candidate['path']}|{candidate['world_id']}"] = candidate
        if root.name == "userdata":
            try:
                userdata_matches = list(root.glob("*/1203620/remote"))
            except OSError:
                userdata_matches = []
            for path in userdata_matches:
                for candidate in save_candidate_from_path(path) or []:
                    candidates[f"{candidate['path']}|{candidate['world_id']}"] = candidate
    return sorted(candidates.values(), key=lambda item: item["modified"], reverse=True)[:50]


def import_discovered_savegame(candidate_id, instance_id):
    try:
        decoded = base64.urlsafe_b64decode(candidate_id.encode("ascii")).decode("utf-8")
    except Exception:
        raise ValueError("Invalid save selection")
    raw_path, _, world_id = decoded.rpartition("|")
    path = Path(raw_path)
    allowed = {f"{item['path']}|{item['world_id']}": item for item in discover_local_savegames()}
    candidate = allowed.get(f"{path}|{world_id}")
    if not candidate:
        raise ValueError("Selected save is no longer available")
    groups = group_save_world_paths(path)
    files = groups.get(world_id)
    if not files:
        raise ValueError("Selected world files are no longer available")
    previous, imported, target_world_id = copy_save_world_files(files, path, instance_id, world_id)
    record = record_save_import(
        instance_id,
        f"{candidate['name']} as {target_world_id} ({imported} files)",
        candidate["path"],
        previous,
    )
    write_log(f"Imported discovered save {candidate['path']} world {world_id} as {target_world_id} into {get_instance(instance_id)['name']}")
    return record


def parse_content_disposition(header_text):
    for line in header_text.splitlines():
        if not line.lower().startswith("content-disposition:"):
            continue
        parts = line.split(":", 1)[1].split(";")
        values = {}
        for part in parts[1:]:
            key, _, value = part.strip().partition("=")
            values[key.lower()] = value.strip().strip('"')
        return values
    return {}


def parse_uploaded_save_folder(headers, stream):
    content_type = headers.get("Content-Type", "")
    marker = "boundary="
    if marker not in content_type:
        raise ValueError("Upload must be multipart/form-data")
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    length = int(headers.get("Content-Length", "0"))
    body = stream.read(length)
    delimiter = ("--" + boundary).encode("utf-8")
    files = []
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, sep, payload = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        header_text = header_blob.decode("utf-8", errors="replace")
        disposition = parse_content_disposition(header_text)
        if disposition.get("name") != "savefiles":
            continue
        filename = disposition.get("filename", "")
        if not filename:
            continue
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        files.append({"filename": filename.replace("\\", "/"), "data": payload})
    if not files:
        raise ValueError("Select the Enshrouded save folder before importing")
    return files


def normalize_uploaded_save_path(filename):
    parts = [part for part in Path(filename.replace("\\", "/")).parts if part not in {"", ".", "/"}]
    lower = [part.lower() for part in parts]
    if "remote" in lower:
        parts = parts[lower.index("remote") + 1:]
    elif "enshrouded" in lower:
        parts = parts[lower.index("enshrouded") + 1:]
    elif len(parts) > 1:
        parts = parts[1:]
    if not parts:
        raise ValueError("Uploaded save folder did not contain save files")
    return Path(*parts)


def group_uploaded_save_files(files):
    groups = {}
    ungrouped = []
    for item in files:
        relative = normalize_uploaded_save_path(item["filename"])
        world_id = save_world_id(relative.name)
        item = {**item, "relative": relative}
        if world_id:
            groups.setdefault(world_id, []).append(item)
        else:
            ungrouped.append(item)
    return groups, ungrouped


def import_uploaded_save_folder(headers, stream, instance_id):
    files = parse_uploaded_save_folder(headers, stream)
    groups, ungrouped = group_uploaded_save_files(files)
    if len(groups) > 1:
        choices = ", ".join(sorted(groups))
        raise ValueError(f"That folder contains multiple Enshrouded worlds ({choices}). Select one world from the list, then import it.")
    if not groups:
        raise ValueError("No Enshrouded world save files were found in that folder.")
    world_id, world_files = next(iter(groups.items()))
    stop_server_for_save_import(instance_id)
    backup = create_backup(push_ftp=False, instance_id=instance_id)
    save_dir = instance_save_path(instance_id)
    target_world_id = server_target_world_id(save_dir)
    if save_dir.exists():
        shutil.rmtree(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    imported = 0
    for item in world_files:
        relative = rename_world_relative(item["relative"], world_id, target_world_id)
        target = safe_child(save_dir, save_dir / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as fh:
            fh.write(item["data"])
        imported += 1
    record = record_save_import(instance_id, f"Uploaded world {world_id} as {target_world_id} ({imported} files)", "browser folder upload", backup.name)
    write_log(f"Imported uploaded save folder world {world_id} as {target_world_id} with {imported} file(s); previous save backed up as {backup.name}")
    return record


def parse_uploaded_file(headers, stream):
    content_type = headers.get("Content-Type", "")
    marker = "boundary="
    if marker not in content_type:
        raise ValueError("Upload must be multipart/form-data")
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    length = int(headers.get("Content-Length", "0"))
    body = stream.read(length)
    delimiter = ("--" + boundary).encode("utf-8")
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, sep, payload = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        header_text = header_blob.decode("utf-8", errors="replace")
        if 'name="savegame"' not in header_text:
            continue
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        return type("Upload", (), {"file": io.BytesIO(payload)})()
    raise ValueError("Missing savegame upload")


class Handler(SimpleHTTPRequestHandler):
    server_version = "EnshroudedManager/0.1"

    def log_request(self, code="-", size="-"):
        polling_routes = {"/api/status", "/api/jobs", "/api/log", "/api/backups", "/api/savegame/imports",
                          "/api/health", "/api/manager/update-status"}
        if self.command == "GET" and str(code) == "200" and urlparse(self.path).path in polling_routes:
            return
        super().log_request(code, size)

    def translate_path(self, path):
        route = urlparse(path).path
        if route == "/":
            return str(STATIC_DIR / "index.html")
        return str(STATIC_DIR / route.lstrip("/"))

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def is_local(self):
        host = self.client_address[0]
        return host in {"127.0.0.1", "::1"} or host.startswith("::ffff:127.")

    def authenticated(self):
        return self.current_user() is not None

    def current_user(self):
        if self.is_local() and config().get("allow_local_bypass", True):
            return primary_admin()
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "esm_session":
                return session_user(value)
        return None

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def require_auth(self):
        if self.current_user():
            return True
        self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
        return False

    def require_admin(self):
        if is_admin(self.current_user()):
            return True
        self.send_json({"error": "Admin permission required"}, HTTPStatus.FORBIDDEN)
        return False

    def require_perm(self, permission):
        if has_permission(self.current_user(), permission):
            return True
        self.send_json({"error": "Permission denied"}, HTTPStatus.FORBIDDEN)
        return False

    def do_GET(self):
        route = urlparse(self.path)
        if route.path == "/api/health":
            return self.send_json({"ready": True, "version": APP_VERSION, "boot_id": BOOT_ID, "pid": os.getpid()})
        if route.path.startswith("/api/"):
            if route.path not in {"/api/auth/state"} and not self.require_auth():
                return
            try:
                if route.path == "/api/manager/update-status":
                    if not self.require_admin():
                        return
                    return self.send_json({"operation": manager_update_status(), "version": APP_VERSION, "boot_id": BOOT_ID})
                if route.path == "/api/auth/state":
                    user = self.current_user()
                    return self.send_json({"authenticated": user is not None, "local": self.is_local(), "config": public_config(user) if user else {}})
                if route.path == "/api/status":
                    user = self.current_user()
                    qs = parse_qs(route.query)
                    requested_instance_id = qs.get("instance_id", [None])[0] or None
                    try:
                        inst = get_instance_for_user(user, requested_instance_id)
                        sup_status = supervisor(inst["id"]).status()
                        server_cfg = load_json(instance_config_path(inst["id"]), {})
                        logs = list_logs(inst["id"])
                    except FileNotFoundError:
                        inst = None
                        sup_status = {}
                        server_cfg = {}
                        logs = list_logs_no_instance()
                    return self.send_json({
                        "server": sup_status,
                        "manager": public_config(user),
                        "instances": [public_instance(item) for item in visible_instances_for_user(user)],
                        "selected_instance": public_instance(inst) if inst else None,
                        "server_config": server_cfg,
                        "logs": logs,
                        "install_jobs": visible_jobs_for_user(user),
                    })
                if route.path == "/api/log":
                    if not self.require_perm("logs"):
                        return
                    qs = parse_qs(route.query)
                    inst = get_instance_for_user(self.current_user(), qs.get("instance_id", [None])[0])
                    return self.send_json({"content": read_tail(qs.get("path", [""])[0], inst["id"])})
                if route.path == "/api/backups":
                    if not self.require_perm("backups"):
                        return
                    qs = parse_qs(route.query)
                    inst = get_instance_for_user(self.current_user(), qs.get("instance_id", [None])[0])
                    backup_dir = instance_backup_dir(inst["id"])
                    items = []
                    for path in backup_dir.glob("*.zip"):
                        stat = path.stat()
                        items.append({"name": path.name, "size": stat.st_size, "modified": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")})
                    return self.send_json({"backups": sorted(items, key=lambda x: x["modified"], reverse=True)})
                if route.path == "/api/savegame/discover":
                    if not self.require_perm("saves"):
                        return
                    return self.send_json({"saves": discover_local_savegames()})
                if route.path == "/api/savegame/imports":
                    if not self.require_perm("saves"):
                        return
                    qs = parse_qs(route.query)
                    inst = get_instance_for_user(self.current_user(), qs.get("instance_id", [None])[0])
                    return self.send_json({"imports": save_import_history(inst["id"])})
                if route.path == "/api/jobs":
                    qs = parse_qs(route.query)
                    return self.send_json({"job": get_job_for_user(qs.get("id", [""])[0], self.current_user())})
                return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            except PermissionError as exc:
                return self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
            except Exception as exc:
                write_log(f"API error on {route.path}: {exc}")
                return self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        return super().do_GET()

    def do_POST(self):
        global ACTIVE_OPERATIONS
        with OPERATIONS:
            if MAINTENANCE.is_set():
                return self.send_json({"error": "ESM-Z is updating. Wait for it to reconnect before making changes."}, 503)
            ACTIVE_OPERATIONS += 1
        try:
            return self.handle_post()
        finally:
            with OPERATIONS:
                ACTIVE_OPERATIONS -= 1
                OPERATIONS.notify_all()

    def handle_post(self):
        route = urlparse(self.path).path
        origin = self.headers.get("Origin")
        if route in {"/api/manager/install-update", "/api/manager/check-update"} and origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.send_json({"error": "Cross-origin updates are not permitted"}, 403)
        try:
            if route == "/api/auth/login":
                body = self.json_body()
                user = find_user(username=body.get("username", ""))
                ok = bool(user and verify_password(body.get("password", ""), user["password_salt"], user["password_hash"]))
                if not ok:
                    return self.send_json({"error": "Invalid username or password"}, HTTPStatus.UNAUTHORIZED)
                token = create_session(user)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"esm_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
                return
            if route == "/api/auth/logout":
                for part in self.headers.get("Cookie", "").split(";"):
                    name, _, value = part.strip().partition("=")
                    if name == "esm_session":
                        revoke_session(value)
                self.send_response(200)
                self.send_header("Set-Cookie", "esm_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")
                self.end_headers()
                return
            if route == "/api/invites/redeem":
                user = redeem_invite_code(self.json_body())
                token = create_session(user)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"esm_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "user": user}).encode("utf-8"))
                return
            if not self.require_auth():
                return
            if route == "/api/bootstrap/steamcmd":
                if not self.require_perm("setup"):
                    return
                with STEAMCMD_LOCK:
                    ensure_steamcmd()
                return self.send_json({"ok": True, "steamcmd": str(steamcmd_path())})
            if route == "/api/instances/import":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                check_server_creation_allowed(self.current_user())
                inst = add_instance(body.get("name") or Path(body["path"]).name, body["path"], select=True, owner_user_id=self.current_user().get("id", ""))
                return self.send_json({"ok": True, "instance": public_instance(inst)})
            if route == "/api/instances/install":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                job_id = start_install_job(body, self.current_user())
                return self.send_json({"ok": True, "job_id": job_id})
            if route == "/api/instances/retry-install":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                job_id = start_install_job({}, self.current_user(), retry_instance_id=body["instance_id"])
                return self.send_json({"ok": True, "job_id": job_id})
            if route == "/api/instances/select":
                inst = get_instance_for_user(self.current_user(), self.json_body()["instance_id"])
                if is_admin(self.current_user()):
                    select_instance(inst["id"])
                return self.send_json({"ok": True, "instance": public_instance(inst)})
            if route == "/api/instances/update":
                body = self.json_body()
                update_keys = set(body) - {"instance_id"}
                if update_keys <= {"scheduled_backup_enabled", "backup_interval_minutes"}:
                    needed_permission = "backups"
                elif update_keys <= {"scheduled_restarts"}:
                    needed_permission = "control"
                else:
                    needed_permission = "settings"
                if not self.require_perm(needed_permission):
                    return
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                inst = update_instance(inst["id"], body)
                return self.send_json({"ok": True, "instance": public_instance(inst)})
            if route == "/api/instances/remove":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body["instance_id"])
                remove_instance(inst["id"], delete_files=bool(body.get("delete_files", False)))
                return self.send_json({"ok": True})
            if route == "/api/instances/restore":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                if not any(item.get("id") == body["instance_id"] for item in removed_instances_for_user(self.current_user())):
                    raise FileNotFoundError("Unknown removed server")
                inst = restore_instance(body["instance_id"])
                return self.send_json({"ok": True, "instance": public_instance(inst)})
            if route == "/api/instances/delete-removed":
                if not self.require_perm("setup"):
                    return
                body = self.json_body()
                if not any(item.get("id") == body["instance_id"] for item in removed_instances_for_user(self.current_user())):
                    raise FileNotFoundError("Unknown removed server")
                delete_removed_instance_files(body["instance_id"])
                return self.send_json({"ok": True})
            if route == "/api/instances/clear-removed":
                if not self.require_admin():
                    return
                clear_removed_instances()
                return self.send_json({"ok": True})
            if route == "/api/server/start":
                if not self.require_perm("control"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                supervisor(inst["id"]).start(update_first=bool(body.get("update", False)))
                return self.send_json({"ok": True})
            if route == "/api/server/stop":
                if not self.require_perm("control"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                supervisor(inst["id"]).stop()
                return self.send_json({"ok": True})
            if route == "/api/server/restart":
                if not self.require_perm("control"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                supervisor(inst["id"]).restart(update_first=bool(body.get("update", False)))
                return self.send_json({"ok": True})
            if route == "/api/server/update":
                if not self.require_perm("control"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                run_update(inst["id"])
                return self.send_json({"ok": True})
            if route == "/api/config/server":
                if not self.require_perm("settings"):
                    return
                body = self.json_body()
                if "server_config" in body:
                    server_config = body["server_config"]
                    instance_id = get_instance_for_user(self.current_user(), body.get("instance_id"))["id"]
                    restart_if_running = bool(body.get("restart_if_running", False))
                    public_server = body.get("public_server")
                else:
                    server_config = body
                    instance_id = None
                    restart_if_running = False
                    public_server = None
                result = save_server_config(server_config, instance_id=instance_id, restart_if_running=restart_if_running, public_server=public_server)
                return self.send_json({"ok": True, "server_config": server_config, **result})
            if route == "/api/config/manager":
                if not self.require_admin():
                    return
                return self.send_json({"ok": True, "manager": update_config(self.json_body())})
            if route == "/api/manager/check-update":
                if not self.require_admin():
                    return
                body = self.json_body()
                return self.send_json({"ok": True, "manager_updates": public_manager_updates(
                    check_manager_updates(force=True, channel=body.get("channel")))})
            if route == "/api/manager/install-update":
                if not self.require_admin():
                    return
                channel = self.json_body().get("channel")
                if channel is not None and channel not in {"stable", "beta"}:
                    raise ValueError("Select the stable or beta update channel")
                if channel is not None and channel != manager_updates_config().get("channel"):
                    raise RuntimeError("The update channel changed. Check for updates again before installing.")
                return self.send_json({"ok": True, "operation": start_manager_update(expected_channel=channel)}, 202)
            if route == "/api/webhooks/test":
                if not self.require_perm("settings"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                return self.send_json({"ok": True, "result": test_webhook(inst["id"], body.get("webhook_id", ""))})
            if route == "/api/webhooks/save":
                if not self.require_perm("settings"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                webhook = save_instance_webhook(inst["id"], body.get("webhook", {}))
                return self.send_json({"ok": True, "instance": public_instance(get_instance(inst["id"])), "webhook_id": webhook["id"]})
            if route == "/api/webhooks/delete":
                if not self.require_perm("settings"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                delete_instance_webhook(inst["id"], body.get("webhook_id", ""))
                return self.send_json({"ok": True, "instance": public_instance(get_instance(inst["id"]))})
            if route == "/api/users/create":
                if not self.require_admin():
                    return
                return self.send_json({"ok": True, "user": create_manager_user(self.json_body())})
            if route == "/api/users/update":
                body = self.json_body()
                if not is_admin(self.current_user()):
                    get_visible_managed_user(self.current_user(), body["user_id"])
                    return self.send_json({"ok": True, "user": get_visible_managed_user(self.current_user(), body["user_id"])})
                return self.send_json({"ok": True, "user": update_manager_user(body["user_id"], body)})
            if route == "/api/users/reset-password":
                body = self.json_body()
                if not is_admin(self.current_user()):
                    get_visible_managed_user(self.current_user(), body["user_id"])
                return self.send_json({"ok": True, "user": reset_manager_user_password(body["user_id"], body.get("password", ""))})
            if route == "/api/users/delete":
                body = self.json_body()
                if not is_admin(self.current_user()):
                    get_visible_managed_user(self.current_user(), body["user_id"])
                delete_manager_user(body["user_id"])
                return self.send_json({"ok": True})
            if route == "/api/users/change-password":
                body = self.json_body()
                return self.send_json({"ok": True, "user": change_own_password(self.current_user(), body.get("old_password", ""), body.get("new_password", ""))})
            if route == "/api/invites/generate":
                return self.send_json({"ok": True, "invite": generate_invite_code(self.json_body(), self.current_user())})
            if route == "/api/invites/invalidate":
                return self.send_json({"ok": True, "invite": invalidate_invite_code(self.json_body()["invite_id"], self.current_user())})
            if route == "/api/invites/clear-expired":
                return self.send_json({"ok": True, "cleared": clear_expired_invite_codes(self.current_user())})
            if route == "/api/invites/clear-expired-one":
                clear_expired_invite_code(self.json_body()["invite_id"], self.current_user())
                return self.send_json({"ok": True})
            if route == "/api/invites/clear-used":
                return self.send_json({"ok": True, "cleared": clear_used_invite_codes(self.current_user())})
            if route == "/api/invites/clear-used-one":
                clear_used_invite_code(self.json_body()["invite_id"], self.current_user())
                return self.send_json({"ok": True})
            if route == "/api/invites/profiles":
                if not self.require_admin():
                    return
                return self.send_json({"ok": True, "invite_profiles": update_invite_profiles(self.json_body())})
            if route == "/api/jobs/dismiss":
                dismiss_job_for_user(self.json_body()["job_id"], self.current_user())
                return self.send_json({"ok": True})
            if route == "/api/backup/create":
                if not self.require_perm("backups"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                archive = create_backup(push_ftp=bool(body.get("ftp", False)), instance_id=inst["id"])
                return self.send_json({"ok": True, "backup": archive.name})
            if route == "/api/savegame/import":
                if not self.require_perm("saves"):
                    return
                qs = parse_qs(urlparse(self.path).query)
                inst = get_instance_for_user(self.current_user(), qs.get("instance_id", [None])[0])
                item = parse_uploaded_file(self.headers, self.rfile)
                previous = import_savegame(item, inst["id"])
                return self.send_json({"ok": True, "previous_backup": previous})
            if route == "/api/savegame/import-local":
                if not self.require_perm("saves"):
                    return
                body = self.json_body()
                inst = get_instance_for_user(self.current_user(), body.get("instance_id"))
                record = import_discovered_savegame(body.get("save_id", ""), inst["id"])
                return self.send_json({"ok": True, "import": record})
            if route == "/api/savegame/import-folder":
                if not self.require_perm("saves"):
                    return
                qs = parse_qs(urlparse(self.path).query)
                inst = get_instance_for_user(self.current_user(), qs.get("instance_id", [None])[0])
                record = import_uploaded_save_folder(self.headers, self.rfile, inst["id"])
                return self.send_json({"ok": True, "import": record})
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            write_log(f"API error on {route}: {exc}")
            return self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def monitor_loop():
    global ACTIVE_OPERATIONS
    while True:
        if MAINTENANCE.is_set():
            time.sleep(0.25)
            continue
        with OPERATIONS:
            if MAINTENANCE.is_set():
                continue
            ACTIVE_OPERATIONS += 1
        try:
            check_manager_updates(force=False)
            for inst in instances():
                supervisor(inst["id"]).monitor_once()
                scheduled_restart_check(inst["id"])
                scheduled_backup_check(inst["id"])
        except Exception as exc:
            write_log(f"Monitor error: {exc}")
        finally:
            with OPERATIONS:
                ACTIVE_OPERATIONS -= 1
        time.sleep(max(2, int(config().get("restart_check_interval_seconds", 5))))


def scheduled_restart_check(instance_id):
    inst = get_instance(instance_id)
    schedules = inst.get("scheduled_restarts", [])
    now = dt.datetime.now()
    key = now.strftime("%Y-%m-%d %H:%M")
    hhmm = now.strftime("%H:%M")
    sup = supervisor(instance_id)
    if hhmm in schedules and sup.last_scheduled_key != key:
        sup.last_scheduled_key = key
        write_log(f"Scheduled restart triggered for {inst['name']} at {hhmm}")
        sup.restart(update_first=inst.get("update_before_start", False))


def main():
    global HTTP_SERVER
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cfg = config()
    for inst in cfg.get("instances", []):
        if inst.get("start_on_manager_launch", False) and not os.environ.get("ESM_UPDATE_RESTART"):
            supervisor(inst["id"]).intentional_stop = False
            update_instance_metadata(inst["id"], desired_running=True)
    host = cfg.get("bind_host", "0.0.0.0")
    port = int(cfg.get("port", 8080))
    write_log(f"ESM-Z UI listening on http://{host}:{port}")
    HTTP_SERVER = ThreadingHTTPServer((host, port), Handler)
    if os.environ.get("ESM_UPDATE_RESTART"):
        MAINTENANCE.set()

        def finish_handoff():
            while manager_update_status().get("phase") in update_runtime.ACTIVE_PHASES:
                time.sleep(0.25)
            result = manager_update_status()
            with CONFIG_LOCK:
                cfg = config()
                updates = cfg.setdefault("manager_updates", default_manager_updates())
                if result.get("phase") == "complete":
                    updates.update(last_installed_at=now_iso(), last_error="", restart_required=False,
                                   installed_pending_version="", update_available=False)
                save_json(MANAGER_CONFIG, cfg)
            MAINTENANCE.clear()
            event = "manager.update.installed" if result.get("phase") == "complete" else "manager.update.failed"
            notify_webhook_event(event, message=result.get("message", "Manager restarted"))

        threading.Thread(target=finish_handoff, daemon=True).start()
    threading.Thread(target=monitor_loop, daemon=True).start()
    try:
        HTTP_SERVER.serve_forever()
    finally:
        HTTP_SERVER.server_close()


if __name__ == "__main__":
    main()
