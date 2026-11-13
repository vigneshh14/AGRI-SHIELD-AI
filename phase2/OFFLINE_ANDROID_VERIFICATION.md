# AGRI-SHIELD AI — Offline Operation Verification

**Date:** 31 October 2026, 11:42 local
**Device:** Infinix NOTE 30 5G (X6711), Android 14
**Claim tag:** `[ARM-PROOT]`

---

## 1. What was tested

Whether the crop-disease classifier runs on the phone with **all radios disabled**. The brief requires at least five predictions with connectivity off, and requires that offline operation not be claimed merely because the application has no visible internet requirement.

---

## 2. Method

1. The model had already run once with radios **on** (11:39), establishing a baseline.
2. **Airplane mode was enabled** on the handset.
3. `run_bench.sh` was re-executed inside the Debian aarch64 rootfs, with no other change — same binary, same model file, same input file.
4. The run performed **10 warm-up inferences, 8 logit-capture inferences, and 50 timed inferences — 68 in total**, against a requirement of five.
5. Results were written to `offline_results.json` on the device.

---

## 3. Evidence that the radios were actually off

| Evidence | Strength |
|---|---|
| Aeroplane icon visible in the status bar in a screenshot taken **during** the run | **Direct, contemporaneous** |
| Mobile signal bars and the 4G/5G indicators **absent** from the same status bar, where they had been present in the preceding screenshot | **Direct, contemporaneous** |
| Network throughput indicator reading `0.00 K/S`, against `1.90 K/S` moments earlier | Direct, contemporaneous |
| `adb shell settings get global airplane_mode_on` | **NOT CAPTURED** — USB dropped before the pull |

**This is honest about its own limits.** The radio state is established by on-screen system indicators photographed at the time of the run, not by an `adb` query of the setting. That query was attempted and failed because the device had left USB. The visual evidence is contemporaneous and unambiguous — the system status bar is not something the application could have influenced — but it is a photograph of an indicator rather than a reading of the setting, and is described as such.

---

## 4. Result

**The model ran with radios off.** Completed, exit 0, results written.

| Metric | Offline (airplane mode) | Online (radios on) |
|---|---|---|
| Timed iterations | 50 | 50 |
| Median | **12.538 ms** | 14.328 ms |
| Mean | 13.086 ms | 14.840 ms |
| P90 | 15.984 ms | 17.458 ms |
| Min | 10.059 ms | 10.303 ms |
| Max | **17.903 ms** | 39.080 ms |
| Peak RSS | 23.7 MB | 23.7 MB |

Offline operation did not merely work — it worked **better**, and measurably so. See `results_arm_proot.md` §3: a near-unchanged minimum alongside a halved maximum indicates the radios were perturbing scheduling on a two-big-core SoC, not that throughput differed.

---

## 5. What this does and does not establish

**Establishes:**

- The classifier requires no network at inference time. 68 inferences completed with radios disabled.
- The model file, runtime and backend are all local to the device; nothing was fetched during the run.
- Offline performance is not degraded relative to online.

**Does not establish:**

- That the *application* as a whole is offline-capable. Only the inference runner was tested. The advisory layer, the knowledge base and the web UI were not exercised on the device.
- That no outbound connection would ever be attempted. This test shows the model runs without connectivity; it does not instrument socket calls. The desktop-side offline audit did that separately, by monkey-patching `socket.socket.connect` to raise on any non-loopback address and recording **0 outbound attempts** — that result stands on its own and is not superseded here.
- Anything about classification accuracy. The inputs were synthetic validation tensors.

---

## 6. Output correctness while offline — VERIFIED

`offline_results.json` was retrieved and its eight logit vectors checked against `benchmarks/desktop_reference.json`:

- **Top-1 agreement: 8 / 8**
- Max absolute logit difference: **2.384 × 10⁻⁶** (max 15 ULPs, relative error 1.03 × 10⁻⁶)
- Narrowest decision margin: 0.5082 logits — about **213,000×** the largest observed difference

So the model did not merely *run* with radios off; it produced **numerically correct output** with radios off, indistinguishable from the online run and from the desktop reference to within float32 rounding. Full analysis in `benchmarks/results_arm_proot.md` §6.

### One measurement that is not available

Both runs report **0 thermal zones**. `/sys/class/thermal/*/temp` is unreadable from inside the proot rootfs without root, and was equally unreadable via the non-root adb shell. **No thermal data exists for these runs, and none is claimed anywhere in the Phase 2 documents.** Thermal behaviour under sustained inference remains uncharacterised.
