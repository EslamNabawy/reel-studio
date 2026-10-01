# Rebuild the app bundle. Run:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Get-Process VideoVoiceOver* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

pyinstaller --noconfirm VideoVoiceOver.spec

# restore externals wiped by pyinstaller
$dist = "dist\VideoVoiceOver"
Copy-Item (Get-Command ffmpeg).Source  "$dist\_internal\ffmpeg.exe"  -Force
Copy-Item (Get-Command ffprobe).Source "$dist\_internal\ffprobe.exe" -Force
Copy-Item "icon.ico" "$dist\icon.ico" -Force
if (Test-Path "README_src.txt") { Copy-Item "README_src.txt" "$dist\README.txt" -Force }

# Never ship a real API key: ship the template only, user pastes it in-app.
# The key itself is stored per-user by keystore.py, not in the bundle at all.
Remove-Item "$dist\.env" -Force -ErrorAction SilentlyContinue
# repo root is two levels up from apps\studio
$envExample = Join-Path $PSScriptRoot "..\..\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$dist\.env.example" -Force
} else {
    Write-Warning ".env.example not found at $envExample - bundle will ship without it"
}

# Fail loudly rather than shipping a bundle that is missing an external.
foreach ($f in @("ffmpeg.exe", "ffprobe.exe")) {
    if (-not (Test-Path "$dist\_internal\$f")) { throw "missing $f in bundle" }
}

New-Item -ItemType Directory -Force -Path "$dist\models\hub" | Out-Null
# NOTE: AI model weights are NOT bundled. The app installs them on demand
# (Models card in the UI, or `VideoVoiceOver_CLI.exe --install-models`).
# To ship them offline instead, copy hf_models\hub\* into $dist\models\hub\ here.

Write-Host "Build done: $dist"
