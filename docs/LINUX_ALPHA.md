# Linux Alpha Test Guide

This guide is for the experimental `v0.10.0-linux-alpha.1` branch. It is not a production Linux release. Keen Games currently supports the Enshrouded dedicated server on Windows only, so ESM-Z uses Wine or Proton to run the Windows server build.

## Before You Start

- Use an x86_64 Linux host with Python 3.11 or newer.
- Install Wine or Wine64 if available for your distribution. Proton installed through Steam is also supported as a fallback.
- Have at least 30 GB of free storage. The server download can exceed 13 GB after extraction and updates.
- Prevent the host from sleeping during installation and testing.

ESM-Z stores SteamCMD, compatibility data, and server files inside its own extracted directory. The package does not install system packages or alter protected operating-system files.

## Install The Test Build

1. Download `ESM-Z-Linux-PythonRequired-v0.10.0-linux-alpha.1.tar.gz` and its matching `.sha256` file from the prerelease.
2. Open a terminal in the download directory and verify the package:

```bash
sha256sum -c ESM-Z-Linux-PythonRequired-v0.10.0-linux-alpha.1.tar.gz.sha256
```

3. Extract the package and enter its folder:

```bash
tar -xzf ESM-Z-Linux-PythonRequired-v0.10.0-linux-alpha.1.tar.gz
cd ESM-Z-Linux-PythonRequired-v0.10.0-linux-alpha.1
```

4. Start the manager:

```bash
./Run\ ESM-Z.sh
```

5. Open `http://127.0.0.1:8080` in a browser on the host.

If the launcher reports that Python is too old or missing, stop and report the exact output. Install Python through your distribution's supported package manager before trying again.

## Confirm Runtime Detection

Open Manager and find **Linux Compatibility Runtime**. ESM-Z prefers Wine when it is available on `PATH` and falls back to a detected Proton installation.

If the runtime is installed but not detected, select its type and enter the executable path manually. Example paths include:

```text
/usr/bin/wine64
~/.steam/root/steamapps/common/Proton - Experimental/proton
```

Save Manager Settings before installing a server.

## First Server Test

1. Open Server Setup & Config > Setup & Instances.
2. Choose Install New Server.
3. Enter a unique instance name and query port.
4. Start the installation once and watch Install Status.
5. Allow 10-30 minutes for the first SteamCMD download and server installation.
6. Wait for the ready-for-configuration message before using the server controls.

The Linux SteamCMD client downloads the Windows Enshrouded server depot. Each server gets separate compatibility data under `enshrouded_manager/data/linux-runtime/`.

## Test Checklist

- Install one new server instance.
- Confirm `enshrouded_server.json` is created.
- Start the server and wait for it to appear online.
- Join it from another Enshrouded client.
- Stop it from ESM-Z and confirm it stops within the configured timeout.
- Start it again, close only the ESM-Z manager, and confirm the game server remains available.
- Restart ESM-Z and confirm it recognizes the existing server process.
- Test one intentional restart and one update check.
- Test a backup before importing any important world.

This alpha does not install a systemd service. The manager and servers are not expected to survive a host reboot, user logout, or session shutdown.

## Remote Access

The manager starts on localhost only. To open the UI from another device, change the listen address under Manager to all network interfaces, choose the desired UI port, save, and restart ESM-Z.

The game server uses UDP query port `15637` by default. Every instance needs a unique query port. Firewall and router configuration may still be required for access from outside the local network.

## Reporting Results

Include these details with a test report:

```bash
cat /etc/os-release
python3 --version
uname -m
```

Also include:

- ESM-Z version.
- Runtime type and path shown in Manager.
- Whether installation, first start, stop, and manager reattachment succeeded.
- `enshrouded_manager/data/manager.log`.
- The selected server's game logs when startup fails.

Remove passwords, webhook URLs, FTP credentials, public IP addresses, and invite codes before sharing logs.
