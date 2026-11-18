# Copies BOTH models to the phone for the CI-built APK (which ships without them):
#   classifier -> /sdcard/Android/data/org.agrishield.ai/files/models/agrishield_tomato4.pte
#   Llama      -> /sdcard/Android/data/org.agrishield.ai/files/llama/  (via get_llama_model.ps1)
# The app re-checks the classifier's SHA-256 before loading it.
# Usage (repo root, phone connected with USB debugging, app installed and opened once):
#   .\scripts\push_models.ps1 -Classifier "C:\Users\VIGNESH\Documents\AGRI_SHIELD_AI\models\agrishield_tomato4.pte"
param(
    [Parameter(Mandatory = $true)][string]$Classifier,
    [string]$Package = "org.agrishield.ai"
)
$ErrorActionPreference = "Stop"
$expected = "f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b"
$got = (Get-FileHash $Classifier -Algorithm SHA256).Hash.ToLower()
if ($got -ne $expected) { throw "Classifier SHA256 mismatch: got $got, expected $expected" }
Write-Host "Classifier verified: $got"
$base = "/sdcard/Android/data/$Package/files"
adb shell mkdir -p "$base/models"
adb push $Classifier "$base/models/agrishield_tomato4.pte"
& "$PSScriptRoot\get_llama_model.ps1" -Push -Package $Package
adb shell ls -l "$base/models" "$base/llama"
Write-Host "Done. Open AGRI-SHIELD AI, pick a leaf photo; watch: adb logcat -s AGRI_ARM"
