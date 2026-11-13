# AGRI-SHIELD AI — Phase 3 Preprocessing Audit

**Date:** 31 October 2026
**Purpose:** recover the *exact* preprocessing the trained model expects, from source, before any real-image code is written.
**Method:** read the actual training, inference and external-evaluation code off the laptop. Nothing below is inferred from documentation or from memory of earlier sessions.

---

## 1. Result — the transform is fully recovered and unambiguous

The evaluation-time transform appears in **three independent places** in the codebase and is **identical in all three**:

| File | Line | Role |
|---|---|---|
| `disease_detection/training/train.py` | 167–171 | `eval_tf`, used for the val and test loaders |
| `disease_detection/inference/predict.py` | 53–59 | `preprocess()`, used for single-image prediction |
| `disease_detection/evaluation/external_eval.py` | 84–87 | PlantDoc external evaluation |

The transform:

```python
transforms.Compose([
    transforms.Resize(int(img_size * 1.14)),   # img_size = 96  →  Resize(109)
    transforms.CenterCrop(96),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])
```

Image loading, identically in all three:

```python
with Image.open(path) as im:
    x = tf(im.convert("RGB"))
```

`int(96 * 1.14)` evaluates to **109** exactly (96 × 1.14 = 109.44, truncated). `img_size = 96` is confirmed independently by `models/agrishield_tomato4.json` and by the training run record `metrics.json`.

**No preprocessing detail is unresolved.** There is nothing in this pipeline that had to be guessed.

---

## 2. The transform, step by step

| # | Operation | Exact behaviour |
|---|---|---|
| 1 | `Image.open(...).convert("RGB")` | PIL decode, forced to 3-channel RGB. Palette/grayscale/RGBA all collapse to RGB. Channel order is **RGB, not BGR**. |
| 2 | `Resize(109)` | A **single int**, so the **shorter side** becomes 109 and the longer side scales proportionally — aspect ratio is preserved. Interpolation is torchvision's default, `InterpolationMode.BILINEAR`. For a PIL input this calls `img.resize((ow, oh), PIL.Image.BILINEAR)`, which is Pillow's antialiased convolution resampler on downscale. |
| 3 | `CenterCrop(96)` | Crops the central 96 × 96. Offsets are `int(round((dim - 96) / 2))`. |
| 4 | `ToTensor()` | HWC uint8 [0, 255] → CHW float32 [0, 1], i.e. divide by 255. |
| 5 | `Normalize(mean, std)` | `(x - mean) / std` per channel, ImageNet constants: mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]`. |

Final tensor: **`[1, 3, 96, 96]`, float32, NCHW**, channel order **R, G, B**.

Approximate value range after normalisation: R ∈ [−2.118, 2.249], G ∈ [−2.036, 2.429], B ∈ [−1.804, 2.640].

### Class order — confirmed, do not reorder

From `models/agrishield_tomato4.json`, matching the training manifest:

| Index | Class |
|---|---|
| 0 | `Tomato___Early_blight` |
| 1 | `Tomato___Late_blight` |
| 2 | `Tomato___Septoria_leaf_spot` |
| 3 | `Tomato___healthy` |

### The training-time transform differs, and correctly so

`train_tf` applies `RandomResizedCrop(96, scale=(0.7, 1.0))`, horizontal and vertical flips, and `ColorJitter(0.2, 0.2, 0.2, 0.05)`. These are **augmentations and must not be applied at inference.** The frozen Phase 1 test metrics were produced with `eval_tf`, so `eval_tf` is the only correct choice here.

---

## 3. Two issues this audit uncovered

Both are consequences of a pipeline built for PlantVillage being pointed at phone photographs. Neither is a defect in the training code.

### 3.1 EXIF orientation is never applied — a real gap for camera images

None of the three code paths calls `ImageOps.exif_transpose`. `Image.open().convert("RGB")` ignores the EXIF `Orientation` tag entirely.

This was **harmless for training**: PlantVillage images are pre-cropped 256 × 256 files with no EXIF orientation, so the tag is absent and there is nothing to apply.

It is **not harmless for phone photographs.** The Infinix camera writes an `Orientation` tag rather than rotating pixels. A portrait photo decoded without EXIF handling arrives rotated 90°, and the center crop then selects an entirely different region of the leaf.

**Decision: apply `ImageOps.exif_transpose` in the Phase 3 pipeline, and declare it.** The justification is that it is a **no-op on the training distribution** (no EXIF orientation present) while making camera input match the upright convention the model was actually trained on. This is a deliberate, documented deviation — it is recorded here rather than made silently, and it is the only deviation in the pipeline.

### 3.2 Center-cropping a phone photo discards a large part of the frame

`Resize(109)` + `CenterCrop(96)` keeps 96/109 ≈ 88 % of the **shorter** dimension, but on the longer dimension it keeps only `96 / (109 × aspect)`.

| Source aspect | Size after `Resize(109)` | Fraction of frame retained |
|---|---|---|
| 1:1 (PlantVillage) | 109 × 109 | **77.6 %** |
| 4:3 phone photo | 145 × 109 | **58.4 %** |
| 16:9 phone photo | 194 × 109 | **43.6 %** |

On PlantVillage this is immaterial — the leaf fills a square frame with a uniform background, so the discarded border is background. On a 16:9 phone photo, **more than half the image is thrown away before the model sees anything**, and any lesion outside the central square is invisible to the classifier.

The brief says: *"Do not silently crop away disease symptoms."* The pipeline therefore:

- applies the **exact** training transform (fidelity to the model is non-negotiable);
- **computes and records, per image, the retained-area fraction** into the manifest, so cropping is visible in the record rather than hidden;
- **warns** when retention falls below 60 %;
- **preserves every original photograph** untouched alongside the tensors.

The practical mitigation is in how photographs are taken, not in altering the transform: **frame the leaf centrally and fill the frame**, square (1:1) if the camera offers it. Changing the transform to pad-instead-of-crop would be a silent mismatch with training and is not done.

---

## 4. Runner input format — already compatible

The Phase 2 Arm runner (`agrishield_bench`) reads a binary file:

```
int32  n_images
int32  C          (3)
int32  H          (96)
int32  W          (96)
float32[n_images * 3 * 96 * 96]    NCHW, little-endian
```

This is exactly what a real-image tensor batch needs. **The runner requires no change to accept photographs** — the synthetic validation path and the real-image path produce the same file format, so the verified binary is reused untouched and the synthetic validation mode cannot be broken by Phase 3 work.

One additive change is required for the brief's per-image reporting (§5 asks for latency *per image*): the runner currently times a loop that cycles inputs, giving an aggregate distribution rather than per-image figures. A per-image timing capture is added to the existing logit pass. This does not alter the synthetic path, the timed loop, or the output of either — and is re-validated against `desktop_reference.json` before use.

---

## 5. Verification status

| Claim | How established |
|---|---|
| Transform constants and order | **Read from source**, three independent sites, all identical |
| `img_size = 96` | Confirmed in `agrishield_tomato4.json` *and* `metrics.json` |
| Class order | Confirmed in `agrishield_tomato4.json` |
| RGB (not BGR) | `im.convert("RGB")` in all three paths |
| `Resize` semantics for a single int | torchvision: shorter side → size, aspect preserved |
| Interpolation = BILINEAR | torchvision default; PIL path uses antialiased resampling |
| Pipeline reproduces torchvision bit-exactly | **See `phase3/preprocess_verification.json`** — the Phase 3 implementation is compared directly against `torchvision.transforms` on identical inputs |

---

## 6. Unresolved items

None affecting correctness of the transform.

Two things remain outside this audit's scope and are tracked in `PHASE3_BLOCKERS.md`:

- **No real tomato leaf photographs are available yet.** The laptop's `datasets/` directory holds only `metadata/split_summary.json`; the PlantVillage images lived in the Phase 1 container, which no longer exists.
- **Domain shift is a known, measured limitation.** The PlantDoc external evaluation gave 0.3914 accuracy and 0.3629 macro-F1 against 0.9562 in-domain. Any prediction on a real photograph must be presented as a model output, never as a diagnosis.
