# Install Guide

This guide is for someone installing Enshrouded Server Manager on their own Windows hardware.

## Requirements

- Windows server or Windows desktop machine that will host the manager.
- Python 3.11 or newer installed and available through `py -3` or `python`.
- Network access from the host to SteamCMD/Steam if you plan to install a fresh dedicated server.
- Permission to open the manager UI port in Windows Firewall only if you want remote browser access.

The current shared package does not bundle Python.

## Download

Download the current release package from this repository:

```text
release/EnshroudedServerManager-PythonRequired-v0.7.7.zip
```

Extract it somewhere permanent, for example:

```text
C:\EnshroudedServerManager
```

Do not extract it inside an existing Enshrouded server install. Keep the manager folder separate from the game server folders it manages.

## Start The Manager

Double-click:

```text
Run Enshrouded Server Manager.bat
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

## Updating

Running game servers are launched as persistent detached processes. Closing or updating the manager should not intentionally stop every running game server.

To update the manager:

1. Stop the manager window/process.
2. Replace the manager files with the newer package.
3. Start `Run Enshrouded Server Manager.bat` again.
4. Check the Updates tab for the version history.

Game servers should still be visible when the manager comes back up.
