# ESM-Z Linux Host Support Analysis

**ESM-Z — Enshrouded Server Manager by Zat**

Analysis date: 2026-09-08  
Repository baseline: v0.9.0  
Decision status: architecture recommendation only; Linux runtime support is not implemented

## A. Executive Summary

Linux support is viable, but it is a large feature rather than a small packaging change. Keen Games currently documents the Enshrouded dedicated server as Windows-only, so an initial Linux host must download the Windows server depot and run `enshrouded_server.exe` through a compatibility runtime. The recommended first runtime is Wine/Wine64, with one Wine prefix per ESM-Z server instance.

ESM-Z should remain one codebase. The backend, web UI, permissions, invites, JSON configuration, scheduling, backups, save upload, FTP, webhooks, and most filesystem operations are already platform-neutral. Windows-specific behavior is concentrated enough to extract behind a host adapter, but process launch, process identity, shutdown, recovery, SteamCMD installation, save discovery, packaging, and self-update selection all need explicit host implementations.

The safest implementation sequence is:

1. Characterize the current Windows behavior with tests.
2. Extract that behavior unchanged into a `WindowsHost` adapter.
3. Prototype Linux SteamCMD and Wine on Ubuntu Server 24.04 LTS.
4. Add one prefix and one independently managed process unit per server.
5. Prove manager restart/update does not stop game servers.
6. Package a Python virtualenv installer and systemd integration.

Direct Wine is recommended over Proton for the first implementation because it has fewer Steam-client and runtime-container assumptions. Docker should follow native Linux-host support, not be part of the first Linux release.

## B. Current Windows-Only Dependencies

### Backend assumptions in `enshrouded_manager/manager.py`

| Area | Current code | Linux impact |
| --- | --- | --- |
| Server executable | `SERVER_EXE`, `instance_exe_path()`, `public_instance()`, `add_instance()`, and `safe_delete_server_directory()` hardcode `enshrouded_server.exe` | Linux still needs this Windows executable, but it must be launched through Wine and installation checks must be runtime-aware. |
| SteamCMD binary | `STEAMCMD` and `steamcmd_path()` hardcode `Steamcmd/steamcmd.exe` | Linux uses `steamcmd.sh` or a distro-provided SteamCMD executable. |
| SteamCMD download | `STEAMCMD_URL` points to `steamcmd.zip`; `ensure_steamcmd()` extracts a ZIP and expects `steamcmd.exe` | Linux uses the Linux SteamCMD tarball/package and may require 32-bit runtime libraries. |
| Steam depot selection | `run_update()` does not set `@sSteamCmdForcePlatformType` | Linux SteamCMD must explicitly request the Windows depot. |
| Launch flags | `ServerSupervisor.start()` uses `CREATE_NEW_PROCESS_GROUP`, `DETACHED_PROCESS`, and optionally `CREATE_BREAKAWAY_FROM_JOB` | These are Windows `CreateProcess` flags. Linux needs a new session/process group or independent service unit. |
| PID inspection | `process_is_running()` uses `ctypes.windll.kernel32.OpenProcess()` and `GetExitCodeProcess()` on Windows | Linux can test a PID, but PID existence alone does not prove it is the same ESM-Z instance. |
| Tree termination | `stop_process_tree()` runs `taskkill /PID /T` and then `/F` | Wine can create several Unix processes. Linux needs process-group and Wine-prefix-aware shutdown. |
| Exit-code display | `signed_exit_code()` interprets unsigned Windows exit values | POSIX signal return codes have different meaning and should be formatted by the host adapter. |
| Persisted process state | `default_instance()` stores only `pid`, desired state, and timestamps | A persisted PID can be reused. Linux needs PID/PGID, start fingerprint, runtime, and prefix identity. Windows would also benefit later, but its behavior must first remain unchanged. |
| Save discovery | `known_save_roots()` uses `USERPROFILE`, `LOCALAPPDATA`, `APPDATA`, `C:/Users`, `Program Files`, and `Saved Games` | Host-local discovery needs a Linux implementation. Browser folder upload remains cross-platform and is the right path for remote users. |
| HTTPS error text | `urlopen_https()` tells users to update Windows/Python certificates | The diagnostic must become host-neutral before Linux release. The unverified TLS retry is a separate security risk. |
| Self-update asset | `find_release_asset()` selects a Python-required ZIP without an OS/architecture manifest | Linux must never install a Windows package. Asset selection needs host, architecture, package type, and integrity metadata. |
| Self-update replacement | `install_manager_update()` directly replaces files under `APP_DIR` | This assumes the running account can mutate the installation and that ZIP layout is identical. Linux package ownership and service restart need a staged installer. |
| Frozen layout | `ROOT` and `STATIC_DIR` use PyInstaller-specific `sys.frozen`/`_MEIPASS` behavior | A Linux standalone build would need its own tested artifact and data-root rules. |

`ctypes` is imported unconditionally, although the `windll` calls are guarded by `os.name == "nt"`. There is no registry access in the repository.

### Windows launch and packaging files

- `enshrouded_manager/Launch Manager.bat` is a legacy Windows launcher.
- `enshrouded_manager/Launch ESM-Z.bat` is the new branded Windows launcher.
- `enshrouded_manager/build_exe.ps1` is PowerShell/PyInstaller tooling and uses the Windows `--add-data` separator.
- `enshrouded_manager/build_python_required_release.ps1` builds a Windows ZIP with a batch launcher.
- `enshrouded_manager/build_portable_release.ps1` copies a Windows Python runtime. It is retained as tooling, but portable-Python packages are not currently part of regular iterations.
- `enshrouded_manager/build_zip.ps1` packages existing Windows SteamCMD and game-server directories.
- `README.md`, `docs/INSTALL.md`, and the packaged READMEs currently describe Windows installation and Windows Firewall.

There is no Windows service installer and no service abstraction today. ESM-Z is launched interactively through a batch file. Firewall rules are documented but not changed in code.

## C. Already-Portable Components

The following are substantially platform-neutral and should stay in shared code:

- `ThreadingHTTPServer`, request routing, static-file delivery, sessions, and role checks.
- User accounts, password hashing, permissions, server assignment, invite codes, and invite profiles.
- JSON manager configuration and Enshrouded configuration parsing/editing.
- Instance ownership, removed-instance history, install-job records, and UI status polling.
- Scheduled restart and backup decision logic.
- ZIP save upload, browser folder upload, world-file grouping, import history, and backup creation.
- FTP transfers through `ftplib`, subject to credentials and FTPS/SFTP improvements discussed below.
- Webhook configuration, event routing, Discord/generic JSON payloads, and delivery.
- GitHub release API parsing and semantic version comparison, after asset selection is host-aware.
- UDP port availability checks through `socket`.
- `pathlib`, `shutil`, JSON, ZIP, threading, and most timestamp/logging code.
- The HTML/CSS/JavaScript UI, except for host-specific labels, path examples, and diagnostics.

## D. Recommended Linux Architecture

### Keep one codebase

A separate Linux fork is not justified. It would duplicate the rapidly changing UI, permissions, instance model, backups, saves, webhooks, and updater logic. ESM-Z should use one shared application layer with a narrow host-runtime boundary.

Do not name the new package `platform`, because that can shadow Python's standard-library `platform` module. A clearer structure is:

```text
enshrouded_manager/
    manager.py
    host/
        __init__.py
        base.py
        models.py
        windows.py
        linux_wine.py
```

`host/base.py` should define a small `HostRuntime` protocol or abstract base class. `host/models.py` should contain immutable command/process records. `host/windows.py` should first receive the current Windows behavior with no intended semantic changes. `host/linux_wine.py` should be added only after Windows characterization tests pass.

### Proposed interface

```python
class HostRuntime(Protocol):
    def capabilities(self) -> HostCapabilities: ...
    def prepare_environment(self) -> PreparationResult: ...
    def server_executable(self, instance: dict) -> Path: ...
    def is_server_installed(self, instance: dict) -> bool: ...
    def install_steamcmd(self, progress=None) -> Path: ...
    def build_server_update(self, instance: dict, validate: bool) -> CommandSpec: ...
    def launch_server(self, instance: dict) -> ProcessHandle: ...
    def inspect_server(self, handle: ProcessHandle) -> ProcessState: ...
    def recover_server(self, instance: dict) -> ProcessHandle | None: ...
    def stop_server(self, handle: ProcessHandle, timeout: int) -> StopResult: ...
    def local_save_roots(self) -> list[Path]: ...
    def release_asset_matches(self, asset_name: str) -> bool: ...
    def format_exit(self, return_code: int | None) -> ExitDescription: ...
```

`ProcessHandle` should be persisted as structured metadata rather than a bare PID. Suggested fields are `runtime`, `pid`, `process_group_id`, `unit_name`, `started_at`, `process_start_token`, `command_fingerprint`, and `wine_prefix`. Not every host must populate every field.

### Existing code to move behind the adapter

| Current symbol | Destination responsibility |
| --- | --- |
| `process_is_running()` | `inspect_server()` and host-specific process identity validation |
| `stop_process_tree()` | `stop_server()` |
| `instance_exe_path()` | `server_executable()` |
| `steamcmd_path()` / `ensure_steamcmd()` | `install_steamcmd()` and host tool discovery |
| `run_update()` command construction | `build_server_update()`; shared code may execute/report the result |
| Launch block in `ServerSupervisor.start()` | `launch_server()` |
| OS branches in `ServerSupervisor.stop()` | `stop_server()` |
| Reattachment logic in `ServerSupervisor.status()` / `monitor_once()` | `recover_server()` / `inspect_server()` |
| `signed_exit_code()` | `format_exit()` |
| `known_save_roots()` | `local_save_roots()` |
| `.exe` checks in `public_instance()`, `add_instance()`, deletion safeguards | `is_server_installed()` and host-provided installation markers |
| `find_release_asset()` | Host-aware release artifact selection |

`ServerSupervisor` should remain the shared policy owner for desired state, update-before-start, crash restart, schedules, status reporting, and webhooks. It should stop knowing how a host creates or destroys processes.

## E. Wine and Enshrouded Execution Design

Keen's current documentation says the dedicated server supports Windows only and that first launch creates `enshrouded_server.json`. That makes Wine a compatibility path, not vendor-supported native Linux execution. A prototype on real hardware is mandatory before making a reliability claim. See [Keen's dedicated server installation guide](https://enshrouded.zendesk.com/hc/en-us/articles/16051370691485-Dedicated-Server-Installation-on-Steam) and [configuration guide](https://enshrouded.zendesk.com/hc/en-us/articles/16055441447709-Dedicated-Server-Configuration).

### Runtime comparison

| Option | Reliability | Complexity and maintenance | Process/network implications | Recommendation |
| --- | --- | --- | --- | --- |
| Wine/Wine64 | Plausible and commonly suited to headless Windows server executables, but not officially supported by Keen and not yet validated here | Moderate. Distro Wine versions and prefixes must be managed | Uses host networking; ESM-Z must control Wine process trees and prefixes | First implementation target |
| Proton | May fix title-specific compatibility issues because it carries Valve patches and runtime components | Higher. Proton is designed for Steam Play and the Steam client, with compatibility data and runtime-container conventions | More environment variables, runtime paths, and lifecycle layers | Advanced fallback after Wine support |
| Docker with Wine | Reproducible once working | High initial complexity. Volume, UID/GID, networking, upgrades, and nested process supervision all become product concerns | Host networking simplifies UDP but reduces isolation; bridge mode needs explicit ports | Separate later distribution |
| Native Linux binary | Best eventual runtime if Keen releases one | Low after release, but unavailable today | Normal POSIX process lifecycle | Add later as another host runtime |
| VM | Strong isolation and Windows fidelity | Very high resource and operational cost per host/instance | Separate guest networking and update management | Not an ESM-Z feature; deployment workaround only |

Valve describes Proton as a Steam-client compatibility tool based on Wine, which is why it is not the lowest-complexity headless default: [Valve Proton README](https://github.com/ValveSoftware/Proton).

### Wine prefix strategy

Use one Wine prefix per server instance, stored outside the game installation, for example:

```text
/var/lib/esm-z/wineprefixes/<instance-id>/
/srv/esm-z/servers/<directory>/
```

Do not put the prefix inside the SteamCMD install directory because validation or removal workflows must not accidentally treat runtime state as game content.

| Prefix layout | Advantages | Problems | Decision |
| --- | --- | --- | --- |
| One shared prefix for all servers | Lowest disk use and fastest initial setup | Shared registry, wineserver, kernel objects, and failure domain; prefix cleanup can stop every instance | Reject |
| One prefix for the ESM-Z install | Simple bookkeeping | Same cross-instance coupling as one shared prefix | Reject |
| One prefix per server | Independent wineserver, registry, troubleshooting, and cleanup | More disk use and initialization time | Recommend |

Wine documents that processes under one prefix share registry, shared memory, and kernel objects, while different `WINEPREFIX` values create independent Wine sessions. It also documents that `wineserver -k` targets the prefix selected by `WINEPREFIX`: [Debian wineserver manual](https://manpages.debian.org/bookworm/wine/wineserver-stable.1.en.html).

The launch environment should minimally set:

```text
WINEPREFIX=/var/lib/esm-z/wineprefixes/<instance-id>
WINEDEBUG=-all
```

The executable should be detected with an absolute configured or discovered `wine64`/`wine` path. Whether `DISPLAY` or an Xvfb service is needed must be established during the prototype; ESM-Z should not silently install a graphical stack unless the server actually requires it.

## F. SteamCMD Design

Linux SteamCMD can request Windows content by setting `@sSteamCmdForcePlatformType windows`. The ESM-Z Linux command should be built as an argument sequence, not a shell string:

```text
/opt/esm-z/steamcmd/steamcmd.sh
+@ShutdownOnFailedCommand 1
+@NoPromptForPassword 1
+force_install_dir /srv/esm-z/servers/<directory>
+login anonymous
+@sSteamCmdForcePlatformType windows
+app_update 2278520 validate
+quit
```

In one line, the intended invocation is:

```bash
/opt/esm-z/steamcmd/steamcmd.sh +@ShutdownOnFailedCommand 1 +@NoPromptForPassword 1 +force_install_dir /srv/esm-z/servers/example +login anonymous +@sSteamCmdForcePlatformType windows +app_update 2278520 validate +quit
```

Valve issue examples confirm the `@sSteamCmdForcePlatformType` command and show that `force_install_dir` should precede login/update: [platform override example](https://github.com/ValveSoftware/steam-for-linux/issues/9076) and [force-install ordering report](https://github.com/ValveSoftware/steam-for-linux/issues/8298). The exact Enshrouded depot result still needs an integration test because Keen does not document Linux SteamCMD as a supported installation path.

Recommended behavior:

- Preserve the existing Windows command and Windows ZIP installer exactly in `WindowsHost` initially.
- On Linux, detect an admin-configured SteamCMD path first, then an ESM-Z-managed copy, then `steamcmd`/`steamcmd.sh` on `PATH`.
- Download the official Linux SteamCMD tarball only when no usable executable is found.
- Use `+force_install_dir` before login.
- Add `+@sSteamCmdForcePlatformType windows` only for the Linux-Wine runtime.
- Keep `validate` for initial install and explicit repair. For backward compatibility, the first Linux implementation may also use it for current update actions, then separate lightweight update and repair actions later.
- Parse and retain SteamCMD output for install progress and diagnostics.
- Stop the target server before writing an update. The current generic update action can run SteamCMD against a live installation and should be coordinated in a later cross-platform hardening change.

SteamCMD updates itself. ESM-Z should report that activity but should not treat SteamCMD's own bootstrap update as a manager update.

## G. Process-Management Design

### Current Windows lifecycle

1. `ServerSupervisor.start()` checks its in-memory `Popen`, then the stored PID.
2. It optionally runs SteamCMD and validates the UDP query port.
3. It launches `enshrouded_server.exe` detached with a new process group and stores the PID.
4. It waits two seconds for an immediate exit.
5. `monitor_once()` polls the `Popen`; after a manager restart it checks only whether the stored PID exists.
6. Unexpected exit plus `desired_running` and `auto_restart` triggers a new start.
7. A manager stop request clears `desired_running` before using `taskkill /T`, then `/F` after timeout.
8. ESM-Z itself has no shutdown hook that stops game servers, so detached servers are intended to remain alive.

The current Windows recovery check has a PID-reuse risk because it does not verify process image or creation time. This analysis does not change that behavior; characterization tests should lock in current semantics before improving identity in a later version.

### Linux plus Wine lifecycle

Killing only the first Wine launcher PID is unsafe and potentially incomplete. The Windows process can involve a launcher, preloader, wineserver, and other Unix children. A child can outlive the original parent, and `wineserver` is shared by every process in a prefix.

For a development prototype, launch the direct Wine command with `start_new_session=True`, persist the process group ID, and send signals with `os.killpg()`. Python documents `start_new_session` as the thread-safe `setsid()` mechanism and recommends it over `preexec_fn`: [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html).

Prototype stop sequence:

1. Persist `desired_running=False` before signaling.
2. Validate the process start token, command fingerprint, and prefix path.
3. Send `SIGTERM` to the isolated process group.
4. Wait the configured graceful timeout.
5. Run `wineserver -k` with only that instance's `WINEPREFIX` if Wine processes remain.
6. Wait for prefix shutdown.
7. Send `SIGKILL` to the process group only as a final fallback.
8. Verify that no processes belonging to the instance prefix remain before reporting stopped.

Because the game has no repository-documented remote console or native graceful-shutdown protocol, `SIGTERM` should be considered best effort until save-flush behavior is proven. Automated backup-before-forced-kill is worth evaluating after the lifecycle prototype.

### Production persistence and systemd

`start_new_session=True` does not by itself guarantee survival when ESM-Z runs in a systemd service. systemd normally stops all processes in a service control group. `KillMode=process` can leave children alive but is explicitly not recommended by systemd because it lets processes escape lifecycle management: [systemd.kill manual](https://manpages.debian.org/unstable/systemd/systemd.kill.5.en.html).

The production design should put each game server in its own unit/scope, separate from `esm-z.service`:

```text
esm-z.service
esm-z-instance@<instance-id>.service
```

The manager service and instance services should run as the same unprivileged `esm-z` account. The installer may perform privileged setup once. Runtime control should use narrowly scoped systemd permissions or a persistent user service manager; ESM-Z must not receive unrestricted `sudo` or Docker-socket access.

Each instance unit should invoke a small ESM-Z-owned runner that:

- Sets the instance `WINEPREFIX`.
- Starts Wine in the foreground.
- Records process identity and exit status atomically.
- Forwards stop requests through the defined timeout/escalation sequence.
- Produces per-instance runtime diagnostics.

Separate units let game servers survive an ESM-Z web-manager restart/update while remaining visible and manageable. On restart, ESM-Z should query unit state and verify process identity, not trust a historical PID. A non-systemd `setsid` fallback can exist for development or unsupported distributions, but should be labeled experimental.

## H. Linux Distribution, Packaging, and Deployment

### Initial distribution target

Target **Ubuntu Server 24.04 LTS x86_64 first**. Add **Debian 12/13 x86_64** after the same Wine/SteamCMD/systemd matrix passes. This is narrow enough to support well and aligns with Valve's Linux client focus on Ubuntu plus required 32-bit runtime support: [Valve Steam for Linux requirements](https://github.com/ValveSoftware/steam-for-linux).

Later distribution work:

| Environment | Additional work |
| --- | --- |
| Fedora | DNF package mapping, SELinux labels/policy, firewalld instructions, Wine version testing |
| Arch | Rolling Wine/Python/systemd regression matrix and a maintained PKGBUILD/AUR strategy |
| Unraid | Container-first packaging, persistent volume conventions, template, host networking guidance |
| TrueNAS | Supported Apps/container model; avoid assuming mutable host packages |
| Proxmox | Document a supported Ubuntu/Debian VM or LXC guest; test Wine and systemd constraints in LXC |
| Non-systemd distros | Alternative supervisor integration and explicitly reduced persistence guarantees |
| ARM hosts | Out of initial scope; Enshrouded is x86-64 and emulation would add a separate compatibility layer |

### Packaging comparison

| Package | Usability | Maintenance | Initial decision |
| --- | --- | --- | --- |
| Virtualenv + `esm-z.sh` installer | Transparent, easy to debug, works with current Python code | Moderate dependency setup | Implement first |
| systemd units | Correct boot startup and independent server lifecycle | Requires careful service-user and control design | Include in first production Linux package |
| Standalone binary | Simple-looking artifact | PyInstaller/Wine/tool discovery and libc compatibility require per-distro testing | Later |
| Docker image | Familiar for NAS/homelab users | Volumes, ports, UID/GID, self-update, and process supervision add complexity | After native Linux support |
| DEB/RPM | Best OS integration | Signing, repositories, upgrades, and distro matrix add ongoing work | Later |

Recommended first package:

```text
ESM-Z-Linux-PythonRequired-vX.Y.Z.tar.gz
install-esm-z.sh
esm-z.sh
esm-z.service
esm-z-instance@.service
```

The installer can use `sudo` to install prerequisites, create the service account/directories, and register units. Normal ESM-Z and game-server processes must run without root.

## I. Configuration Changes

### Automatic and hidden

- `host_platform`: detected from the OS; persisted only for diagnostics/migration.
- `host_architecture`: detected; used for package selection.
- Runtime process metadata: PID, PGID/unit, start token, command fingerprint, and prefix.
- Managed Wine prefix root: derived from ESM-Z's data root and instance ID.
- Managed SteamCMD location: derived from installation/data roots.
- Release artifact platform/package type: generated and validated, not selected by normal users.

### Admin advanced settings

- Wine executable path, with `wine64`/`wine` autodetection.
- wineserver executable path.
- SteamCMD executable path and managed/unmanaged toggle.
- Linux server root, backup root, and Wine-prefix root.
- Graceful-stop and force-stop timeouts.
- Optional headless display command only if the prototype proves it necessary.
- Service integration status and diagnostic commands.

### Per-instance advanced settings

- Runtime provider (`windows-native`, `linux-wine`, future `linux-native`, optional future `proton`).
- Server executable override for imported installations.
- Wine prefix override only for expert/import migration use.
- Unit name/process identity shown read-only in diagnostics.

Normal users should continue seeing instance name, directory, query port, config, saves, and controls. Wine, SteamCMD paths, prefixes, and systemd concepts should be automatic and hidden unless an admin opens advanced diagnostics.

Existing keys such as `path`, `pid`, `desired_running`, server IDs, data directories, APIs, and JSON files must remain readable. New process metadata should be additive and migration-safe.

## J. Security Considerations

1. Run ESM-Z and Wine as a dedicated unprivileged `esm-z` service account. Never run the web application as root in normal operation.
2. Use installation-time privilege only for account, package, directory, firewall, and systemd setup.
3. Own server, prefix, backup, and config directories by the service account. Suggested defaults are `0750` for directories and `0600` for files containing passwords/tokens.
4. Keep each Wine prefix private. A prefix contains a simulated user profile and registry and should be treated as sensitive mutable state.
5. Bind ESM-Z to localhost by default. For remote access, prefer a VPN or a TLS reverse proxy and explicit firewall rules.
6. Disable `allow_local_bypass` when a same-host reverse proxy is used. Otherwise every proxied request can appear to originate from localhost and bypass login. This is a critical deployment warning for Windows and Linux.
7. Do not expose the Docker socket to ESM-Z. It commonly grants host-equivalent control.
8. Avoid unrestricted `sudo systemctl`. Use ESM-Z-owned user units or narrowly scoped policy for only `esm-z-instance@...` units.
9. Replace the current automatic unverified HTTPS retry before production Linux self-update. Downloading executable updates without certificate verification is unsafe.
10. Add release checksums/signatures and atomic rollback before unattended self-update is enabled on Linux.
11. FTP sends credentials/data without transport security. Add FTPS or SFTP as a later security feature and keep credentials out of logs/API responses.
12. Revisit symlink and time-of-check/time-of-use behavior in path deletion/import operations before allowing broad Linux existing-install paths.

Ubuntu's server security guidance emphasizes least privilege, updates, SSH hardening, and firewalling: [Ubuntu Server security suggestions](https://ubuntu.com/server/docs/explanation/security/security_suggestions/).

## K. Update Behavior

| Component | Recommended owner | Linux behavior |
| --- | --- | --- |
| ESM-Z | ESM-Z updater or package manager | Download host-specific signed artifact to staging, verify, stop only `esm-z.service`, replace atomically, restart manager, rollback on failed health check |
| SteamCMD | SteamCMD bootstrap | Let it self-update when invoked; report progress/errors |
| Enshrouded server | ESM-Z through SteamCMD | Stop only the selected instance, update Windows depot, validate when requested, restart if previously desired-running |
| Wine runtime | OS package manager | Detect/report version; do not silently upgrade Wine from the web app |

Manager updates must not stop `esm-z-instance@...` units. After ESM-Z restarts, it should enumerate configured instances, query their independent unit/process state, validate identity, and reconstruct in-memory supervisors.

Linux release assets should include platform and architecture, for example `ESM-Z-Linux-x86_64-PythonRequired-vX.Y.Z.tar.gz`. Windows assets should remain `ESM-Z-Windows-PythonRequired-vX.Y.Z.zip` after a compatibility transition. The release manifest should contain version, platform, architecture, package kind, SHA-256, and entrypoint. Current legacy Windows package names must remain accepted until deployed versions have crossed the transition.

## L. Testing Plan

### Unit and contract tests

- Host factory selects the correct adapter and rejects unsupported systems.
- A shared host contract suite runs against a fake host plus Windows/Linux adapters where possible.
- SteamCMD command construction verifies argument order, absolute install path, platform override, and validation mode.
- Process handles serialize/migrate without losing existing `pid`/desired state.
- Release asset selection cannot cross operating systems or architectures.
- Config migration preserves every existing Windows instance and user setting.
- Local save roots and deletion markers are host-specific and path-contained.

### Windows regression matrix

| Scenario | Required result |
| --- | --- |
| Existing v0.9.x configuration | Loads without migration loss; all instances/users/webhooks remain visible |
| Fresh manager install | Localhost UI, initial admin flow, first instance setup work as today |
| Existing server import | `.exe` and JSON detection unchanged |
| Fresh server install | Windows SteamCMD ZIP, first start/config creation, and install status unchanged |
| Server start/stop/restart | Current detached launch and `taskkill` behavior unchanged |
| Crash recovery | Desired-running instance restarts; intentional stop does not restart |
| Multiple servers | Independent ports, controls, configs, webhooks, backups, and owners |
| Manager restart/update | Running game servers remain running and are rediscovered |
| Scheduled restart/update-before-start | Timing and checkbox persistence unchanged |
| Save import/backups/FTP | Existing workflows and data layout unchanged |
| Release update | ESM-Z and legacy Windows package names both resolve during transition |

### Linux integration matrix

Run first on Ubuntu Server 24.04 LTS x86_64, then repeat supported rows on Debian:

| Scenario | Required evidence |
| --- | --- |
| Fresh ESM-Z install | Non-root service, correct ownership, localhost UI, clean health check |
| Existing server import | Windows depot detected without modifying user files unexpectedly |
| SteamCMD install/detection | Managed and PATH/configured variants work; output is visible |
| Wine detection/prefix setup | Version reported; one private prefix per instance |
| Server installation | Windows depot downloaded with ForcePlatformType and validated |
| First launch | Config file created; no interactive Wine dialog blocks setup |
| Start | Correct PID/unit/prefix identity and UDP bind |
| Graceful stop | Save remains healthy; no instance processes remain |
| Forced stop | Timeout escalation affects only selected prefix/instance |
| Crash recovery | Crash event and restart occur once; no duplicate server processes |
| Scheduled restart | Selected instance only; update-before-start obeyed |
| Backups and FTP | Permissions, local archive, remote transfer, retention |
| Multiple instances | Unique ports/prefixes/units; one stop or wineserver kill cannot affect another |
| Manager restart | Every running game server stays up and is reattached accurately |
| Manager update | Game units stay up; manager rollback works on failed health check |
| Host reboot | Desired instances return according to configured policy |
| LAN/remote access | Bind behavior, authentication, firewall, reverse proxy with local bypass disabled |
| User roles/invite codes | Same visibility and permissions as Windows |
| Config editing/bans | Live warning/restart and file ownership are correct |
| Save import | Browser-folder and ZIP imports select one world and start the imported world |
| Wine update | Existing prefixes continue or produce a clear compatibility warning/rollback path |

Long-running soak tests should cover at least 72 hours, repeated scheduled restarts, manager restarts, a forced server crash, and simultaneous multi-instance load.

## M. Risk Assessment

| Severity | Risk | Mitigation |
| --- | --- | --- |
| Critical | Manager systemd stop/update kills game servers in the same cgroup | Separate per-instance units and prove manager-update persistence |
| Critical | Wine launcher PID exits or changes while Windows server children remain | Prefix-aware unit/runner plus process fingerprinting; never trust PID alone |
| Critical | Linux updater installs a Windows/incorrect artifact or unverified code | Typed release manifest, signatures/checksums, TLS verification, atomic rollback |
| High | Platform extraction regresses working Windows launch/stop/update | Characterization tests first; move code mechanically into `WindowsHost` |
| High | One prefix/wineserver operation stops all instances | One Wine prefix per instance and isolation tests |
| High | Current Enshrouded build is unstable or nonfunctional under selected Wine | Hardware prototype, pinned tested runtime, explicit support matrix |
| High | PID reuse makes ESM-Z control an unrelated process | Persist creation token, command fingerprint, prefix/unit identity |
| High | Root-run web manager turns a web flaw into full host compromise | Dedicated non-root account and narrow service controls |
| High | Reverse proxy plus localhost bypass grants unauthenticated remote access | Force bypass off in proxy mode and document/migrate securely |
| Medium | Wine or SteamCMD needs 32-bit libraries/headless display not present | Prerequisite probe and distro-specific installer diagnostics |
| Medium | Wine update breaks existing prefixes | OS-managed version, compatibility test, version reporting, backup prefixes before migration |
| Medium | Linux permissions break import, backup, delete, or self-update | Explicit ownership model and integration tests across all storage roots |
| Medium | Docker creates a second lifecycle/update model and support burden | Defer until native Linux adapter is stable |
| Medium | FTP exposes credentials | Add FTPS/SFTP; restrict config/log exposure |

## N. Scope and Phased Roadmap

Overall scope: **large**. A functional prototype is much smaller than a supportable release. A realistic engineering range is roughly 2-3 weeks for a focused prototype and 6-10 weeks for implementation, packaging, migration, security hardening, and multi-host testing, depending on access to Linux test hardware and Wine behavior.

### Phase 0: completed by this analysis

- Inventory Windows assumptions and portable components.
- Select one-codebase host-adapter architecture.
- Select Wine/Wine64, per-instance prefixes, Ubuntu 24.04 LTS first.
- Rename user-facing application branding to ESM-Z.

### Phase 1: Windows characterization and abstraction

- Add process, SteamCMD command, install-detection, update-asset, save-root, and migration tests.
- Introduce `host/base.py`, `host/models.py`, and `host/windows.py`.
- Move existing Windows behavior without intentional changes.
- Build and exercise the Windows v0.9.x upgrade matrix.

Approval gate: Windows behavior and package update remain green before Linux code merges.

### Phase 2: Ubuntu Linux prototype

- Add host detection and prerequisite diagnostics.
- Add Linux SteamCMD install/detection and Windows-depot command.
- Add per-instance Wine prefix preparation.
- Launch one server through Wine in an isolated session and verify config creation/networking.
- Extend to multiple instances and independent stop/restart.

Approval gate: repeatable clean install and 24-hour single/multi-instance operation.

### Phase 3: production lifecycle

- Add per-instance runner and independent systemd units.
- Persist and validate process/unit identity.
- Implement stop escalation, crash recovery, manager restart recovery, and reboot behavior.
- Prove manager update leaves game servers running.

Approval gate: 72-hour soak and failure-injection matrix.

### Phase 4: packaging, security, and documentation

- Add virtualenv installer, `esm-z.sh`, service account, units, uninstall/upgrade flow.
- Add signed/checksummed platform release manifest and rollback.
- Harden TLS, permissions, proxy guidance, diagnostics, and support bundle.
- Publish Ubuntu support; add Debian after test parity.

### Phase 5: optional runtimes and distributions

- Evaluate Proton only for servers that fail under supported Wine.
- Add native Linux server adapter if Keen publishes a Linux binary.
- Expand Fedora/Arch/NAS support based on demand.
- Build Docker as a separate distribution after lifecycle behavior is stable.

## O. Docker Strategy

Implement Docker afterward. Linux plus Wine support will make a future image practical because the runtime command, prefix layout, prerequisites, and lifecycle will already be understood. It does not make Docker free.

A single container containing ESM-Z and all game processes would recreate the manager-update problem: replacing the manager container stops every server. One game container per instance plus a manager container is cleaner, but it requires orchestration and often Docker-socket access. Writable bind mounts are host-dependent and can modify host files; Docker documents that behavior here: [bind mounts](https://docs.docker.com/engine/storage/bind-mounts/). Host networking avoids port translation but shares the host network namespace and permits only one process to bind a given port: [host networking](https://docs.docker.com/engine/network/drivers/host/). Rootless mode reduces daemon/runtime privilege but still has operational constraints: [Docker rootless mode](https://docs.docker.com/engine/security/rootless/).

For Unraid/TrueNAS users, a later container distribution may ultimately be the easiest product, but it should consume the same host-runtime contracts and test suite instead of becoming a fork.

## P. Final Recommendation

Keep one ESM-Z codebase. First extract the current Windows behavior behind a tested `WindowsHost` adapter. Then implement an Ubuntu 24.04 LTS `LinuxWineHost` using Linux SteamCMD with `@sSteamCmdForcePlatformType windows`, one Wine prefix per server, and one independent systemd instance unit per server. Use Wine/Wine64 as the supported default, keep Proton experimental, and defer Docker until the native Linux lifecycle is proven.

Do not ship Linux support based only on a successful launch. The release bar is reliable multi-instance shutdown, crash recovery, manager restart/update persistence, non-root operation, and a complete Windows regression pass.

## Q. Branding Changes in v0.9.1

Files changed or added for this analysis/branding release:

- `README.md`: product title/expanded name, Windows-only release status, screenshot label, package, launcher, and analysis link.
- `docs/LINUX_SUPPORT_ANALYSIS.md`: this repository-specific architecture report.
- `docs/INSTALL.md`: ESM-Z Windows package, launcher, path, and updater naming.
- `docs/FEATURES.md`: ESM-Z update-section heading.
- `docs/RELEASES.md`: v0.9.1 release and branding notes.
- `docs/SCREENSHOTS.md`: ESM-Z screenshot heading.
- `docs/screenshots/dashboard.png`: newly rendered ESM-Z dashboard screenshot.
- `enshrouded_manager/static/index.html`: browser title, login title, application header, update labels, neutral path example, and JavaScript cache key.
- `enshrouded_manager/static/app.js`: ESM-Z version/update heading.
- `enshrouded_manager/manager.py`: v0.9.1, startup log, update notifications, webhook display name/messages, HTTP user agent, and compatible release-asset selection.
- `enshrouded_manager/README.md`: packaged admin-guide title and launcher.
- `enshrouded_manager/USER_README.md`: packaged user-guide title.
- `enshrouded_manager/Launch ESM-Z.bat`: new preferred source-tree launcher.
- `enshrouded_manager/Launch Manager.bat`: legacy-compatibility note; behavior retained.
- `enshrouded_manager/build_exe.ps1`: ESM-Z executable/display name.
- `enshrouded_manager/build_python_required_release.ps1`: ESM-Z stage, package, launcher, install text, and legacy update alias.
- `enshrouded_manager/build_portable_release.ps1`: future portable package branding; no bundled-Python package was produced for this release.
- `enshrouded_manager/build_zip.ps1`: ESM-Z stage/package and preferred launcher.
- `release/README.md`: current package, compatibility alias, and launcher guidance.
- `tests/test_branding_release.py`: ESM-Z UI and new/legacy release-asset tests.
- `release/ESM-Z-PythonRequired-v0.9.1.zip`: primary generated Python-required Windows package.
- `release/EnshroudedServerManager-PythonRequired-v0.9.1.zip`: byte-identical legacy alias for older self-updaters.

Intentionally unchanged for compatibility:

- Python directory/module name `enshrouded_manager`.
- Existing config keys, API routes, server IDs, user IDs, data locations, and `manager.log` filename.
- Existing managed server and SteamCMD data directories.
- `Launch Manager.bat` remains as a legacy launcher.
- Legacy `EnshroudedServerManager-PythonRequired-vX.Y.Z.zip` release names remain accepted, and the build creates a compatibility alias so older ESM-Z installations can discover a renamed release.

## Source Notes and Uncertainties

- Keen's Windows-only statement is current as of the analysis date but may change. A future native Linux server should replace Wine as the preferred adapter without changing shared application code.
- The SteamCMD force-platform syntax is supported by Valve tooling examples, but the current Enshrouded app/depot combination must be verified in the Linux prototype.
- No Wine/Proton reliability claim for the current Enshrouded server build is treated as established until tested by ESM-Z.
- systemd unit control details require a prototype before choosing between persistent user units and narrowly authorized system units.
