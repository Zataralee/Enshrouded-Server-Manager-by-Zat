$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) { $Python = "py" }
& $Python -m PyInstaller --onefile --name esm-z `
  --add-data "$PSScriptRoot\static;static" `
  "$PSScriptRoot\manager.py"
Write-Host "ESM-Z EXE build complete. Copy dist\esm-z.exe beside the Enshrouded Dedicated Server and Steamcmd folders."
