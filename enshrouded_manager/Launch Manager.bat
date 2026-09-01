@echo off
cd /d "%~dp0\.."
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" enshrouded_manager\manager.py
) else (
  py -3 enshrouded_manager\manager.py
)
pause
