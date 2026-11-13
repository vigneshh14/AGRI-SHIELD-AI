# AGRI-SHIELD AI — Phase 2 Environment Audit

**Audit date:** 31 October 2026
**Laptop measurement:** `phase2_audit.bat` executed on the target machine at 10:01:08 local time; raw output preserved at `phase2/phase2_audit_raw.txt`
**Target device:** Infinix NOTE 30 5G
**Auditor note:** Nothing in this document is carried over from earlier sessions. Every laptop row was re-measured today. Rows that could not be measured are marked **NOT MEASURED**, not inferred.

---

## 1. Summary

The laptop has **no Android toolchain of any kind** — no Git, no ADB, no JDK, no Android SDK, no CMake. The Phase 1 Python environments (`env-executorch`, `env-vision`) **do not exist on the laptop**; all Phase 1 ExecuTorch work was performed in a cloud container that no longer exists.

The one thing that *is* present, and intact, is the deliverable that matters most: the trained model. `models/agrishield_tomato4.pte` is byte-for-byte the Phase 1 artifact (SHA256 verified against its own metadata record).

The phone is **physically connected over USB and mounted** — it appears in File Explorer under *This PC* as "Infinix NOTE 30 5G". That is MTP file-transfer mode. **It is not evidence that USB debugging is enabled**, and no property, CPU feature, or thermal reading has been taken from the phone. Section 5 is empty by design.

---

## 2. Laptop toolchain — measured

| Component | Result | Evidence |
|---|---|---|
| Git | **NOT INSTALLED** | `where git` → not found; `git --version` → not recognised |
| ADB / platform-tools | **NOT INSTALLED** | `where adb` → not found; `adb version` → not recognised |
| Java / JDK | **NOT INSTALLED** | `where java` → not found; `JAVA_HOME` empty |
| Android SDK | **NOT INSTALLED** | `ANDROID_HOME`, `ANDROID_SDK_ROOT` empty; `%LOCALAPPDATA%\Android\Sdk` absent |
| Android NDK | **NOT INSTALLED** | `ANDROID_NDK_HOME` empty |
| CMake | **NOT INSTALLED** | `where cmake` → not found |
| Python (system) | **3.13.15** | `C:\Users\VIGNESH\AppData\Local\Programs\Python\Python313\python.exe` |
| `env-executorch` | **DOES NOT EXIST** | directory absent from project root |
| `env-vision` | **DOES NOT EXIST** | directory absent from project root |

**Consequence.** The laptop cannot presently build an Android application, cannot run ExecuTorch, and cannot talk to the phone over ADB. Phase 1's reproducibility therefore depends entirely on the archived artifacts, not on this machine's state.

---

## 3. Trained model artifact — verified intact

| Property | Value |
|---|---|
| Path | `models/agrishield_tomato4.pte` |
| Size | 8,890,640 bytes (8.891 MB) |
| SHA256 | `f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b` |
| Classes (fixed order) | `Tomato___Early_blight`, `Tomato___Late_blight`, `Tomato___Septoria_leaf_spot`, `Tomato___healthy` |
| Input | 1 × 3 × 96 × 96, ImageNet normalisation |
| `pretrained_backbone` | `false` — trained from random initialisation |

The SHA256 computed on disk today (`certutil -hashfile`) matches the hash recorded inside `models/agrishield_tomato4.json`, **and** matches the copy staged into the build container. The model is authentic and uncorrupted. The frozen Phase 1 size figure of 8.891 MB is confirmed.

---

## 4. Build-container capability — measured today

The Phase 2 build work runs in a Linux x86_64 container. What that container can and cannot reach materially shapes the deployment route, so it was measured rather than assumed:

| Resource | Status | Impact |
|---|---|---|
| PyPI | **reachable** | ExecuTorch aarch64 wheel obtainable |
| Ubuntu package archive | **reachable** | aarch64 cross-compiler obtainable |
| `raw.githubusercontent.com` | reachable | source headers obtainable |
| GitHub repository API | **restricted** | PlantVillage image repo not accessible this session |
| `dl.google.com` | **BLOCKED** | **no Android NDK, no platform-tools, no Android SDK** |
| Maven Central | **BLOCKED** | **no prebuilt ExecuTorch Android AAR** |

Two blocked hosts remove both of the conventional native-Android routes from the container. Section 6 explains the route that remains.

---

## 5. Phone — NOT MEASURED

**No data has been collected from the Infinix NOTE 30 5G.** ADB is not installed, so the audit script's phone section terminated without executing a single device command. It recorded, verbatim: `ADB NOT ON PATH - no phone inspection performed`.

The following are therefore **unknown and unverified**:

- SoC identity and `/proc/cpuinfo` `Features` line
- Whether the CPU exposes `asimddp` (SDOT) and/or `i8mm`
- Per-core MIDR values and maximum frequencies
- Android version and API level, ABI list
- Available RAM, thermal zone layout, storage headroom
- Whether `/data/local/tmp` permits execution

**Open correction flagged for your decision.** The Phase 2 directive states the Infinix NOTE 30 5G carries a MediaTek Dimensity 6080 (2× Cortex-A76 + 6× Cortex-A55). If that is correct, the part is **ARMv8.2-A**, which provides SDOT but **not I8MM**. The Phase 1 report, §5 hardware table, places the Android phone on the "Armv8.6+/v9, has I8MM" side of its comparison against the Raspberry Pi 5. Those two statements cannot both be true.

I have **not** edited the Phase 1 report, because it is a frozen archive and you asked to be consulted before authoritative files are replaced. The claim is recorded here as disputed. The `Features` line from the phone settles it definitively, and the benchmark runner built for this phase captures that line into its results JSON automatically — so the correction will be evidence-backed rather than spec-sheet-backed.

---

## 6. Deployment route selected

With `dl.google.com` and Maven Central both blocked to the container, neither a Gradle/AAR Android app nor an NDK cross-build can be produced here. The route that *is* available was verified by construction today:

1. The ExecuTorch 1.5.1 **aarch64 wheel** (`manylinux_2_28_aarch64`, 17.8 MB) was downloaded from PyPI. It ships genuine `ARM aarch64` shared objects — `libexecutorch.so`, `libexecutorch_backend_xnnpack.so`, `libexecutorch_threadpool.so` — **plus the full C++ headers**, including the high-level `Module` API.
2. `libexecutorch.so` was confirmed to have **zero** PyTorch/c10 link dependencies. Only the *Python* bindings need libtorch. A C++ runner therefore needs no PyTorch at all — this removes a 484 MB download from the phone.
3. A benchmark runner (`android/agrishield_bench.cpp`) was written against that API and **compiled for both architectures**:
   - x86_64 (validation) — built and executed successfully against the real `.pte`.
   - aarch64 (deployment) — cross-compiled with `aarch64-linux-gnu-g++ 13.3.0`.
4. The resulting Arm binary is 84,744 bytes and depends only on the three shipped `.so` files plus standard glibc/libstdc++.

**Execution environment on the phone.** The wheel's shared objects are glibc-linked. Android's C library is Bionic, so these binaries cannot run natively under Android or Termux. They run inside a **Debian aarch64 rootfs under `proot-distro`**, which supplies glibc. This is an honest and important qualification:

- The code executes on the **real Cortex-A76 / A55 cores**, using real NEON/dotprod kernels. The arithmetic is genuine Arm arithmetic.
- `proot` intercepts syscalls via `ptrace`. Syscall-heavy operations carry overhead; the compute-bound GEMM inner loops do not.
- **It is not a native Android application.** Any latency figure obtained this way must be labelled as such and must not be presented as an Android app measurement.

A native Android app remains the gold standard for the competition and requires the Android SDK/NDK — see `PHASE2_BLOCKERS.md`.

---

## 7. Desktop reference run — for cross-architecture verification

The runner was executed on x86_64 against the real `.pte` with a fixed, deterministic input file (`validation_inputs.bin`, 8 inputs of 3×96×96, SHA256 `6b28415a3f99471b7fa16346fda2d1f353ee851e81a3c0d6f49afcb2cc8eb5c4`). The *same bytes* will be fed to the phone, so there is no cross-platform random-number question — both devices consume an identical file.

| Metric | Value |
|---|---|
| Timed iterations | 50 (after 10 warm-up) |
| Median latency | 0.936 ms |
| Mean ± sd | 0.945 ± 0.044 ms |
| P90 / max | 0.997 / 1.072 ms |
| Peak RSS | 24.7 MB |
| Host | Intel Xeon @ 2.10 GHz, 2 vCPU (cloud container) |

**This is a `[DESK]` figure on cloud-container hardware and is not a performance claim for any target platform.** Its purpose is to establish the reference logit vectors that the phone must reproduce. All eight reference vectors are recorded in `benchmarks/desktop_reference.json`.

*Caveat on the validation inputs:* they are synthetic gradient-plus-noise tensors, not leaf photographs. They test **numerical reproducibility across architectures**, which is exactly what is needed to prove the Arm port is correct. They test nothing about classification accuracy, and all eight happen to be predicted `healthy`. No accuracy claim of any kind may be drawn from them.

---

## 8. What is ready, and what is blocked

**Ready now, requiring no further work from me:**

- Cross-compiled aarch64 benchmark runner, with the ExecuTorch Arm runtime and XNNPACK backend
- The authentic trained `.pte`
- Deterministic validation inputs and the desktop reference logits
- A complete self-contained payload directory, 13 MB total

**Blocked on you (details and exact commands in `PHASE2_BLOCKERS.md`):**

- Installing Termux and a Debian aarch64 rootfs on the phone — the only remaining step before the model runs on the Infinix
- Installing platform-tools so ADB works, which unlocks `/proc/cpuinfo` capture, thermal sampling and file push without MTP
- Installing the Android SDK/NDK if a native Android application is wanted

**Not claimed anywhere in this document:** that the model has run on the phone; that any Arm latency has been measured; that the phone supports or lacks I8MM; that ExecuTorch is integrated into an Android application.
