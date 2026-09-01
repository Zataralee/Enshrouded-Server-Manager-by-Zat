$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) { $Python = "py" }
& $Python -m PyInstaller --onefile --name EnshroudedServerManager `
  --add-data "$PSScriptRoot\static;static" `
  "$PSScriptRoot\manager.py"
Write-Host "EXE build complete. Copy dist\EnshroudedServerManager.exe beside the Enshrouded Dedicated Server and Steamcmd folders."
