$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "dist"
$Stage = Join-Path $Out "EnshroudedServerManager-Portable"
$Zip = Join-Path $Out "EnshroudedServerManager-Portable.zip"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python"

if (-not (Test-Path (Join-Path $BundledPython "python.exe"))) {
  throw "Bundled Python was not found at $BundledPython. Install Python 3.11+ or build the EXE with PyInstaller instead."
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
if (Test-Path $Zip) { Remove-Item -LiteralPath $Zip -Force }
if (Test-Path $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }

New-Item -ItemType Directory -Force -Path $Stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "enshrouded_manager") | Out-Null

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "static") -Destination (Join-Path $Stage "enshrouded_manager") -Recurse
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "manager.py") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.md") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath $BundledPython -Destination (Join-Path $Stage "python") -Recurse

@'
@echo off
cd /d "%~dp0"
echo Starting Enshrouded Server Manager...
echo.
"%~dp0python\python.exe" "%~dp0enshrouded_manager\manager.py"
pause
'@ | Set-Content -LiteralPath (Join-Path $Stage "Run Enshrouded Server Manager.bat") -Encoding ASCII

@'
Enshrouded Server Manager - Portable Install

1. Extract this ZIP anywhere on the server, for example:
   C:\EnshroudedServerManager

2. Double-click:
   Run Enshrouded Server Manager.bat

3. Open this on the server:
   http://127.0.0.1:8080

4. By default the manager only listens on localhost, so port 8080 is not exposed
   to the network. To access it from another PC, open the Manager tab locally,
   change Listen address to "All network interfaces", set the port you want,
   save, and restart the manager. Then open:
   http://SERVER-IP:8080

5. If Windows Firewall asks, allow private network access for the bundled python.exe
   only if you intentionally enabled LAN access. You may also need to allow inbound
   TCP for the configured manager port.

6. On first load, use Setup & Instances to:
   - point to an existing Enshrouded dedicated server install, or
   - install a new server. The manager will download SteamCMD and then install the dedicated server.

Local access does not require a password by default. Remote access uses the generated admin password in:
enshrouded_manager\data\manager.log
'@ | Set-Content -LiteralPath (Join-Path $Stage "README_FIRST.txt") -Encoding ASCII

[System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null
[System.IO.Compression.ZipFile]::CreateFromDirectory($Stage, $Zip)
Write-Host "Created $Zip"
