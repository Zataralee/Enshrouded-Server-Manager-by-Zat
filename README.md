# Enshrouded Server Manager

Private source repository for the Enshrouded Server Manager.

The current manager source lives in `enshrouded_manager/`.

- Admin/setup instructions: `enshrouded_manager/README.md`
- User instructions: `enshrouded_manager/USER_README.md`
- Main server manager: `enshrouded_manager/manager.py`
- Web UI assets: `enshrouded_manager/static/`

This repository intentionally ignores runtime data, logs, installed game server files, SteamCMD, and built release zips. Build output is generated locally into `dist/`.

For machines that already have Python installed, build the release package with:

```powershell
.\enshrouded_manager\build_python_required_release.ps1
```
