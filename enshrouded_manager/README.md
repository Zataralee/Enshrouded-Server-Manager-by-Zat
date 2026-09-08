# Enshrouded Server Manager

Run `Launch Manager.bat`, then open `http://127.0.0.1:8080` on the server machine.

Regular user instructions are in `USER_README.md`. Give that file to non-admin users instead of this admin/setup README.

Localhost can open the UI without a password while `No password from localhost` is enabled. Remote access requires the manager username and password. On first launch, the manager creates a random remote password and writes it to `enshrouded_manager\data\manager.log`; change it from the Manager tab.

Fresh installs listen on `127.0.0.1:8080` by default so the manager is not exposed to the network. Change the listen address and port in the Manager tab if you want LAN access. Use `0.0.0.0` only when you intentionally want the UI reachable from other machines, and restart the manager after changing it.

On first load, the manager checks for configured Enshrouded server instances. If none exist, use `Setup & Instances` to either paste the path to an existing dedicated server install or install a new one. New installs download SteamCMD into the manager folder, then run SteamCMD app update `2278520` into the server instance folder.

Included features:

- Start, stop, restart, and update-check the Enshrouded dedicated server.
- Manage multiple Enshrouded dedicated server instances from one UI.
- Review manager version history and update notes from the Updates tab.
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

The Python-required release script updates the latest zip in `dist` and also keeps a copy in `dist\versions` named with the manager version. Running servers are launched as detached processes and are not intentionally stopped when the manager exits, so updating the manager does not require restarting every game server.

Only open the configured manager TCP port in Windows Firewall if you intentionally want to reach the UI from another machine.
