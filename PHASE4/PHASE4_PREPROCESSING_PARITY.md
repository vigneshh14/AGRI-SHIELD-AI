# AGRI-SHIELD AI — Kotlin / Python Preprocessing Parity Report

**Date:** 31 October 2026
**Stage:** Phase 4, Stage 1, items 1–5
**Result:** **9 / 9 cases bit-exact. Worst max absolute difference 0.000000e+00.**

---

## 1. Why this had to be done first

The Android app must feed the model the same numbers the Python pipeline does, or every verified result in this project stops applying to it.

The obvious Android approach — `Bitmap.createScaledBitmap(src, w, h, filter = true)` — **is not equivalent to Pillow**, and the gap is not small. Android's bilinear samples a 2×2 neighbourhood with no pre-filtering. Pillow's `BILINEAR` scales its filter support by the downscale factor, so it antialiases. A 4000×3000 photo resized to 145×109 is a ~27× downscale: Android reads roughly one pixel in 700.

Measured on the final normalised tensor, whose full range spans about 4.4:

| Content | max abs diff | mean abs diff | RMS |
|---|---|---|---|
| **Leaf-like texture (high frequency)** | **0.8235** | 0.0923 | 0.1263 |
| Smooth gradient (low frequency) | 0.0128 | 0.0002 | 0.0011 |

The error is content-dependent and lands hardest on exactly the high-frequency detail that lesions consist of. A naive port would have silently changed predictions. **`createScaledBitmap` is therefore not used anywhere in this project.**

---

## 2. What was built

`AgriShieldPreprocess.kt` reimplements Pillow's `ImagingResample` for 8-bit RGB with the `BILINEAR` filter, including its **fixed-point integer arithmetic** rather than a floating-point approximation of it:

```
PRECISION_BITS = 32 - 8 - 2 = 22
coefficients rounded to Int at that scale (normalize_coeffs_8bpc)
accumulator seeded with 1 shl (PRECISION_BITS - 1)   // round-to-nearest
output = (acc shr PRECISION_BITS), clamped to 0..255
horizontal pass first -> 8-bit intermediate -> vertical pass
```

Then the rest of the Phase 3 transform: `Resize(109)` on the shorter side with aspect preserved, `CenterCrop(96)`, `ToTensor()`, `Normalize(ImageNet)`, producing `[1,3,96,96]` float32 NCHW, RGB.

The algorithm was first reimplemented in Python and checked against Pillow directly (`pil_algo.py`): **bit-exact across six geometries, zero differing pixels**. Only then was it ported to Kotlin.

---

## 3. The bug the test caught

The first parity run failed on **every case**, including `exact_109` — a 109×109 input that needs no resizing at all. That localised the fault away from the resampler and into the crop.

Cause: torchvision computes crop offsets with Python's `int(round(x))`, which is **round-half-to-even** (banker's rounding). Kotlin/Java's `Math.round` is **round-half-up**.

```
Python round(6.5)      = 6        Java Math.round(6.5)  = 7
Python round(24.5)     = 24       Java Math.round(24.5) = 25
                                  Java Math.rint(6.5)   = 6.0   <- matches
```

For a 109 → 96 centre crop the offset is **exactly 6.5 on every image**, so the Kotlin crop was shifted one pixel vertically and horizontally — every time, for every photograph.

`Math.rint` is half-to-even and matches Python. One-line fix, and the comment in the source says not to "simplify" it back.

**This is the entire justification for the parity test.** The bug is invisible to inspection, produces a plausible-looking image, and would have quietly degraded every on-device prediction. No amount of code review would reliably have caught it; one test did, immediately.

---

## 4. Results after the fix

Python side: Pillow + the verified Phase 3 transform.
Kotlin side: `AgriShieldPreprocess.kt`, compiled by **K2JVMCompiler** and executed on **OpenJDK 21**. Both sides consume byte-identical source pixels.

| Case | Source | max abs diff | mean abs diff | RMS | Verdict |
|---|---|---|---|---|---|
| leaf_4000x3000 | 4000×3000 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| leaf_3000x4000 | 3000×4000 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| leaf_1920x1080 | 1920×1080 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| square_1024 | 1024×1024 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| noise_640x480 | 640×480 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| noise_480x640 | 480×640 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| small_109x140 | 109×140 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| tiny_97x96 | 97×96 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |
| exact_109 | 109×109 | 0.000e+00 | 0.000e+00 | 0.000e+00 | **BIT-EXACT** |

**9 / 9 bit-exact. Worst max absolute difference across all 248,832 tensor values: 0.000000e+00.**

Cases were chosen to exercise the failure modes: both phone orientations, 16:9, square, pure noise (worst case for aliasing), inputs needing no resize, and inputs smaller than the crop.

Machine-readable record: `parity/kotlin_parity_report.json`.

---

## 5. What is verified, and what is not

**Verified:**

- The Kotlin resampler reproduces Pillow's antialiased BILINEAR exactly, integer arithmetic included.
- Resize, centre crop, `ToTensor` and `Normalize` all match to the last bit.
- Tensor shape, dtype, layout (NCHW) and channel order (RGB) match.
- Compiled by a real Kotlin compiler and executed on a real JVM — not reasoned about on paper.

**Not yet verified — stated plainly:**

- **The Android image decoder is not in this test.** The harness feeds raw RGB bytes, so it isolates the arithmetic. On-device, `BitmapFactory` decodes the JPEG, and Android's decoder may not produce byte-identical pixels to Pillow's for the same file — JPEG decoding has implementation freedom in upsampling and IDCT. **This is the one remaining link in the chain, and it must be tested on the device with a real photograph.** Until then, "bit-exact preprocessing" means bit-exact *given identical input pixels*.
- **EXIF orientation is not in this test.** It is a lossless transpose/flip, so it carries no numerical risk, but the Android `ExifInterface` path still needs an on-device check.
- **Nothing has run on the phone.** No APK exists. This is JVM-side verification only.

A device-side decoder parity test is the first item in the Stage 2 plan: push one real JPEG, decode it both ways, compare.

---

## 6. Files

| File | Purpose |
|---|---|
| `parity/AgriShieldPreprocess.kt` | The Kotlin implementation — ships in the app |
| `parity/pil_algo.py` | Python reimplementation of Pillow's resampler, used to validate the algorithm before porting |
| `parity/parity_test.py` | The harness |
| `parity/kotlin_parity_report.json` | Machine-readable results |

Phase 1 archive, Phase 2 evidence and the trained model are untouched.
