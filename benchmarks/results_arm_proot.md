# AGRI-SHIELD AI — On-Device Arm Results `[ARM-PROOT]`

**Date:** 31 October 2026, 11:39 and 11:42 local
**Device:** Infinix NOTE 30 5G (X6711), serial `103223136P110167`
**Model:** `agrishield_tomato4.pte`, SHA256 `f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b`
**Claim tag:** **`[ARM-PROOT]`** — Debian aarch64 under `proot-distro` on Android. **Not** a native Android application. Never to be reported as `[ARM-ANDROID]`.

> **Provenance.** Every figure below is read from the machine-readable `android_inference_results.json` and `offline_results.json`, written by the runner on the phone and retrieved to `benchmarks/`. The cross-architecture correctness check is **complete** — see §6.

---

## 1. The headline

The authentic trained MobileNetV2 classifier executed on the Infinix NOTE 30 5G's own Arm cores.

| Run | Radios | Median | Mean | SD | P90 | P99 | Min | Max | Peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| Online | on | 14.328 ms | 14.840 ms | 4.095 ms | 17.458 ms | 31.143 ms | 10.303 ms | 39.080 ms | 23.7 MB |
| **Offline** | **airplane mode** | **12.538 ms** | **13.086 ms** | **1.954 ms** | **15.984 ms** | **17.857 ms** | **10.059 ms** | **17.903 ms** | **23.7 MB** |

Both runs: 50 timed iterations after 10 warm-up, batch 1, input 1×3×96×96, 8 distinct input tensors cycled.

Each run began with a SHA256 check of the model against the Phase 1 hash; the runner aborts on mismatch, so completion is itself evidence that the artifact was authentic and unmodified after transfer.

**Use the offline figure, 12.538 ms median,** as the headline result. Reasoning in §3.

---

## 2. Execution environment

| Property | Value |
|---|---|
| SoC | MediaTek MT6833GP (`mt6833`) |
| CPU | 2× Cortex-A76 @ 2.4 GHz + 6× Cortex-A55 @ 2.0 GHz |
| ISA | ARMv8.2-A — `asimddp` present, **`i8mm` absent**, no bf16, no SVE |
| RAM | 7.44 GiB |
| Android | 14 (SDK 34) |
| ABI | `arm64-v8a` |
| Userland | Debian aarch64 under `proot-distro` |
| Runtime | ExecuTorch 1.5.1, XNNPACK backend |
| Runner | `agrishield_bench`, cross-compiled `aarch64-linux-gnu-g++ 13.3.0`, static libstdc++ |
| Threads | **not pinned** — default XNNPACK thread pool |

ExecuTorch's own CPU detection logged `Number of efficient cores 6`, correctly identifying the six A55s. It failed to read `/sys/devices/soc0/image_version` (a Qualcomm path absent on MediaTek) — harmless, and it fell through to the generic path.

---

## 3. Why the offline run is the better measurement

The two runs are identical in model, inputs, binary and userland. The only difference is radio state. Yet:

- Median improved 14.328 → 12.538 ms (−12.5 %)
- **Max collapsed 39.080 → 17.903 ms (−54 %)**
- Min barely moved: 10.303 → 10.059 ms

A near-unchanged minimum with a halved maximum is the signature of **interference, not throughput change**. The floor is what the hardware can do; the tail is what the scheduler lets it do. Background radio activity — modem interrupts, connectivity wake-ups — was perturbing a machine with only two big cores, and a migrated thread lands on an A55 at 2.0 GHz with a much weaker pipeline.

Two consequences:

1. For AGRI-SHIELD's actual deployment — a field device operating without connectivity — the offline figure is not merely cleaner, it is the *representative* one.
2. The online run's 39 ms outlier should not be reported as "worst case latency" of the model. It is worst-case latency of *an unpinned thread on a contended big.LITTLE SoC*, which is a different claim.

**Thread pinning was not attempted.** Pinning to the two A76 cores would likely tighten the distribution further and is the obvious next experiment. Until it is run, no claim is made about what the A76 pair can do in isolation.

---

## 4. What these numbers are not

- **Not a native Android app measurement.** `proot` intercepts syscalls via `ptrace`. Compute-bound convolution loops are unaffected; allocation and thread operations pay overhead. The proot penalty has **not been quantified**, so the true native figure is likely somewhat *better* than 12.538 ms — but by an unmeasured margin. No native comparison may be asserted.
- **Not an accuracy result.** The eight inputs are deterministic synthetic tensors designed to test numerical reproducibility across architectures. They are not leaf photographs. All eight predict `healthy`, which is an artifact of smooth gradient inputs and says nothing about disease classification. **No accuracy claim of any kind may be drawn from this run.**
- **Not comparable to the desktop figure** without qualification. The x86_64 reference (0.962 ms median) ran on a cloud Xeon vCPU, a different hardware class entirely. The comparison is meaningless as a performance statement; the desktop run exists only to supply reference logits.

---

## 5. Practical reading

12.5 ms per inference is roughly **80 classifications per second** on a midrange 2023 handset, at 23.7 MB peak RSS and an 8.9 MB model. For a single-shot crop-disease diagnosis from a camera capture, latency is not a constraint — the bottleneck will be image capture and preprocessing, not the network.

The absence of I8MM costs something here. XNNPACK's int8 paths fall back to SDOT; an Armv8.6 part with I8MM would do better on a quantized model. The present model is float32, so the gap is smaller than it would otherwise be, but it bears on any future quantization work.

---

## 6. Cross-architecture correctness — VERIFIED

The phone's output was compared against `desktop_reference.json`, produced by the x86_64 build from the **same model file and the same input bytes**.

| Measure | Result |
|---|---|
| **Top-1 agreement** | **8 / 8** |
| Bit-identical vectors | 0 / 8 |
| Max absolute logit difference | **2.384 × 10⁻⁶** |
| Max relative error | 1.026 × 10⁻⁶ |
| Max ULP distance (32 values) | **15** |
| float32 epsilon, for scale | 1.192 × 10⁻⁷ |

Identical agreement from both the online and offline runs.

**Not being bit-identical is the expected and correct outcome**, and is worth stating plainly rather than glossing over. The earlier emulated check *was* bit-identical because qemu executes Arm semantics on x86 floating-point hardware. The handset runs genuine NEON instructions, whose fused multiply-add behaviour and accumulation order differ from the x86 build's. A divergence of ~15 ULPs across a MobileNetV2 forward pass is precisely what reordered FMA produces. A bit-identical result on real Arm silicon would have been the surprising outcome.

**The divergence cannot affect a prediction.** The narrowest top-1 margin across the eight inputs is 0.5082 logits — roughly **213,000×** the largest observed difference. The other seven exceed 3.2 logits, over 1.3 million× the difference. The classifier's decisions are numerically unreachable from this level of noise.

**Conclusion: the Arm port is correct.** The model on the phone computes the same function as the desktop build, to within float32 rounding.

---

## 7. Open items

| Item | Status |
|---|---|
| Thermal readings | **UNAVAILABLE — confirmed.** Both JSONs report 0 thermal zones. `/sys/class/thermal/*/temp` is unreadable from inside proot without root, and was equally unreadable via the non-root adb shell. **No thermal data exists for these runs and none is claimed.** |
| CPU fields inside the JSON | The runner records the **first** `/proc/cpuinfo` entry, so `cpu.part` reads `0xd05` (A55, cpu0). A reporting limitation, not a claim that the device is all-A55 — the full 2×A76 + 6×A55 topology is in `device_sysinfo.txt`. |
| Quantify proot overhead | not attempted |
| Thread pinning to the A76 pair | not attempted |
| Real leaf images on device | not attempted |
| Native Android APK | not attempted — needs the NDK or Maven Central, both unreachable from the build container |
