# Releases

## Current Release

**v0.8.0** - 2026-09-08

Package:

```text
release/EnshroudedServerManager-PythonRequired-v0.8.0.zip
```

Changes:

- Added per-server Discord/generic webhook notifications under Server Setup & Config.
- Added configurable manager update checks against GitHub releases.
- Added optional self-update package install support for GitHub Release assets.
- Added webhook notifications for manager update availability.

## Version History

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
