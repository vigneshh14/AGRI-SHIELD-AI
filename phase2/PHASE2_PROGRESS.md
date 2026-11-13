# AGRI-SHIELD AI — Phase 2 Progress

**Updated:** 31 October 2026, 12:25 local
**Objective:** run the trained MobileNetV2 `.pte` on the actual Infinix NOTE 30 5G
**Status: ACHIEVED AND VERIFIED.**

---

## 1. Primary success condition — met

> *"The task is successful only when the authentic trained `agrishield_tomato4.pte` model has executed on the actual Infinix NOTE 30 5G CPU and real device benchmark files have been generated."*

Both conditions hold. The model executed on the handset's own Arm cores, twice, and `android_inference_results.json`, `offline_results.json` and `device_sysinfo.txt` were generated on the device and retrieved.

| Claim | Status |
|---|---|
| Model artifact authentic on laptop | **VERIFIED ON LAPTOP** — SHA256 matched on disk and in container |
| ADB installed, no admin rights | **VERIFIED ON LAPTOP** |
| aarch64 runner built, numerically exact vs x86_64 | **VERIFIED UNDER EMULATION** — 8/8 bit-identical |
| Phone reachable, device profile captured | **VERIFIED ON PHYSICAL PHONE** |
| **I8MM absent / ARMv8.2-A** | **VERIFIED ON PHYSICAL PHONE** |
| Payload transferred, hash re-verified on handset | **VERIFIED ON PHYSICAL PHONE** |
| **Model executed on the phone's CPU** | **VERIFIED ON PHYSICAL PHONE** |
| **Output numerically correct on real Arm silicon** | **VERIFIED ON PHYSICAL PHONE** — 8/8 top-1, ≤15 ULPs |
| **Runs with all radios disabled** | **VERIFIED OFFLINE** — 68 inferences in airplane mode |
| Thermal behaviour | **BLOCKED** — unreadable without root; none claimed |
| Native Android APK | **NOT STARTED** — NDK and Maven both unreachable |
| Llama integration | **NOT STARTED** — deferred by directive |

---

## 2. The numbers

| Run | Radios | Median | Mean | SD | P90 | P99 | Min | Max | Peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| Online | on | 14.328 ms | 14.840 ms | 4.095 ms | 17.458 ms | 31.143 ms | 10.303 ms | 39.080 ms | 23.7 MB |
| **Offline** | **airplane** | **12.538 ms** | **13.086 ms** | **1.954 ms** | **15.984 ms** | **17.857 ms** | **10.059 ms** | **17.903 ms** | **23.7 MB** |

50 timed iterations after 10 warm-up, 1×3×96×96, 8 input tensors cycled. Model 8.891 MB.

Tagged **`[ARM-PROOT]`** throughout — Debian aarch64 under `proot-distro`, not a native APK.

**Headline figure: 12.538 ms median**, roughly 80 classifications per second.

---

## 3. Three findings worth carrying into the report

### 3.1 The phone has no I8MM — Phase 1 §5 is wrong

Measured from the handset's own `/proc/cpuinfo`, identical on all eight cores: `asimddp` present, **`i8mm` absent**, no bf16, no SVE. The device is **ARMv8.2-A** — 2× Cortex-A76 @ 2.4 GHz + 6× Cortex-A55 @ 2.0 GHz, MediaTek MT6833GP.

The Phase 1 report §5 hardware table places this phone on the "Armv8.6+/v9, has I8MM" side of its comparison against the Raspberry Pi 5. That is falsified. The phone sits at the *same* ISA level as the Pi 5's A76, not a generation ahead.

**The Phase 1 archive has not been edited.** Amending §5 is your decision; the evidence is now measured rather than argued from a spec sheet.

### 3.2 Radios perturb latency more than they change throughput

Between the two runs the median improved 12.5 %, but the **maximum fell 54 %** (39.080 → 17.903 ms) and the standard deviation halved (4.095 → 1.954 ms), while the **minimum barely moved** (10.303 → 10.059 ms).

An unchanged floor with a collapsed tail is interference, not throughput. Background radio activity was disturbing scheduling on a part with only two big cores; a migrated thread lands on an A55 and pays for it. For a field device that operates without connectivity, the offline distribution is the representative one — and the online run's 39 ms outlier must not be reported as the model's worst case, because it is the worst case of *an unpinned thread on a contended big.LITTLE SoC*.

### 3.3 Correct on Arm, and not bit-identical — which is the right answer

8/8 top-1 agreement with the desktop reference; max absolute difference 2.384 × 10⁻⁶, at most 15 ULPs.

The earlier *emulated* check was bit-identical because qemu runs Arm semantics on x86 FP hardware. The handset executes real NEON, whose FMA behaviour and accumulation order differ. About 15 ULPs across a MobileNetV2 forward pass is exactly what reordered FMA produces; bit-identity on real silicon would have been the suspicious outcome. The narrowest decision margin is 213,000× the largest difference, so predictions are numerically unreachable from this noise.

---

## 4. What is explicitly not claimed

- **No accuracy result.** The eight inputs are deterministic synthetic tensors for cross-architecture verification, not leaf photographs. All eight predict `healthy`, an artifact of smooth gradient inputs. No classification-accuracy claim may be drawn from any of this.
- **No native Android measurement.** proot intercepts syscalls via `ptrace`; the overhead was not quantified. The true native figure is probably somewhat better than 12.538 ms, by an unmeasured margin.
- **No thermal data.** Zero thermal zones were readable. Sustained-load behaviour is uncharacterised.
- **No desktop-versus-phone performance comparison.** The x86_64 reference ran on a cloud Xeon vCPU and exists only to supply reference logits.

---

## 5. Phase 1 integrity

Untouched. No frozen value altered, no authoritative file replaced, nothing retrained, no Llama work begun. The §5 I8MM discrepancy is recorded as disputed, with measured evidence, and awaits your decision.

---

## 6. What remains

Ranked by value to the submission:

1. **Amend Phase 1 §5** — your decision, evidence in hand.
2. **Thread pinning to the two A76 cores** — likely tightens the distribution; cheap to test.
3. **Real leaf images on the device** — converts a numerical result into a demonstrable one. The phone has a camera; the runner needs a small image-preprocessing path.
4. **Demo video** — the phone now runs the model, so this is recordable today.
5. **Native APK** — needs Android Studio (~3 GB) and realistically a day of build work. Weigh against the 21 days remaining.
6. **Llama 3.2 1B** — still correctly deferred; licence unaccepted, and the advisory system still has 0 source-verified chemical records.
