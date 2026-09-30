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

# never ship a real API key: ship the template only, user pastes it in-app
Remove-Item "$dist\.env" -Force -ErrorAction SilentlyContinue
if (Test-Path "..\.env.example") {
    Copy-Item "..\.env.example" "$dist\.env.example" -Force
}

New-Item -ItemType Directory -Force -Path "$dist\models\hub" | Out-Null
foreach ($m in @("models--Salesforce--blip-image-captioning-base",
                 "models--Systran--faster-whisper-tiny")) {
    if (Test-Path "hf_models\hub\$m") {
        Copy-Item "hf_models\hub\$m" "$dist\models\hub\" -Recurse -Force
    }
}
Write-Host "Build done: $dist"
