# Releases

## Current Release

**v0.9.6.3a / v0.9.6.3b** - 2026-10-21

Check for Updates now reads and saves the Run beta version checkbox directly; no separate Save Manager Settings step is required. Install uses the existing download, verification, automatic restart, and browser reconnection flow. Switching the checkbox invalidates old channel results. Unrelated unsaved Manager settings are not applied. Stable excludes EML; beta retains it.

### Previous stable

**v0.9.6.2a** - 2026-10-21

- Added staged, administrator-approved updates with automatic manager restart and browser reconnection.
- Added an independent helper, startup health checks, and rollback to the previous manager if startup fails.
- Preserved remote login sessions across restarts; logout, expiry, and password changes invalidate sessions.
- Waits for active server operations and leaves running game server processes alone.
- Requires a release checksum for remote updates. Existing older managers need one final manual restart to activate this updater.
- Stable remains free of EML integration. See [remote update instructions](REMOTE_UPDATES.md).

### v0.9.6.1a - 2026-10-20

Adds Manager > Run beta version, Windows beta selection, four-part version ordering, and return to the paired stable release. No EML integration is installed in stable. See [beta channel instructions](BETA_CHANNEL.md).

## Previous Release

**v0.9.6** - 2026-10-19

Package:

```text
release/ESM-Z-PythonRequired-v0.9.6.zip
```

Changes:

- Loads Enshrouded's Steam app metadata before installing/updating, fixing a reproduced first-install `Missing configuration` failure on Windows.
- Retries this specific metadata failure once without deleting the Steam cache, server files, saves, or configuration.
- Includes current Steam content and app-info diagnostics in the selected server's SteamCMD log.
- Stops save/backup polling when no server is selected and clears stale browser instance selections.

## Experimental Linux Prerelease

**v0.10.0-linux-alpha.7** - 2026-10-19

Linux host support remains experimental and is distributed separately from the stable Windows package. See the GitHub prerelease and `codex/linux-alpha` branch for Linux packages and test instructions.

## Version History

### v0.9.5 - 2026-10-19

- Initializes SteamCMD before downloading the game and retries the first-run self-update exit code 7.
- Captures current bootstrap diagnostics and prioritizes actionable errors over the localization warning.
- Adds Retry Install for failed or interrupted installs, preserving the instance, directory, and query port without consuming another server allocation.
- Registers install instances immediately and prevents duplicate install jobs for an instance.
- Suppresses successful background API polling from the console; errors and user actions are still logged.

### v0.9.4 - 2026-10-16

- Added automatic backup and one-time recovery of the selected server's Steam manifests after Enshrouded state 0x6 failures.
- Serialized SteamCMD jobs and added per-server progress logs and explicit install-success checks.

### v0.9.3 - 2026-10-16

- Failed update-before-start checks show a warning and continue by launching the existing server installation.
- Added a server update failed webhook event and the running ESM-Z version to the persistent page header.

### v0.9.2 - 2026-10-16

- Added an admin update notice and explicit Download & Install action.
- Removed automatic manager update installation; background checks are notification-only.
- Added stable and testing release-channel selection, with stable releases selected by default.
- Added optional SHA-256 verification, package version validation, backup, and rollback protection.
- Added an installed-pending-restart state while keeping running game servers independent from the manager restart.

### v0.9.1 - 2026-09-08

- Renamed the user-facing product to ESM-Z - Enshrouded Server Manager by Zat.
- Renamed new launchers and release packages to prefer ESM-Z while preserving legacy updater compatibility.
- Added a repository-specific Linux host support architecture analysis without changing Windows runtime behavior.
- Clarified installed versus published update versions and corrected misleading up-to-date results for manually updated files.
- Moved optional private/custom GitHub credentials into collapsed advanced settings and masked them in manual update API responses.

### v0.9.0 - 2026-09-08

- Changed webhooks to a per-server list with support for multiple destinations.
- Limited Current Webhooks to the server selected in the header.
- Added independent add, edit, test, enable/disable, and delete controls for each webhook.
- Existing single-webhook configurations migrate automatically.

### v0.8.2 - 2026-09-08

- Added a current webhooks management list under Server Setup & Config.
- Improved GitHub update checks on Windows installs with missing local certificate authority data.

### v0.8.1 - 2026-09-08

- Updated the default GitHub update-check repository after the project moved.

### v0.8.0 - 2026-09-08

- Added per-server Discord/generic webhook notifications under Server Setup & Config.
- Added configurable manager update checks against GitHub releases.
- Added optional self-update package install support for GitHub Release assets.
- Added webhook notifications for manager update availability.

### v0.7.7 - 2026-09-01

- Added shareable repository documentation for install, use, features, screenshots, and releases.
- Updated the Python-required release package to include repository docs and screenshots.

### v0.7.6 - 2026-08-19

- Changed grouped navigation into true sub-tabs under Server Setup & Config and Account.
- Reduced the main tab bar to the primary areas while keeping related pages visible in a second-row sub-tab bar.

### v0.7.5 - 2026-08-19

- Cleaned up navigation into Server Setup & Config and Account groups.
- New server installs now leave Instance name blank and auto-fill Directory from the chosen instance name.
- Added a default Friends game user group and removed the confusing public-server checkbox from basic server settings.

### v0.7.4 - 2026-08-19

- Fixed auto-refresh resetting invite code type selections before code generation.
- Fixed auto-refresh resetting user-management edits before they are saved.
- Added broader UI edit guards so active settings stay in place while the manager refreshes status.

### v0.7.3 - 2026-08-18

- Fixed save imports loading as fresh worlds by installing the selected local world into the server's primary save slot.
- Save imports now stop a running server before replacing the save files.

### v0.7.2 - 2026-08-18

- Added local save-folder world grouping so users choose one Enshrouded world before importing.
- Added safeguards to prevent accidentally importing every world from a multi-save folder.

### v0.7.1 - 2026-08-18

- Improved Windows server stop handling for detached persistent server processes.
- Manager Stop now clears desired-running state immediately so stopped servers are not restarted during shutdown delays.

### v0.7.0 - 2026-08-18

- Added manager update log and version history packaging.
- Changed server launches to detached persistent processes so manager updates do not intentionally stop running servers.
- Added stored server lifecycle metadata including PID, last start, last stop, last restart, and last update timestamps.

### v0.6.0 - 2026-08-18

- Added remote-user save folder import workflow.
- Added server owner creation limits and creation cooldowns.
- Improved install job visibility across users and admin sessions.

### v0.5.0 - 2026-08-18

- Added adaptive Instructions tab.
- Added used invite cleanup.
- Added query port conflict checks before server start.

### v0.4.0 - 2026-08-17

- Added invite URLs, invite titles and descriptions, server-owner invite generation, and invite cleanup tools.
- Moved manager users into role-based user management.
