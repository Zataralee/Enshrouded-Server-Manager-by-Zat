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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "update_runtime.py") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "log_downloads.py") -Destination (Join-Path $Stage "enshrouded_manager")
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot "eml_support.py")) {
    $Emm = Join-Path $PSScriptRoot "vendor\eml-v0.2.0\emm.exe"
    if (-not (Test-Path -LiteralPath $Emm)) { throw "Prepare EML first with python build_eml_vendor.py" }
    if ((Get-FileHash -LiteralPath $Emm -Algorithm SHA256).Hash -ne "b1133f6b8ea7000596cc7710901bd8307b48165b0e650c0487a611d90ea49305") { throw "EML checksum mismatch" }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "eml_support.py") -Destination (Join-Path $Stage "enshrouded_manager")
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "vendor") -Destination (Join-Path $Stage "enshrouded_manager") -Recurse
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Launch ESM-Z.bat") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.md") -Destination (Join-Path $Stage "enshrouded_manager")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_exe.ps1") -Destination (Join-Path $Stage "enshrouded_manager")
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip
Write-Host "Created $Zip"
