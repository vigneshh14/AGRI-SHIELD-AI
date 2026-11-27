# One command for the on-phone run (GATE 1). From the repo root, phone on USB debugging:
#   .\scripts\run_on_phone.ps1
# 1. downloads the latest CI-built APK from the apk-latest release and checks its SHA256
# 2. installs it and opens the app once (creates the app's files folder)
# 3. verifies and pushes the classifier + Llama model (push_models.ps1)
# 4. clears the log and shows the AGRI_ARM lines live (Ctrl+C to stop)
param(
    [string]$Classifier = "$HOME\Documents\AGRI_SHIELD_AI\models\agrishield_tomato4.pte",
    [string]$Package = "org.agrishield.ai"
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# adb from the Phase 2 setup, if it is not already on PATH
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    foreach ($d in "$HOME\Documents\AGRI_SHIELD_AI\phase2\platform-tools",
                   "$env:LOCALAPPDATA\Android\Sdk\platform-tools") {
        if (Test-Path "$d\adb.exe") { $env:Path = "$d;$env:Path"; break }
    }
}
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { throw "adb.exe not found. Install Android platform-tools (developer.android.com/tools/releases/platform-tools) and add it to PATH." }

$dev = (adb devices) -match "`tdevice$"
if (-not $dev) { throw "No phone found. Plug it in, allow USB debugging, then run 'adb devices'." }

$rel = "https://github.com/vigneshh14/AGRI-SHIELD-AI/releases/download/apk-latest"
New-Item -ItemType Directory -Force -Path build_apk | Out-Null
curl.exe -L --fail -o build_apk\agri-shield-ai-debug.apk "$rel/agri-shield-ai-debug.apk"
curl.exe -L --fail -o build_apk\agri-shield-ai-debug.apk.sha256 "$rel/agri-shield-ai-debug.apk.sha256"
$want = ((Get-Content build_apk\agri-shield-ai-debug.apk.sha256) -split '\s+')[0].ToLower()
$got = (Get-FileHash build_apk\agri-shield-ai-debug.apk -Algorithm SHA256).Hash.ToLower()
if ($want -ne $got) { throw "APK SHA256 mismatch: got $got, expected $want" }
Write-Host "APK verified: $got"

adb install -r build_apk\agri-shield-ai-debug.apk
adb shell monkey -p $Package -c android.intent.category.LAUNCHER 1 | Out-Null
Start-Sleep -Seconds 3

& "$PSScriptRoot\push_models.ps1" -Classifier $Classifier -Package $Package

Write-Host ""
Write-Host "Now: turn on AIRPLANE MODE, start the screen recorder, open AGRI-SHIELD AI,"
Write-Host "pick a tomato leaf photo. Advisory text should stream under 'Advisory'."
Write-Host "Live log below (Ctrl+C to stop). Paste these lines to Claude."
adb logcat -c
adb logcat -s AGRI_ARM
