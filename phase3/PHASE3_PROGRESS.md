# AGRI-SHIELD AI — Phase 3 Progress

**Updated:** 31 October 2026, 12:50 local
**Objective:** run the trained model on **real tomato leaf photographs** on the physical Infinix NOTE 30 5G
**Status:** pipeline complete and verified. **Blocked on photographs — nothing else.**

---

## 1. Where this stands

Everything that can be built without photographs is built, and verified rather than assumed:

| Item | Status |
|---|---|
| Preprocessing recovered from source | **DONE** — three call sites, all identical, nothing guessed |
| Preprocessing implementation | **VERIFIED BIT-EXACT vs torchvision** — 9 geometries, max diff 0.0 |
| Runner extended for per-image latency + probabilities | **DONE** |
| Extended runner, x86_64 regression | **8/8 bit-identical** vs frozen `desktop_reference.json` |
| Extended runner, aarch64 regression | **8/8 bit-identical** vs frozen reference |
| Tensor format compatibility | **UNCHANGED** — synthetic validation path cannot break |
| Real photographs | **BLOCKED — none available** |
| Inference on real images on the phone | **NOT STARTED** — needs photographs |

**The primary success condition is not met and is not claimed.** A synthetic tensor test does not satisfy it; the brief says so explicitly, and I agree.

---

## 2. The preprocessing audit — nothing was guessed

The transform appears in three independent places (`train.py` `eval_tf`, `predict.py` `preprocess`, `external_eval.py`) and is **identical in all three**:

```
Resize(109)        # int(96 * 1.14), shorter side, aspect preserved, BILINEAR
CenterCrop(96)
ToTensor()         # HWC uint8 [0,255] -> CHW float32 [0,1]
Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
```

Loading is `Image.open(path).convert("RGB")` — RGB, not BGR. Output `[1,3,96,96]` float32 NCHW. Class order confirmed from `agrishield_tomato4.json`.

**No preprocessing detail was unrecoverable.** Full provenance in `PHASE3_PREPROCESSING_AUDIT.md`.

### Verified, not believed

The Phase 3 implementation uses PIL directly rather than torchvision, so that it stays dependency-light. That makes "I replicated torchvision correctly" a claim requiring proof, not an assumption. So torchvision was installed and the two compared head-to-head on nine geometries — 640×480, 4000×3000, 1920×1080, 256×256, 109×109, 97×96 and others:

**Maximum absolute difference: 0.000e+00. Bit-exact on every case.** Recorded in `phase3/preprocess_verification.json`.

---

## 3. Two findings from the audit

### 3.1 EXIF orientation was never handled — and matters now

None of the three training/inference paths calls `ImageOps.exif_transpose`. That was **harmless for training**: PlantVillage files carry no EXIF orientation tag.

It is **not harmless for phone photographs.** The Infinix camera writes an orientation tag rather than rotating pixels, so a portrait photo would reach the model rotated 90° and the centre crop would select the wrong region entirely.

**Decision: apply EXIF transpose, and declare it.** It is a no-op on the training distribution and corrects camera input to the upright convention the model was trained on. This is the pipeline's only deviation from the literal training code, it is documented, and it is recorded per-image in the manifest.

### 3.2 Centre-cropping a phone photo throws away most of the frame

`Resize(109)` + `CenterCrop(96)` keeps the central square. The cost depends entirely on aspect ratio:

| Source | After resize | Frame retained |
|---|---|---|
| 1:1 (PlantVillage) | 109 × 109 | **77.6 %** |
| 4:3 phone photo | 145 × 109 | **58.4 %** |
| 16:9 phone photo | 194 × 109 | **43.6 %** |

On PlantVillage the discarded border is uniform background. On a 16:9 photo **more than half the image never reaches the model**, and a lesion outside the central square is invisible to it.

The brief forbids cropping symptoms away silently. So the transform is applied **exactly** — fidelity to the model is not negotiable — but the pipeline **computes and records the retained-area fraction for every image**, flags anything under 60 %, and preserves every original untouched. The mitigation belongs in how photographs are framed, not in altering the transform.

---

## 4. Runner change, and why it is safe

The brief asks for latency *per image*. The existing timed loop cycles inputs and yields an aggregate distribution, which cannot give that.

The change is **additive**: the existing logit-capture pass — which already runs each image exactly once — is now timed, and a `per_image` block is emitted carrying index, latency, softmax probabilities, top-1 and top-2, and the decision margin. The timed loop, the logits, the input format and the synthetic path are untouched.

Proof that nothing broke: both rebuilt binaries were run against the **frozen** `desktop_reference.json` and both returned **8/8 bit-identical** logit vectors.

The tensor file format is unchanged, so real-image tensors and synthetic validation tensors are interchangeable inputs to the same verified binary.

---

## 5. What is ready and waiting

- `phase3/preprocess_images.py` — EXIF correction, exact transform, dimension and dtype validation, per-image crop accounting, originals preserved, manifest with **blank label columns** (a label must come from the photographer, never from the prediction)
- `phase3/run_real.sh` — one command on the phone; re-checks the model hash and refuses to run on a mismatch
- Updated `agrishield_bench`, cross-compiled and regression-checked
- `phase3/preprocess_verification.json` — the torchvision parity evidence

---

## 6. Honest expectations before we run

The PlantDoc external evaluation measured **0.3914 accuracy** on real-world images against **0.9562** in-domain. The model was trained from random initialisation on lab photographs of detached leaves against uniform backgrounds.

**Real photographs may well be misclassified.** That would be a finding — on-device corroboration of a domain-shift limitation already documented in Phase 1 — not a failure of this phase. What would be dishonest is presenting whatever the model outputs as correct.

Predictions will be recorded as **model predictions, never diagnoses**. No pesticide names, doses or treatment schedules will be issued; the knowledge base still holds **0 source-verified chemical records**.

---

## 7. Next action

**Photographs.** Details and shooting guidance in `PHASE3_BLOCKERS.md` §B1. Even one real leaf photo satisfies the milestone; twenty makes it a result.

---

## 8. Integrity

Phase 1 archive untouched. Phase 2 results untouched — the new synthetic runs went to separate files and the frozen reference was used read-only, as a regression oracle. Model not retrained, replaced, quantized or modified. No photographs or labels fabricated. No native Android claim. No Llama work.
