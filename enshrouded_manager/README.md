# ESM-Z

ESM-Z - Enshrouded Server Manager by Zat.

Run `Launch ESM-Z.bat`, then open `http://127.0.0.1:8080` on the server machine.

Regular user instructions are in `USER_README.md`. Give that file to non-admin users instead of this admin/setup README.

Localhost can open the UI without a password while `No password from localhost` is enabled. Remote access requires the manager username and password. On first launch, the manager creates a random remote password and writes it to `enshrouded_manager\data\manager.log`; change it from the Manager tab.

Fresh installs listen on `127.0.0.1:8080` by default so the manager is not exposed to the network. Change the listen address and port in the Manager tab if you want LAN access. Use `0.0.0.0` only when you intentionally want the UI reachable from other machines, and restart the manager after changing it.

On first load, the manager checks for configured Enshrouded server instances. If none exist, use `Setup & Instances` to either paste the path to an existing dedicated server install or install a new one. New installs download SteamCMD into the manager folder, then run SteamCMD app update `2278520` into the server instance folder.

Included features:

- Start, stop, restart, and update-check the Enshrouded dedicated server.
- Manage multiple Enshrouded dedicated server instances from one UI.
- Review manager version history and update notes from the Updates tab.
- Receive an admin notice for compatible GitHub releases and install an update with an explicit admin click.
- Generate account invite codes with optional titles and descriptions for admin tracking.
- Remove server instances from the manager registry without deleting server files.
- Monitor each persistent server process and restart it after crashes unless it was stopped from the UI.
- Edit `enshrouded_server.json`, user groups, bans, logs, and scheduled restarts.
- Configure multiple Discord or generic JSON webhooks independently for each server.
- Upload a zipped savegame into the server `savegame` folder. The current save is backed up first.
- Create local save/config backups and optionally push them to an FTP server.
- Build a distributable zip with `enshrouded_manager\build_zip.ps1`.
- Build a manager-only portable zip with bundled Python using `enshrouded_manager\build_portable_release.ps1`.
- Build a smaller zip for machines that already have Python using `enshrouded_manager\build_python_required_release.ps1`.
- Build an exe with `enshrouded_manager\build_exe.ps1` after installing PyInstaller.

The Python-required release scripts keep versioned packages in `dist\versions`. Manager update checks are notification-only until an admin clicks Download & Install Update. From v0.9.6.2a/b, the updater stages and verifies the package, preserves `data`, backs up manager files, restarts itself, and reconnects the browser. A failed startup triggers file rollback and relaunch of the previous manager. Upgrading an older manager to this updater requires one final manual restart. Running servers remain detached and are not intentionally stopped. See `docs/REMOTE_UPDATES.md`.

Only open the configured manager TCP port in Windows Firewall if you intentionally want to reach the UI from another machine.
