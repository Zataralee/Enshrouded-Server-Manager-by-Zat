$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "dist"
$Zip = Join-Path $Out "esm-z.zip"
$Stage = Join-Path $Out "esm-z"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
if (Test-Path $Zip) { Remove-Item -LiteralPath $Zip -Force }
if (Test-Path $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Copy-Item -LiteralPath (Join-Path $Root "Enshrouded Dedicated Server") -Destination $Stage -Recurse
Copy-Item -LiteralPath (Join-Path $Root "Steamcmd") -Destination $Stage -Recurse
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "enshrouded_manager") | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "static") -Destination (Join-Path $Stage "enshrouded_manager") -Recurse
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "manager.py") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Launch ESM-Z.bat") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.md") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_exe.ps1") -Destination (Join-Path $Stage "enshrouded_manager")
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip
Write-Host "Created $Zip"
