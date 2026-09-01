$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "dist"
$Versions = Join-Path $Out "versions"
$Stage = Join-Path $Out "EnshroudedServerManager-PythonRequired"
$Zip = Join-Path $Out "EnshroudedServerManager-PythonRequired.zip"
$ManagerPy = Join-Path $PSScriptRoot "manager.py"
$Version = (Select-String -LiteralPath $ManagerPy -Pattern '^APP_VERSION = "([^"]+)"').Matches.Groups[1].Value
if (-not $Version) { $Version = Get-Date -Format "yyyyMMdd-HHmmss" }
$VersionZip = Join-Path $Versions "EnshroudedServerManager-PythonRequired-v$Version.zip"

New-Item -ItemType Directory -Force -Path $Out | Out-Null
New-Item -ItemType Directory -Force -Path $Versions | Out-Null
if (Test-Path $Zip) { Remove-Item -LiteralPath $Zip -Force }
if (Test-Path $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }

New-Item -ItemType Directory -Force -Path $Stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "enshrouded_manager") | Out-Null

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "static") -Destination (Join-Path $Stage "enshrouded_manager") -Recurse
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "manager.py") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.md") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "USER_README.md") -Destination (Join-Path $Stage "enshrouded_manager")
if (Test-Path -LiteralPath (Join-Path $Root "README.md")) {
    Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination (Join-Path $Stage "PROJECT_README.md")
}
if (Test-Path -LiteralPath (Join-Path $Root "docs")) {
    Copy-Item -LiteralPath (Join-Path $Root "docs") -Destination $Stage -Recurse
}

@'
@echo off
cd /d "%~dp0"
echo Starting Enshrouded Server Manager...
echo.
py -3 "%~dp0enshrouded_manager\manager.py"
if errorlevel 1 (
  echo.
  echo Could not start with the Python launcher. Trying python.exe from PATH...
  python "%~dp0enshrouded_manager\manager.py"
)
pause
'@ | Set-Content -LiteralPath (Join-Path $Stage "Run Enshrouded Server Manager.bat") -Encoding ASCII

@'
Enshrouded Server Manager - Python Required Install

This package is for servers that already have Python 3.11+ installed.

1. Extract this ZIP anywhere on the server, for example:
   C:\EnshroudedServerManager

2. Double-click:
   Run Enshrouded Server Manager.bat

3. Open this on the server:
   http://127.0.0.1:8080

By default the manager only listens on localhost, so port 8080 is not exposed
to the network. To access it from another PC, open the Manager tab locally,
change Listen address to "All network interfaces", set the port you want,
save, and restart the manager.

On first load, use Setup & Instances to point to an existing Enshrouded
dedicated server install or install a new server. The manager will download
SteamCMD and then install the dedicated server.

Regular user instructions are in:
enshrouded_manager\USER_README.md

The manager includes an Updates tab. Running game servers are persistent and
are not intentionally stopped when the manager is closed for an update.

Local access does not require a password by default. Remote access uses the
generated admin password in:
enshrouded_manager\data\manager.log
'@ | Set-Content -LiteralPath (Join-Path $Stage "README_FIRST.txt") -Encoding ASCII

[System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null
[System.IO.Compression.ZipFile]::CreateFromDirectory($Stage, $Zip)
[System.IO.File]::Copy($Zip, $VersionZip, $true)
Write-Host "Created $Zip"
Write-Host "Version history copy $VersionZip"
