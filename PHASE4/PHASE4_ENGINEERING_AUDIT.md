# AGRI-SHIELD AI — Phase 4 Engineering Audit

**Date:** 31 October 2026 · **Bundle:** `PHASE4_android_v3.zip`
**Not compiled as an Android app. No APK exists. Nothing has run on the phone.** No Android SDK or Android Gradle Plugin is reachable from the environment this work was done in.

**Note on the brief.** The uploaded brief ends mid-sentence in §5 ("Error handling when no camera/gallery") — the file itself is 124 lines, so this is truncation in the upload, not in reading. §1–§5 are addressed in full. If further sections existed, they have not been seen.

---

## How to read the verification claims

| Label | Meaning |
|---|---|
| **JVM-TESTED** | Compiled by a real Kotlin compiler (K2JVMCompiler) and executed on OpenJDK 21, with results checked against Pillow / torchvision where relevant |
| **STATIC** | Android-dependent code, checked mechanically (37 automated source checks) but **not compiled** |
| **DEVICE: NOT TESTED** | Requires the phone; no claim is made |

Every Android-framework behaviour below — `BitmapFactory`, `getPixels`, `ExifInterface`, `ViewModel`, the camera intent — is **STATIC** at best. The logic those calls feed into was moved into pure Kotlin precisely so it could be **JVM-TESTED**.

---

## 1. Preservation — verified

| Item | Status |
|---|---|
| `AgriShieldPreprocess.kt` (verified resampler) | **byte-identical** — SHA-256 `45dee236…c218`; parity re-run **9/9 bit-exact** from the app's own copy |
| `PreprocessUnitTest.kt` | **byte-identical**; 8/8 pass |
| `DecoderParityTest.kt` | **byte-identical**; still compiles against the new API (`ImageLoader.toRgb(Bitmap)` kept for it) — STATIC |
| Model asset name, SHA-256 check, class order, `[1,3,96,96]`, ImageNet constants | unchanged; checked mechanically |
| Phase 1 / 2 / 3 deliverables | untouched; one Phase 3 erratum is **recorded, not edited** (§8) |
| Model input pixels | **unchanged** — nothing in this round downsamples, crops, or colour-converts the model input differently |

---

## 2. Image-pipeline memory safety (§2)

### 2.1 Allocation inventory — 4000×3000 photograph

| Allocation | v2 | v3 | Pool |
|---|---|---|---|
| Decoded ARGB_8888 bitmap | 48 MB | 48 MB | native |
| Second full bitmap for EXIF rotation (`createBitmap` + matrix) | **+48 MB** when rotated | **0** — removed | native |
| RGB array for the resampler | 36 MB | 36 MB | Java heap |
| Row strip | 4 MB | 4 MB (freed before resampling) | Java heap |
| Resampler intermediates | ~1.5 MB | ~1.5 MB | Java heap |
| Display thumbnail | ~3 MB | ~3 MB, separate small decode | native |
| **Full pipeline runs per photo** | **2** (Preview, on the **main thread**, then Result) | **1** (Result, background) | — |

**Native peak:** 96 MB → **48 MB** for a rotated photo. **Full-resolution decodes per photo:** 2 → **1**.

The 36 MB RGB array is **not** eliminated, as the review correctly noted. It is the verified resampler's input. It could be streamed — the horizontal pass is row-independent, so a strip-fed variant would be provably bit-identical — but that means duplicating verified internals, and the brief forbids changing preprocessing for memory without a parity strategy. It is listed as an option, not implemented.

### 2.2 What changed

- **Pre-flight refusal.** `MemoryPlan` itemises every large allocation from the image dimensions alone and checks them against the real Java-heap and native budgets **before allocating**. Too large → a readable message; nothing is downsampled.
- **EXIF without a second bitmap.** `OrientedRgb` applies the orientation as an exact pixel permutation while copying into the RGB array that was needed anyway. This also removes a parity risk: Android does not document that `createBitmap(…, matrix, filter=true)` is pixel-exact; Pillow's `exif_transpose` is.
- **Release as early as possible.** The full bitmap is recycled in a `finally` block, so it is freed even on failure.
- **OOM handling.** `OutOfMemoryError` is caught at decode and at conversion, and mapped to `ImageMemoryException` with a user-facing message, as is the array-limit guard.
- **Preview path is separate.** `loadPreview()` decodes a small display-only bitmap off the main thread. Only the model path is full resolution.
- **Two parity hardenings found along the way:**
  - `inPremultiplied = false` for the model decode. Pillow's `convert("RGB")` drops alpha without compositing; a premultiplied bitmap has already multiplied RGB by alpha and zeroed transparent pixels, which `getPixels` cannot undo exactly. JPEG is unaffected; transparent PNG/WebP would have diverged.
  - **Colour space detection.** `getPixels` returns sRGB. For a photo tagged with another colour space (e.g. Display P3), Android converts and Pillow does not. This is now **detected and shown on the result screen**, not hidden.

### 2.3 Measured — JVM-TESTED

Java-heap peak of the actual pipeline (`OrientedRgb.extract` + `AgriShieldPreprocess.preprocess`) on OpenJDK 21, source pixels supplied by a generator so the measurement contains only what Android's Java heap would hold:

| Size | Planned (itemised) | **Measured** | Required by check (×1.25 + 4 MB) | Covered |
|---|---|---|---|---|
| 640×480 | 1.6 MB | **2.3 MB** | 6.0 MB | yes |
| 1920×1080 | 8.2 MB | **9.5 MB** | 14.2 MB | yes |
| 4000×3000 | 40.1 MB | **42.2 MB** | 54.1 MB | yes |
| 3000×4000, EXIF 6 | 39.1 MB | **41.2 MB** | 52.9 MB | yes |

**Measurement changed the design.** The first version of the check used ×1.25 alone, which does **not** cover 640×480 (2.0 MB required vs 2.3 MB measured): the 0.7–2.1 MB of fixed overhead dominates small images. A fixed +4 MB term was added. `MemoryPlanTest` now asserts the requirement covers every measured peak.

**Failure handling, under a real 48 MB heap:**
- 4000×3000 **refused before allocating** — "needs about 50.1 MB, 44.2 MB available … The image is not shrunk automatically, because that would change what the model sees."
- With the check bypassed, the `OutOfMemoryError` **was caught**, and the process then allocated 1 MB normally — no lasting damage.
- 30000×30000 refused by both guards (RGB would exceed the JVM array limit).

These are desktop-JVM figures. Android's ART allocator differs; the 1.25× + 4 MB margin is there for that. **DEVICE: NOT TESTED.**

### 2.4 A practical consequence for your phone

The Infinix NOTE 30 5G has a **108 MP** main camera. A full-resolution 12000×9000 frame needs ~324 MB of RGB and ~432 MB of native bitmap: **it will be refused**, with a message, rather than crash or be silently shrunk. Phones like this usually save a binned, lower-resolution image by default, but what yours delivers to `ACTION_IMAGE_CAPTURE` is **not verified** — test it on the device. If 108 MP refusal proves to be a real problem, supporting it needs a documented downsample with its own parity strategy; that is a decision, not a fix.

---

## 3. ResultActivity lifecycle and thread safety (§3)

### 3.1 Defects in v2 — all confirmed by reading the code

1. Raw `thread { }` re-ran the **entire pipeline on every rotation**.
2. `runOnUiThread` posted results to activities that might already be destroyed.
3. `onDestroy()` called `classifier.close()` while `forward()` could still be inside JNI on the worker — **freeing the native module underneath a running inference**. That is a native use-after-free: a crash, not an exception.
4. Nothing cancelled the work.
5. Found during the fix: if the screen is cleared **while the model is loading**, `onCleared()` sees no classifier, closes nothing, and the late-arriving native module **leaks**.

### 3.2 Design

| Component | Responsibility |
|---|---|
| `ResultViewModel` | Owns the pipeline; survives rotation; `start()` is idempotent → no duplicate inference |
| `repeatOnLifecycle(STARTED)` | UI collects state only while visible; cancelled on destroy → no updates to a dead activity |
| `InferenceGuard` | Serialises `forward()`; `close()` is non-blocking and **defers** destruction until a running `forward()` returns; destroys **exactly once**; refuses work after close |
| `OwnedResource` | Holds the classifier; a model that finishes loading **after** the owner closed is released immediately instead of leaked |
| Stage checks | `ensureActive()` between decode, load and inference stops remaining work early |
| Error mapping | `CancellationException` always rethrown first; memory, decode, model, OOM and unexpected errors each mapped to a distinct message |

A `forward()` already inside JNI cannot be interrupted — it runs to completion (~12 ms on this phone, measured in Phase 2). The guard is what makes that safe.

No new dependencies in substance: `lifecycle-runtime-ktx`, `lifecycle-viewmodel-ktx` and coroutines already arrive transitively through `activity-ktx`. They are now declared explicitly because the app calls them directly.

### 3.3 Tests — JVM-TESTED

`InferenceGuardTest`, 9 tests, real threads:

- `close()` during a 300 ms `forward()`: returned in **~0 ms**, released **0** times during, **1** time after
- 400 concurrent `close()` calls → **exactly 1** release
- 100 runs on 8 threads → never more than **1** inside `forward()`
- **200 randomised interleavings** of run/close → 0 releases during an active `forward()`, 0 double releases, 0 leaks
- an exception inside `forward()` does not block later release
- model arriving after close → released immediately; **500 load/clear races** → exactly one release every time

(A standalone harness ran the same scenarios at 500 interleavings: 11/11.)

`ViewModel`, `lifecycleScope` and `repeatOnLifecycle` themselves are **STATIC**.

---

## 4. ExecuTorch integration audit (§4)

| Check | Result |
|---|---|
| Asset filename | `agrishield_tomato4.pte` — matches exactly |
| Hash checked **before** `Module.load()` | yes — verified by source position |
| Expected hash | `f57f5ec3…37f4b` — the frozen artifact |
| Input tensor | `longArrayOf(1, 3, 96, 96)` |
| Normalisation | ImageNet mean/std, inside the unchanged verified file |
| Output class order | matches `models/agrishield_tomato4.json` exactly |
| Output validation | rejects non-tensor output and any logit count ≠ 4 |
| Softmax | max-subtracted, double precision — same as the Phase 2/3 runner |
| API calls | all seven against the published 1.5.x Java API: `Module.load`, `Tensor.fromBlob`, `EValue.from`, `forward`, `isTensor`, `toTensor`, `getDataAsFloatArray`; `destroy()` confirmed in the javadoc |
| Resource cleanup | `destroy()` reachable **only** through `InferenceGuard` |

**Fixed:**
- **Non-atomic asset copy.** A process death mid-copy left a truncated `.pte` that failed the hash check on every launch until the user cleared app data. Now copied to `.partial` and renamed.
- `Prediction` was a `data class` holding `FloatArray`s, which compare by reference. Now a plain class.
- `Classifier.create()` held the caller's `Context`; now uses the application context.
- Preprocessing time is now reported separately from `forward()` latency.

**Not claimed:** Android inference parity. The model has never loaded on Android.

---

## 5. Camera and gallery workflows (§5)

| Area | Finding | Status |
|---|---|---|
| `TakePicture` | No permission declared or requested — correct for `ACTION_IMAGE_CAPTURE` (fixed last round) | STATIC |
| **Process death during capture** | `pendingCaptureUri` lived only in a field. On a loaded phone Android often kills the app while the camera is in front; the photo was then reported "not captured" despite being saved. **Fixed:** path saved in instance state. | STATIC |
| Cancelled capture | Left an empty file in cache. **Fixed:** deleted. | STATIC |
| FileProvider | `cache-path "captures/"` matches the capture directory; `IllegalArgumentException` caught | STATIC |
| **`GetContent` URI** | Read grant not persistable; re-read across two screens. **Fixed:** byte-for-byte copy into private storage on selection — identical bytes, so identical model input. Size-capped at 200 MB, refuses if under 50 MB free. | STATIC |
| Cache growth | Phone is at 98 % storage. **Fixed:** copies older than 24 h purged on launch, never the pending capture. | STATIC |
| EXIF | Exact permutation; all 8 orientations | **JVM-TESTED** — 112/112 bit-exact vs Pillow |
| RGB conversion | Alpha dropped like Pillow; un-premultiplied decode | permutation JVM-TESTED; decode STATIC |
| No camera / no gallery | `ActivityNotFoundException` caught on both, with a message | STATIC |
| Main-thread work | Preview decode moved off the main thread | STATIC |

---

## 6. Gradle wrapper — now shipped, verified

A Gradle 8.14.3 installation was present in the build environment all along; I had not looked for one last round. Its own `wrapper` task, run offline in an empty directory, produced the official `gradlew`, `gradlew.bat` and `gradle-wrapper.jar`.

**SHA-256 `7d3a4ac4de1c32b59bc6a4eb8ecb8e612ccd0cf1ae1e99f66902da64df296172` matches Gradle's published 8.14.3 wrapper checksum exactly.** The properties file is byte-identical to the one already in the project, still naming Gradle 8.9. My hand-written launchers and `init_gradle_wrapper.bat` are removed.

---

## 7. Tests run

| Suite | Result | How |
|---|---|---|
| Project JUnit — `PreprocessUnitTest` | **8/8** | JUnit 4.13.2, OpenJDK 21 |
| Project JUnit — `OrientedRgbTest` | **6/6** | same |
| Project JUnit — `MemoryPlanTest` | **8/8** | same |
| Project JUnit — `InferenceGuardTest` | **9/9** | same |
| **Total project unit tests** | **31/31** | not via Gradle — Gradle needs the Android plugin |
| Orientation + full transform vs Pillow | **112/112** bit-exact | 7 geometries × 8 orientations × 2 strip sizes |
| Original Kotlin↔Pillow parity | **9/9** bit-exact | rebuilt from the app copy |
| Memory measurement, refusal, OOM recovery, overflow | all as expected | real `-Xmx` limits |
| Guard concurrency harness | **11/11** | 500 randomised interleavings |
| Mechanical audit of Android sources | **37/37** | binding IDs, API calls, ordering, manifest |
| `DecoderParityTest` (instrumented) | **not run** | needs the phone |
| Android app build | **not run** | no Android SDK / AGP reachable |

---

## 8. Erratum — Phase 3 preprocessing audit

A new test caught it. `PHASE3_PREPROCESSING_AUDIT.md` §3.2 (and `PHASE3_PROGRESS.md` §3.2) state:

| Aspect | Phase 3 says | torchvision actually gives |
|---|---|---|
| 4:3 | 145×109, **58.4 %** | 145×109, **58.3 %** (9216 / 15805 = 0.5831) |
| 16:9 | **194**×109, **43.6 %** | **193**×109, **43.8 %** (9216 / 21037 = 0.4381) |

torchvision computes the long side as `int(109 × long / short)` — **truncation**: 109 × 16/9 = 193.78 → 193. The Phase 3 table rounded.

**Impact:** none on any result. The pipeline itself was always correct (verified bit-exact against torchvision); only the explanatory table was off. The 60 % retention warning still flags both 4:3 and 16:9. The Phase 3 documents are **not edited** — they are earlier deliverables; correcting them is your call.

---

## 9. Remaining risks

1. **Nothing Android-specific has compiled.** Every framework call is STATIC. Expect some compile errors on the first Gradle run; they are normal and not evidence the design is wrong.
2. **JPEG decoder parity unmeasured.** The 9/9 and 112/112 results hold *given identical input pixels*. `DecoderParityTest` is written and waiting for the phone.
3. **108 MP captures will be refused.** What the camera actually delivers to the app is unverified.
4. **Colour-managed photos.** A non-sRGB-tagged image is converted by Android and not by Pillow. Detected and disclosed, not corrected.
5. **Desktop-JVM memory figures.** ART will differ; the margin is meant to absorb it.
6. **Laptop TLS.** The wrapper's 130 MB Gradle download is the first large transfer the build will attempt.
7. **Phone storage at 98 %.** Imports are capped and purged, but headroom is small.
8. **Still no real leaf photographs** — blocks Phase 3's milestone independently of all of this.

---

## 10. Files changed since v2

**Modified:** `app/build.gradle.kts`, `MainActivity.kt`, `PreviewActivity.kt`, `ResultActivity.kt`, `ml/Classifier.kt`, `ml/ImageLoader.kt`, `gradlew`, `gradlew.bat`
**Added:** `ResultViewModel.kt`, `ml/InferenceGuard.kt`, `ml/OwnedResource.kt`, `preprocess/MemoryPlan.kt`, `preprocess/OrientedRgb.kt`, `OrientedRgbTest.kt`, `MemoryPlanTest.kt`, `InferenceGuardTest.kt`, `gradle/wrapper/gradle-wrapper.jar`
**Removed:** `init_gradle_wrapper.bat`, `gradle/wrapper/README.txt`
**Unchanged, verified:** `AgriShieldPreprocess.kt`, `PreprocessUnitTest.kt`, `DecoderParityTest.kt`, manifest, layouts, resources
