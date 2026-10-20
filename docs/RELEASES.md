# Releases

## Current Release

**v0.9.6** - 2026-10-19

Package: download `ESM-Z-PythonRequired-v0.9.6.zip` from the [GitHub release](https://github.com/Zataralee/Enshrouded-Server-Manager-by-Zat/releases/tag/v0.9.6).

Changes:

- Loads Enshrouded's Steam app metadata before installing/updating, fixing a reproduced first-install `Missing configuration` failure on Windows.
- Retries this metadata failure once and includes current Steam content and app-info diagnostics in the server log.
- Stops save/backup polling without a selected server and clears stale browser selections.

## Experimental Prerelease

**v0.10.0-linux-alpha.7** - 2026-10-19

- Added the metadata-first installation and bounded retry from stable v0.9.6.
- Moved the Linux Windows-depot platform override before Steam login, addressing an upstream fresh-install failure.
- Stopped save/backup polling before an instance exists and added Steam content/app-info diagnostics.
- Linux host support remains experimental; full installation was verified on Windows, not on a Linux host.

**v0.10.0-linux-alpha.6** - 2026-10-19

- Added the same SteamCMD bootstrap handling, install retry workflow, and quiet background polling as stable v0.9.5.
- Retained Linux Windows-depot selection and Wine/Proton runtime behavior.

**v0.10.0-linux-alpha.5** - 2026-10-16

- Added the same scoped Steam manifest recovery, serialized update jobs, and per-server SteamCMD logs as stable v0.9.4.
- Retained Linux Windows-depot selection and Wine/Proton runtime behavior.

**v0.10.0-linux-alpha.4** - 2026-10-16

- Failed update-before-start checks now show a warning and continue by launching the existing server installation.
- Added a server update failed webhook event for failed SteamCMD checks.
- Added the running ESM-Z version to the persistent header on every manager page.

**v0.10.0-linux-alpha.3** - 2026-10-16

- Added an admin update notice and explicit Download & Install action.
- Removed automatic manager update installation; background checks are notification-only.
- Added stable/prerelease release-channel selection that follows the installed build by default.
- Added optional SHA-256 verification, package version validation, backup, and rollback protection.
- Added an installed-pending-restart state and kept running game servers independent from the manager restart.

**v0.10.0-linux-alpha.2** - 2026-10-16

- Prevented a failed update-before-start operation from retrying every monitor cycle.
- Isolated per-server monitor failures so one broken instance cannot block monitoring, restarts, or backups for the others.
- Added a visible last-start error to the server dashboard.
- Added Linux and Python-required Windows test packages for the corrective alpha.

**v0.10.0-linux-alpha.1** - 2026-09-11

- Added an experimental Linux host path using Wine or Proton.
- Added automatic Proton discovery for standard Steam and Flatpak Steam locations.
- Added Linux SteamCMD download and Windows depot selection for app `2278520`.
- Added isolated compatibility data and process groups per server instance.
- Added Linux local-save discovery roots and platform-specific updater asset selection.
- Added Linux runtime status and selection under Manager settings.
- Added a Linux installation and test guide.
- This prerelease does not provide systemd services and is not production Linux support.

## Version History

### v0.9.5 - 2026-10-19

- Initializes SteamCMD before downloading the game and retries the first-run self-update exit code 7.
- Captures current bootstrap diagnostics and prioritizes actionable errors over the localization warning.
- Adds Retry Install for failed or interrupted installs, preserving the instance, directory, and query port without consuming another server allocation.
- Registers install instances immediately and prevents duplicate install jobs for an instance.
- Suppresses successful background API polling from the console; errors and user actions are still logged.

### v0.9.4 - 2026-10-16

- Added scoped manifest recovery after Enshrouded state 0x6 failures, serialized SteamCMD jobs, and per-server progress logs.

### v0.9.3 - 2026-10-16

- Failed pre-start update checks display a warning and continue by launching the existing server installation.
- Added the server update failed webhook event and the running ESM-Z version in the header.

### v0.9.2 - 2026-10-16

- Added an admin update notice and explicit Download & Install action.
- Removed automatic manager update installation; background checks are notification-only.
- Added stable and testing release channels, checksum verification, package validation, backup, and rollback protection.

### v0.9.1 - 2026-09-08

- Renamed the user-facing product to ESM-Z - Enshrouded Server Manager by Zat.
- Preserved legacy updater package compatibility and clarified installed versus published manager versions.
- Moved private/custom GitHub credentials into advanced settings and masked saved tokens.

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
