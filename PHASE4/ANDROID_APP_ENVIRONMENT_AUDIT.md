# AGRI-SHIELD AI — Android App Environment and Runtime Compatibility Audit

**Date:** 31 October 2026
**Scope:** everything that had to be established *before* app code was written.

---

## 1. Model compatibility — established from the artifact, not from documentation

The `.pte` was inspected directly rather than assumed about:

| Property | Value | Method |
|---|---|---|
| Flatbuffer file identifier | **`ET12`** | bytes 4–7 of the file |
| Extended header magic | `eh00`, header size 32 | parsed |
| Program section | **15,616 bytes** | from the extended header |
| Constant segment | ~8.87 MB | file size − segment base offset |
| Backend referenced | **`XnnpackBackend`** — and only that | string scan |
| Undelegated ATen operators | **none** | zero `namespace::op` strings in the program section |
| Quantization | none | no `quantized_decomposed` references |
| SHA-256 | `f57f5ec3…37f4b` | matches the frozen Phase 1 artifact |

**Two consequences that shaped the design:**

1. **The graph is delegated to XNNPACK in its entirety.** There are no undelegated operators, so the Android runtime needs the XNNPACK backend and no portable or optimized kernel registry. The 15.6 KB program against an 8.87 MB constant segment is exactly what full delegation looks like — the graph is a thin wrapper over one delegate blob.
2. **Nothing is quantized**, so the absence of I8MM on this phone (measured in Phase 2) costs less than it would for an int8 model. It still matters for any future quantization work.

---

## 2. Runtime selection

| Question | Answer |
|---|---|
| Exporting version | ExecuTorch **1.5.1** (Python) |
| Android artifact | `org.pytorch:executorch-android` |
| Is 1.5.1 published for Android? | **Yes** — on Maven Central, published late September 2026 |
| Version chosen | **1.5.1**, pinned |
| ABIs in the AAR | `arm64-v8a`, `x86_64` |
| ABI needed | `arm64-v8a` (measured on the device in Phase 2) |
| Java API | `org.pytorch.executorch.{Module, EValue, Tensor}` |
| Transitive deps | kotlin-stdlib 1.9.23, fbjni 0.7.0, soloader nativeloader 0.10.5, androidx.core 1.13.1 |

**Pinning the Android runtime to the exporting version removes schema-mismatch risk rather than managing it.** ExecuTorch v1.5.1 also introduced explicit schema-version checks for PTE files, so a mismatch would fail loudly instead of producing silent nonsense.

`abiFilters` is set to `arm64-v8a` only, which drops the x86_64 `.so` from the APK. Add x86_64 back if you ever want to run on an emulator.

---

## 3. The Linux/proot runner does NOT transfer to Android

The Phase 2 runner is a glibc-linked aarch64 ELF using ExecuTorch's **C++** API. Android's C library is Bionic. That binary cannot load on Android — which is precisely why Phase 2 ran it inside a Debian rootfs under proot.

The Android app is therefore a **different integration path**, not a port: the prebuilt AAR with its JNI bindings and the Java/Kotlin `Module` API. Nothing is compiled from C++ source, so **no NDK is required** — about 1 GB less setup than a typical Android ML project.

What carries across is the thing that matters: the same `.pte`, the same XNNPACK backend, the same preprocessing arithmetic.

---

## 4. Host toolchain — measured, and absent

Measured on the laptop at 10:01 today:

| Component | State |
|---|---|
| Android Studio | **not installed** |
| Android SDK | **not installed** (`ANDROID_HOME` empty, SDK dir absent) |
| JDK / Java | **not installed** (`JAVA_HOME` empty) |
| Gradle | **not installed** |
| NDK | not installed — **and not needed** |
| CMake | not installed — not needed |
| Platform-Tools / ADB | **installed** at `phase2\platform-tools\` |
| Free space on C: | 64.5 GB |

Build container: `dl.google.com` and Maven Central both **blocked**, so neither the SDK nor the AAR can be fetched here.

**Net: the project cannot be compiled by me.** `DEPENDENCY_AND_DOWNLOAD_REPORT.md` sets out what installing the toolchain costs.

---

## 5. Three design decisions worth recording

### 5.1 `createScaledBitmap` is not used anywhere

Android's bilinear samples 2×2 with no pre-filtering; Pillow's scales its filter support with the downscale factor. On a ~27× downscale, measured divergence on the normalised tensor was **0.8235 max** on leaf-like texture, against a range spanning ~4.4. The verified Pillow-compatible resampler is used instead, unmodified.

The one place a box downsample *is* permitted is `BitmapFactory`'s `inSampleSize`, which is power-of-two area averaging and therefore antialiased — and it is off by default (`maxDecodeEdge = 0`).

### 5.2 The app declares no `INTERNET` permission

Offline operation is enforced by Android rather than asserted by us: the app cannot open a socket. This is verifiable independently of anything I say:

```
adb shell dumpsys package org.agrishield.ai | findstr INTERNET
```

Expect no output. Adding the permission for any reason would forfeit the project's strongest offline claim.

### 5.3 The model's hash is checked before it is used

Same discipline as the Phase 2 and Phase 3 runners: a number produced by some other file is worthless, and silent substitution is worse than a crash. The app refuses to run on mismatch.

---

## 6. Verification status

| Claim | Status |
|---|---|
| Model is XNNPACK-delegated, no undelegated ops | **VERIFIED** from the artifact |
| `executorch-android:1.5.1` exists and matches the export | **VERIFIED** via Maven Central listings |
| Kotlin preprocessing reproduces Pillow | **VERIFIED** — 9/9 bit-exact on OpenJDK 21 |
| Verified resampler preserved in the app unmodified | **VERIFIED** — SHA-256 identical to the tested file |
| Unit-test expectations match the implementation | **VERIFIED** — resize 4000×3000→145×109, crop offset 6, `int(96×1.14)`=109, all confirmed by execution |
| Project compiles | **NOT ATTEMPTED** — no toolchain |
| APK exists | **NO** |
| Runs on the phone | **NO** |
| Android JPEG decoder matches Pillow | **UNMEASURED** — test written, needs a device |

Nothing in this phase has been run on the Infinix NOTE 30 5G. The verified `[ARM-PROOT]` result from Phase 2 remains the project's demonstrated on-device evidence.
