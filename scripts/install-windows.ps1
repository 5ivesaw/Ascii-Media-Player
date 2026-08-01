$ErrorActionPreference = 'Stop'
$Repo = if ($env:AMP_REPO) { $env:AMP_REPO } else { '5ivesaw/Ascii-Media-Player' }
$Release = Invoke-RestMethod -Headers @{ Accept = 'application/vnd.github+json' } -Uri "https://api.github.com/repos/$Repo/releases/latest"
$Asset = $Release.assets | Where-Object { $_.name -match 'Windows-x64\.exe$' } | Select-Object -First 1
if (-not $Asset) { throw 'No Windows x64 executable was found in the latest release.' }
$InstallDir = Join-Path $env:LOCALAPPDATA 'ASCII Media Player'
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$Target = Join-Path $InstallDir 'ASCII-Media-Player.exe'
Invoke-WebRequest -UseBasicParsing -Uri $Asset.browser_download_url -OutFile $Target
Write-Host "Installed: $Target"
Write-Host "Run: & '$Target' 'C:\Music'"
