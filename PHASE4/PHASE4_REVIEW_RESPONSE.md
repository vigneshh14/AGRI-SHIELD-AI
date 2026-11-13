# AGRI-SHIELD AI — Response to Phase 4 Review

**Date:** 31 October 2026 · Bundle: `PHASE4_android_v2.zip`
**Nothing has been compiled. No APK exists. Nothing has run on the phone. No download or installation has been performed.**

---

## 1. Gradle wrapper — `gradlew`, `gradlew.bat` added; JAR explained, not faked

`gradlew` and `gradlew.bat` are now included. They are minimal but functionally correct launchers whose only job is to run `org.gradle.wrapper.GradleWrapperMain` from the wrapper JAR, with clear diagnostics when Java or the JAR is missing.

**`gradle-wrapper.jar` is still absent, deliberately.** It is a ~43 KB binary. `services.gradle.org` and Maven Central are both unreachable from the environment this project was prepared in, so I could neither download it nor verify a checksum for it. Shipping an unverified binary, or inventing a checksum, would be worse than its absence.

You were right that I should not have assumed Android Studio regenerates it. Three routes are now documented, two needing no extra download:

| Route | Download | Notes |
|---|---|---|
| **A** `init_gradle_wrapper.bat` | ~43 KB | PowerShell fetch, then **structural verification** — must open as a ZIP and contain `GradleWrapperMain.class`, else the file is deleted. Prints its SHA-256 for your own comparison. |
| **B** Android Studio with a specified Gradle location | none | The wrapper is never consulted. Lowest risk given your laptop's TLS record today. |
| **C** `gradle wrapper --gradle-version 8.9` | none extra | Writes the **official** wrapper files, overwriting mine. Expected and correct. |

`gradle/wrapper/README.txt` states the same in the tree itself.

---

## 2. BUILD_INSTRUCTIONS.md — rewritten

New §3 covers the three wrapper routes above. The claim "Android Studio generates it on first sync" is removed. §2 now gives the model path explicitly and says the build will not work without it. §3.1 separates the build step.

**I cannot call any of this "tested."** It is technically correct and internally consistent; it has not been executed, because no toolchain exists on either machine.

---

## 3. `__pycache__` removed

`parity/__pycache__/pil_algo.cpython-313.pyc` found and deleted. The new archive is built with explicit `-x "*__pycache__*" "*.pyc"` and verified to contain **0** such entries.

---

## 4. ExecuTorch API signatures — confirmed against published docs

| Call in `Classifier.kt` | Status |
|---|---|
| `Module.load(String)` | confirmed — official Android example |
| `Tensor.fromBlob(float[], long[])` | confirmed — official Android example |
| `EValue.from(Tensor)` | confirmed — `EValue` javadoc, static `from(Tensor)` |
| `module.forward(EValue...)` → `EValue[]` | confirmed — official example indexes `[0]` |
| `EValue.isTensor()` | confirmed — `EValue` javadoc method summary |
| `EValue.toTensor()` | confirmed — `EValue` javadoc |
| `Tensor.getDataAsFloatArray()` | confirmed — official example |
| `Module.destroy()` | **confirmed** — javadoc index lists `destroy()` on `org.pytorch.executorch.Module` |

`destroy()` was the one I was unsure of, and it was worth checking: a missing method is a compile error, which `try/catch` does not rescue.

**Change made:** Kotlin synthetic property access (`.isTensor`, `.dataAsFloatArray`) replaced with explicit Java calls (`.isTensor()`, `.getDataAsFloatArray()`), so the code reads line-for-line against the published API.

---

## 5. Camera / gallery / EXIF / FileProvider — two real bugs found and fixed

### 5.1 Camera capture could never have worked

`MainActivity` requested `android.permission.CAMERA` at runtime, but the manifest declared no such permission. Android returns **denied immediately** for an undeclared permission, so the capture button was dead.

**Fix:** the permission request is removed entirely. `ActivityResultContracts.TakePicture` dispatches `MediaStore.ACTION_IMAGE_CAPTURE`, which requires `CAMERA` **only if the app declares it** — and declaring it would make the runtime grant mandatory. Not declaring it is both simpler and correct. A comment in the source records why, so it is not "helpfully" reintroduced.

### 5.2 A 12 MP photograph would likely have run the app out of memory

The old path, for a 4000×3000 image:

| Allocation | Size |
|---|---|
| ARGB_8888 bitmap | ~48 MB |
| `IntArray(w*h)` in `toRgb` | ~48 MB |
| Full bitmap retained for display, loaded twice | ~48 MB again |

That is ~130 MB peak against a typical ~256 MB heap, on a phone that had **110 MB free RAM** when measured in Phase 2.

**Fixes:**
- `toRgb` now reads **256-row strips**, so extra allocation is bounded (~4 MB) regardless of image size.
- `load()` returns a **display-only thumbnail** (longest edge 1024) and recycles the full bitmap immediately. `createScaledBitmap` is used for that thumbnail — and **only** there, with a comment stating it never reaches the model.
- `OutOfMemoryError` on decode is caught and reported as a readable message.

### 5.3 Other hardening in the same pass

- Missing-EXIF is treated as `ORIENTATION_NORMAL`, not an error — most gallery images have no orientation tag.
- `FileProvider.getUriForFile` wrapped: `IllegalArgumentException` means `file_paths.xml` does not cover the directory, which is now reported rather than crashing.
- Gallery and camera launches wrapped for "no app available" on a device without either.
- `FLAG_GRANT_READ_URI_PERMISSION` forwarded to our own activities.
- Unused `MediaStore` / `Activity` imports removed.
- `file_paths.xml` confirmed to match the capture directory (`cache-path` ↔ `File(cacheDir, "captures")`).

**Not fixed, flagged instead:** the `GetContent` URI is re-read in `ResultActivity`. The read grant is held by the app's UID so this works in practice, but it is not persistable (`GetContent` does not support `takePersistableUriPermission`). If the process is killed between screens the URI could become unreadable. Risk 4 below.

---

## 6. Model asset — intentionally excluded, path stated

Excluded on purpose: 8.9 MB, and the Phase 1 archive is the single authoritative copy. Duplicating it invites silent drift.

```
from:  C:\Users\VIGNESH\Documents\AGRI_SHIELD_AI\models\agrishield_tomato4.pte
to:    android_app\app\src\main\assets\agrishield_tomato4.pte
```

Filename must match exactly — `Classifier.ASSET_NAME`. `assets/MODEL_GOES_HERE.txt` repeats this in the tree. The app hash-checks it at startup and refuses to run on mismatch. A missing model produces a clear error naming the file, not a crash.

---

## 7. AAR size — my estimate was wrong by ~6×

I estimated 40–70 MB. Published Maven Central listings give:

| Artifact | Published size |
|---|---|
| `executorch-android-1.3.0.aar` | **7,176,139 bytes** (6.84 MiB) |
| `executorch-android-1.3.1.aar` | **7,177,348 bytes** (6.85 MiB) |

Two consecutive releases within 1.2 KB of each other, so the figure is stable. **1.5.1 is expected around 7 MB**; I could not read its listing directly, so the report states ~7–12 MB and says to confirm at download time.

The error came from assuming two ABIs of unstripped kernel libraries. Corroboration that it was too high: a third-party repackaging ships `core-android-arm64-v8a` at 4.49 MB.

**Knock-on correction:** total Gradle dependencies drop from "60–90 MB" to **~25–40 MB**. The toolchain total barely moves (~1.8–2.0 GB) because Android Studio and the SDK dominate by two orders of magnitude.

---

## 8. Verified preprocessing and tests — preserved

`AgriShieldPreprocess.kt` in the app is **byte-identical** to the 9/9-verified file:

```
SHA-256  45dee236610aec19446d32227597ff12fc75049b4b50fd66f64b2a14c4cfc218
```

Both test files are intact: `PreprocessUnitTest.kt` (8 JVM tests) and `DecoderParityTest.kt` (3 instrumented tests). The unit test's hard-coded expectations were re-verified by **executing** the compiled Kotlin: resize 4000×3000 → 145×109, centre-crop offset 6, `int(96×1.14)` = 109.

One fix in `DecoderParityTest.kt`: `?: fail(...).let { return }` does not type-check, since `fail()` returns `void`. Replaced with `assertNotNull` plus an explicit non-null assertion.

---

## Remaining risks

1. **Nothing compiles yet.** No toolchain on either machine; both download hosts blocked here. Until Gradle actually runs, every file in this bundle is unexercised except the preprocessing, which was compiled and run on a JVM.
2. **Android JPEG decoder parity is unmeasured.** The 9/9 result holds *given identical input pixels*. Whether `BitmapFactory` decodes a JPEG to the same bytes as Pillow is untested — the test is written and waiting for a device.
3. **Your laptop's TLS.** It truncated a 100 MB download today. Android Studio is ~1.2 GB. Resumable, but expect repeated attempts. Wrapper Route B avoids adding a further download.
4. **`GetContent` URI not persistable.** Works in practice within one app session; could fail if the process is killed between Preview and Result. Fix if seen: copy the image into app cache on selection.
5. **Phone storage at 98 %** (5.8 GB free) alongside Termux and Debian. APK is ~60–80 MB, so not blocking, but tight.
6. **Still no real leaf photographs.** Blocks Phase 3's milestone independently of the APK, and means the app can only be demonstrated on whatever image is to hand.
7. **UI is unrendered.** The four layouts have never been inflated. Expect cosmetic adjustment on first run — that is normal, and distinct from the functional issues above.
