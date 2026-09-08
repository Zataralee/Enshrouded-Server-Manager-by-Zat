# Feature Guide

## Server Control

- Start, stop, and restart selected servers.
- Run manual SteamCMD update checks.
- Optionally run update checks before start/restart.
- Schedule restart times.
- See server PID, start time, restart time, update time, stop time, uptime, and last exit state.

## Multiple Instances

- Manage multiple Enshrouded dedicated server instances from one UI.
- Add existing server installs by folder path.
- Install new servers into the configured server root directory.
- Restore removed server entries when the files still exist.
- Remove server entries with a prompt to keep or delete files.

## Installation Help

- Downloads SteamCMD when needed.
- Installs the Enshrouded dedicated server.
- Starts a new install once to create `enshrouded_server.json`.
- Stops the server after first config generation so it is ready to configure.
- Shows install progress in the Install Status panel.

## Configuration

- Edit `enshrouded_server.json` from the UI.
- Validate managed query port conflicts before install and before start.
- Manage game server user groups and bans.
- Include default Admin and Friends user groups.
- Save changes while the server is stopped, or warn/restart as needed for running servers.

## Users And Invites

- Primary admin has full permissions.
- Admins can create and reset user accounts.
- Admins can generate one-time invite codes.
- Server owners can generate invite codes scoped to servers they own.
- Invite codes can have a title, description, expiration window, or no-expiration setting.
- Invite URLs can pre-fill the code on the account creation page.
- Users can change their own password after receiving an initial password.

## Saves And Backups

- Import local Enshrouded worlds into a dedicated server.
- Group related local save files so the user selects one world instead of importing the whole save folder blindly.
- Back up current server saves before replacement.
- Create local backups.
- Schedule automatic backups at server-level intervals.
- Optionally send backups to an FTP server.

## Webhooks

- Configure a Discord or generic JSON webhook for each server.
- Choose which events should be sent.
- Send test webhooks from the UI.
- Notify server owners/admins when servers start, stop, restart, crash, update, back up, or finish install jobs.
- Send manager update notifications through configured server webhooks.

## Manager Updates

- Check GitHub releases for newer manager packages.
- Configure the repository, check interval, and optional GitHub token from the Manager tab.
- Private repositories require a GitHub token that can read the repository releases.
- Automatically install available Python-required manager packages when enabled.
- Restart the manager after a self-update install to run the new version.

## Logs And Instructions

- View server and manager logs from the UI.
- Read role-aware instructions inside the Instructions tab.
- Read the manager update history inside the Updates tab.
