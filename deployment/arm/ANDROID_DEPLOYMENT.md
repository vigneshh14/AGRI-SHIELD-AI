# Android Arm deployment plan

Target: your Arm Android phone. This is the only route to `[ARM]` numbers, and
therefore the only route to satisfying M3 and M4.

## Step 0 — what has to be true first

| Prerequisite | Status |
| --- | --- |
| adb installed and on PATH | **missing** (see `INSTALL_NEXT.md`) |
| USB debugging enabled on the phone | not yet |
| Phone authorised to this laptop | not yet |
| Llama licence approved | not yet requested |
| WSL2 (for the NDK cross-compile) | **not installed** |

## Step 1 — enable USB debugging (your hands, ~2 minutes)

1. Settings → About phone → tap **Build number** seven times
2. Back → System → **Developer options** → turn on **USB debugging**
3. Plug the phone into the laptop with a data cable (not a charge-only cable)
4. A dialog appears on the phone: **Allow USB debugging** → tick "Always allow
   from this computer" → Allow

## Step 2 — profile the device (automated)

Double-click **`probe_phone.bat`** in the project folder. It writes
`phone_profile.txt`, which I read back directly — you do not need to copy
anything out of it.

It collects manufacturer, model, SoC, board platform, Android version and API
level, CPU ABI list, full `/proc/cpuinfo`, the **CPU feature flag line**, the
**MIDR identification register**, core topology and max frequencies, total RAM,
free space on `/data`, and a write-and-read test under `/data/local/tmp`.

### The one line that decides the performance story

The `Features` line in `/proc/cpuinfo`. What to look for:

| Flag | Meaning | Consequence |
| --- | --- | --- |
| `asimd` | Advanced SIMD (NEON) | baseline, present on all arm64 |
| `asimddp` | SDOT / UDOT dot product | Armv8.2+; usable int8 path |
| **`i8mm`** | **Int8 matrix multiply** | **Armv8.6+; the fast int4/int8 LLM path** |
| `bf16` | bfloat16 | nice to have |
| `sve` / `sve2` | Scalable Vector Extension | newer flagships only |

If `i8mm` is present, the KleidiAI kernels inside XNNPACK take the fast path and
the phone will outrun a Raspberry Pi 5 on this workload — the Pi's Cortex-A76 is
Armv8.2 and has `asimddp` but **not** `i8mm`. That contrast is a genuine
SoC-level finding and belongs in the report either way the result falls.

The MIDR register is the same thing ExecuTorch was probing in the sandbox run,
where it failed on x86 and logged `Failed to open midr file`. On the phone it
should succeed. Capturing that is a small but real piece of evidence that the
Arm feature-detection path is live.

## Step 3 — compatibility determination

Decided once `phone_profile.txt` exists. The criteria:

| Requirement | Threshold | Why |
| --- | --- | --- |
| CPU ABI | must include `arm64-v8a` | ExecuTorch Llama runner is 64-bit |
| Android API | 26+ comfortably, 21 minimum | NDK target |
| Free space on `/data` | ≥ 3 GB | `.pte` ~0.96 GB + runner + room |
| RAM | ≥ 4 GB, 6 GB+ comfortable | int4 1B model plus KV cache |
| `i8mm` | desirable, not required | determines which performance story we tell |

Known so far: ExecuTorch **1.5.1** verified working on the build side, with
`to_edge_transform_and_lower` + `XnnpackPartitioner`. Android targets XNNPACK,
which is the backend we are already using — so the export artifact and the
runtime path are the same family on both sides.

## Step 4 — build the runner

Cross-compile with the Android NDK:

```bash
cmake -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
      -DANDROID_ABI=arm64-v8a \
      -DANDROID_PLATFORM=android-26 \
      -DCMAKE_BUILD_TYPE=Release \
      -DEXECUTORCH_BUILD_XNNPACK=ON \
      -DEXECUTORCH_XNNPACK_ENABLE_KLEIDI=ON \
      -DEXECUTORCH_BUILD_EXTENSION_LLM_RUNNER=ON \
      -DEXECUTORCH_BUILD_KERNELS_QUANTIZED=ON \
      -DEXECUTORCH_BUILD_KERNELS_OPTIMIZED=ON \
      -Bcmake-android-out .
cmake --build cmake-android-out -j4 --config Release
```

`-DEXECUTORCH_XNNPACK_ENABLE_KLEIDI=ON` is the flag that enables the KleidiAI
kernels. Build it twice — once with, once without — and report both numbers.
The delta is a result, not a footnote.

This step is markedly easier under WSL2 than native Windows.

## Step 5 — push and run

```bash
adb shell mkdir -p /data/local/tmp/agrishield
adb push llama3_2_1b.pte       /data/local/tmp/agrishield/
adb push tokenizer.model       /data/local/tmp/agrishield/
adb push llama_main            /data/local/tmp/agrishield/
adb push libllama_runner.so    /data/local/tmp/agrishield/
adb shell chmod +x /data/local/tmp/agrishield/llama_main

adb shell "cd /data/local/tmp/agrishield && \
  LD_LIBRARY_PATH=. ./llama_main --model_path=llama3_2_1b.pte \
  --tokenizer_path=tokenizer.model --prompt='Tomato late blight advice:' --seq_len=128"
```

**GATE 1 passes the moment coherent tokens come out of that command with the
phone in airplane mode.** Capture the terminal output; it is the evidence for M3
and M4.

## Step 6 — benchmarks to collect

All tagged `[ARM]`, into `benchmarks/results_arm.md`:

- Prefill latency and decode latency, separately — they are different workloads
- Tokens per second, KleidiAI on vs off
- Peak RSS during generation (`adb shell dumpsys meminfo <pid>`)
- `.pte` size on disk against context length
- Vision model latency alone, Llama alone, then both in sequence
- Sustained-load behaviour: run ten times back to back and watch for thermal
  throttling. Phones throttle hard; that is a finding, not a problem to hide.
- Power: no inline meter on a phone, so use `dumpsys batterystats` deltas across
  a fixed workload and **label it an estimate**, or state that power was not
  measured. Do not report a number you did not measure.

## Known risk

If the NDK cross-compile fails on Windows without WSL2, that blocks GATE 1.
Mitigation order: install WSL2; if that stalls, fall back to a community
pre-exported `.pte` plus a prebuilt runner to prove the runtime path first, and
do your own export afterwards.
