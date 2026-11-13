# Downloads the pre-exported Llama 3.2 1B Instruct (SpinQuant INT4) ExecuTorch model and
# tokenizer, and verifies them against the SHA256 values Hugging Face publishes for them.
# Usage (PowerShell, from the repo root):   .\scripts\get_llama_model.ps1
# Optional push straight to the phone:       .\scripts\get_llama_model.ps1 -Push -Package com.agrishield.app
param(
    [string]$OutDir = "models\llama",
    [switch]$Push,
    [string]$Package = ""
)
$ErrorActionPreference = "Stop"
$repo = "https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET/resolve/main"

# Values from the Hugging Face API (tree/main, lfs.oid and lfs.size), read 13 Nov 2026.
$files = @(
    @{ Remote = "Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"; Local = "llama3_2_1b_spinquant.pte"
       Size = 1135951488; Sha = "8715cdba9e91f6bede00cc5f2d6b12397b95225da5630c4972a8da03001cda3b" },
    @{ Remote = "tokenizer.model"; Local = "tokenizer.model"
       Size = 2183982; Sha = "82e9d31979e92ab929cd544440f129d9ecd797b69e327f80f17e1c50d5551b55" }
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
foreach ($f in $files) {
    $dest = Join-Path $OutDir $f.Local
    $ok = $false
    if (Test-Path $dest) {
        $ok = ((Get-Item $dest).Length -eq $f.Size) -and
              ((Get-FileHash $dest -Algorithm SHA256).Hash.ToLower() -eq $f.Sha)
    }
    if ($ok) { Write-Host "OK (already present): $dest"; continue }
    Write-Host "Downloading $($f.Remote) ($([math]::Round($f.Size/1MB)) MB) ..."
    # -C - resumes a partial download if the connection drops.
    curl.exe -L --fail -C - -o $dest "$repo/$($f.Remote)"
    if ($LASTEXITCODE -ne 0) { throw "download failed: $($f.Remote)" }
    $len = (Get-Item $dest).Length
    $sha = (Get-FileHash $dest -Algorithm SHA256).Hash.ToLower()
    if ($len -ne $f.Size) { throw "SIZE MISMATCH $dest : got $len, expected $($f.Size). Delete it and re-run." }
    if ($sha -ne $f.Sha)  { throw "SHA256 MISMATCH $dest : got $sha. Delete it and re-run." }
    Write-Host "VERIFIED: $dest  sha256=$sha"
}

if ($Push) {
    if (-not $Package) { throw "-Push needs -Package <your applicationId>" }
    $target = "/sdcard/Android/data/$Package/files/llama"
    adb shell mkdir -p $target
    foreach ($f in $files) { adb push (Join-Path $OutDir $f.Local) "$target/" }
    adb shell ls -l $target
}
Write-Host "Done. Record the two SHA256 values above in benchmarks/results_arm.md."
