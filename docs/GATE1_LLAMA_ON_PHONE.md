# GATE 1: Llama 3.2 1B through ExecuTorch on the Infinix NOTE 30 5G

This is the mandatory requirement. Without it the entry does not qualify, however
good the classifier is. Do this before anything else.

## Why this route

- **No export on the laptop.** `executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET`
  on Hugging Face is **not gated** (checked 13 Nov 2026: `gated: false`). It ships a
  ready `.pte` and `tokenizer.model`. ExecuTorch's own v1.6.0 Llama README still links
  this exact file as the convenience model.
- **No NDK, no C++ build.** The `executorch-android` AAR that the app already uses for
  the classifier contains the Llama runner (`LlmModule`). `LlamaAdvisoryEngine.kt`
  calls it directly.

## Step 1: Download (laptop, PowerShell)

```powershell
mkdir $HOME\Documents\AGRI_SHIELD_AI\models\llama
cd $HOME\Documents\AGRI_SHIELD_AI\models\llama
$R="https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET/resolve/main"
curl.exe -L -o llama3_2_1b_spinquant.pte "$R/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"
curl.exe -L -o tokenizer.model "$R/tokenizer.model"
certutil -hashfile llama3_2_1b_spinquant.pte SHA256
certutil -hashfile tokenizer.model SHA256
dir
```

Paste the two SHA256 values and the file sizes into `benchmarks/results_arm.md`.
**Do not commit the `.pte` to Git.** GitHub rejects files over 100 MB. Put the
download URL and SHA256 in the README instead.

## Step 2: Add the code to the app

Copy into `app/src/main/java/com/agrishield/advisory/`:
`AdvisoryGate.kt`, `KnowledgeBase.kt`, `LlamaAdvisoryEngine.kt`.

If your app's package is not `com.agrishield...`, change only the `package` line
in all three files.

**Check the AAR version** in `app/build.gradle(.kts)`:

```kotlin
implementation("org.pytorch:executorch-android:<version>")
```

- `0.7.0` or newer: fine, no change.
- `0.6.x`: does not compile (`onStats` takes a float there). Move to the version
  the classifier `.pte` was exported with.

## Step 3: Push the model to the phone

The app reads from its own external files folder, which needs no storage permission:

```powershell
$PKG="com.agrishield.app"   # <-- your applicationId from build.gradle
adb shell mkdir -p /sdcard/Android/data/$PKG/files/llama
adb push llama3_2_1b_spinquant.pte /sdcard/Android/data/$PKG/files/llama/
adb push tokenizer.model           /sdcard/Android/data/$PKG/files/llama/
adb shell ls -l /sdcard/Android/data/$PKG/files/llama/
```

(Install the app once first so the folder belongs to it.)

## Step 4: Call it from the Activity

```kotlin
private lateinit var llama: LlamaAdvisoryEngine

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val dir = File(getExternalFilesDir(null), "llama")
    llama = LlamaAdvisoryEngine(File(dir, "llama3_2_1b_spinquant.pte"), File(dir, "tokenizer.model"))
}

// after the classifier returns (topLabel, confidence):
llama.advise(topLabel, confidence,
    onToken = { tok -> runOnUiThread { advisoryView.append(tok) } },
    onDone  = { r -> runOnUiThread {
        advisoryView.text = r.shownText
        sourceBadge.text = if (r.fromLlama) "Llama 3.2 1B · ExecuTorch · on-device"
                           else "Safety fallback (model output rejected)"
        // Show doses from the KB, never from Llama:
        (r.decision as? Decision.Advise)?.record?.let { showChemicalTable(it) }
        Log.i("AGRI_ARM", "wallMs=${r.wallMs} stats=${r.statsJson} viol=${r.violations}")
    } },
    onError = { e -> runOnUiThread { advisoryView.text = "Advisory unavailable: ${e.message}" } })

override fun onDestroy() { llama.close(); super.onDestroy() }
```

`showChemicalTable` lists `record.chemicals` (active ingredient and dose), then
`record.chemicalNote`, `AdvisoryGate.NO_INTERVAL_TEXT` and `record.sourceUrl`.

## Step 5: Pass the gate

1. Phone in **airplane mode**, Wi-Fi and data off.
2. Take a photo, and wait for the advisory to stream.
3. `adb logcat -s AGRI_ARM` (re-enable USB only, which is not a network).

**GATE 1 passes** when coherent advisory text streams on screen in airplane mode
and the badge reads "Llama 3.2 1B · ExecuTorch · on-device". Screen-record it;
this is the core of the demo video.

## Step 6: [ARM] numbers to record

The `stats` JSON from ExecuTorch has prompt-token count, generated-token count, and
model load, prefill and decode timings. Copy them **verbatim** from logcat. Run
10 times back to back and record each run, to show thermal behaviour. Also record:

- `adb shell dumpsys meminfo <pkg>`: peak PSS during generation
- First-run load time vs warm runs
- Classifier latency and Llama latency separately, then end to end

Tag every number `[ARM]`. If a field isn't in the stats string, write "not measured".

## If Step 5 fails

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Llama model missing` | wrong folder or package name | redo Step 3 with the real applicationId |
| Load error / operator not found | `.pte` too old for your AAR (ExecuTorch guarantees `.pte` compatibility only one minor release forward) | Try the sibling `Llama-3.2-1B-Instruct-QLORA_INT4_EO8-ET` (same steps). If that also fails, see the export fallback below |
| App killed during load | memory pressure (8 GB phone, ~1 GB model) | close other apps; check the classifier `Module` isn't loaded twice |
| Garbage text | wrong tokenizer | use the `tokenizer.model` from the same repo |
| Very slow first token | normal first-load cost | report cold and warm numbers separately |

**Export fallback** (only if both pre-exported files fail). Request access to
`meta-llama/Llama-3.2-1B-Instruct` on Hugging Face and download
`original/consolidated.00.pth`, `original/params.json` and `original/tokenizer.model`.
Then, in WSL2 with the **same ExecuTorch version as your AAR**:

```bash
pip install executorch==<AAR version>
git clone --depth 1 --branch v<AAR version> https://github.com/pytorch/executorch.git && cd executorch
python -m extension.llm.export.export_llm \
  --config examples/models/llama/config/llama_q8da4w.yaml \
  +base.model_class="llama3_2" \
  +base.checkpoint=/path/consolidated.00.pth \
  +base.params=/path/params.json
```

This is the v1.6.0 documented command; check the README at your tag. Your laptop
has 7.7 GB RAM, so first give WSL2 at least 8 GB of swap (`.wslconfig`:
`swap=8GB`). Export can take a long time on an i3.
