# Install Guide

This guide is for someone installing ESM-Z - Enshrouded Server Manager by Zat - on their own Windows hardware.

## Requirements

- Windows server or Windows desktop machine that will host the manager.
- Python 3.11 or newer installed and available through `py -3` or `python`.
- Network access from the host to SteamCMD/Steam if you plan to install a fresh dedicated server.
- Permission to open the manager UI port in Windows Firewall only if you want remote browser access.

The current shared package does not bundle Python.

## Download

Download the current release package from this repository:

```text
release/ESM-Z-PythonRequired-v0.9.5.zip
```

Extract it somewhere permanent, for example:

```text
C:\ESM-Z
```

Do not extract it inside an existing Enshrouded server install. Keep the manager folder separate from the game server folders it manages.

## Start The Manager

Double-click:

```text
Run ESM-Z.bat
```

Then open this URL on the server machine:

```text
http://127.0.0.1:8080
```

The manager listens on localhost by default. That means the UI is available on the machine running it, but port `8080` is not exposed to the network.

## First Login

Localhost access can open without a password while `No password from localhost` is enabled.

Remote access requires a username and password. On first launch, the manager writes the generated admin password to:

```text
enshrouded_manager\data\manager.log
```

Change the admin password from the Manager or Account area after first login.

## Enable Remote Access

Only do this if you want the UI reachable from another computer.

1. Open the UI locally at `http://127.0.0.1:8080`.
2. Open the Manager tab.
3. Change the listen address from localhost to all network interfaces.
4. Change the port if desired.
5. Save the settings.
6. Restart the manager.
7. Open the selected port in Windows Firewall if needed.

Use the server IP address and configured port from the other machine, for example:

```text
http://192.168.1.50:8080
```

## Add Your First Server

Open `Server Setup & Config` > `Setup & Instances`.

Use `Use Existing Install` if you already have a dedicated server folder that contains:

```text
enshrouded_server.exe
```

Use `Install New Server` if you want the manager to download SteamCMD and install a fresh Enshrouded dedicated server instance.

New installs can take several minutes. If SteamCMD has to be downloaded for the first time, or if the host connection is slow, 10-20 minutes or longer is possible. Use the Install Status panel and wait until the server says it is ready for configuration.

The first install initializes and updates SteamCMD itself before downloading Enshrouded. Install Status shows this stage, including any automatic initialization retries. If the install fails, use **Retry Install** on that instance or its failed job; this continues with the existing directory rather than creating a duplicate server. Retry does not consume an additional server allocation. A normal local directory such as `C:\ESM-Z` is preferable to a cloud-synced Desktop folder, although the presence of OneDrive alone does not establish the cause of an install failure.

## Updating

Running game servers are launched as persistent detached processes. Closing or updating the manager should not intentionally stop every running game server.

The Manager tab checks published GitHub Releases for ESM-Z updates. Git tags and manually copied files are not releases. The status panel shows the installed version, latest published release, and last check separately. The default repository is public and needs no token; private/custom repository settings are under Advanced update source. Checks never install files automatically. From v0.9.6.2a/b onward, an admin-approved update verifies the required checksum, stages and backs up manager files, restarts the manager, and reconnects the browser. Running game servers are not stopped. See [Remote Updates](REMOTE_UPDATES.md) for recovery and first-upgrade instructions.

To update from the UI:

1. Open Manager and review the ESM-Z Updates section.
2. Click **Check Now** if you do not want to wait for the scheduled check.
3. Click **Download & Install Update** and confirm the prompt.
4. Wait for the update dialog to reconnect and reload into the new version. When upgrading an older manager to this version for the first time, restart ESM-Z manually once instead.
5. Check the Updates tab for the version history.

Game servers should still be visible when the manager comes back up.

For game server updates, stop the selected server and click **Update Check**, or use **Start/Restart** with **Always run update check before start/restart** enabled. SteamCMD progress is saved under that server's **Logs** tab as `esm-steamcmd.log`. ESM-Z backs up the selected server's Steam manifests and retries once if SteamCMD reports the known Enshrouded `0x6` failure. See [SteamCMD Update Recovery](STEAMCMD_RECOVERY.md) for details.
