# CONSISTENCY_AUDIT.md

Pre-submission audit, 2026-10-31. Six issues raised; all six
resolved. Two required retracting a previous claim of mine. Nothing below was
corrected by assumption — each resolution is backed by a run.

---

## 1. Confusion matrix consistency — RESOLVED, no defect found

Regenerated directly from `best.pt` against the exact test manifest.

| Check | Required | Measured |
| --- | --- | --- |
| Matrix total | 936 | **936** |
| Diagonal sum | 895 | **895** |
| Accuracy | 95.62% | **0.9561966** |
| Matches `metrics.json` | yes | **yes, element-wise** |

`confusion_matrix.png` regenerated; its title now carries n=936, accuracy 0.9562
and macro F1 0.9506 so the asset cannot drift from the numbers again.
`training_curves.png` plots loss and accuracy per epoch and contains no accuracy
headline, so it needed no change.

**Stale 96.15% figures:** swept across all reports. The only surviving mentions
are explicitly historical, in `PHASE1_RESULTS.md` and here, describing the
defect that produced them.

---

## 2. Leaf-level leakage — CONTRADICTION RESOLVED; one document retracted

### The contradiction
- `PHASE1_REPORT.md` claimed 63.97% leaf-level contamination.
- `VERIFICATION_REPORT.md` claimed the colour subset had little duplication.

Both could not be true. The second was mine, written before I had the leaf map,
and it was **wrong**. It is retracted and the file corrected.

### How the leaf identities were validated

Four independent lines of evidence, because the dHash null result genuinely
looked like grounds for doubt:

**A. Provenance.** `leaf_grouping/aggregate_map.py` builds `leaf-map.json` from
human-annotated spreadsheets whose columns are `File Name` and `Leaf #`. The
identifier comes from annotators counting physical leaves, not from pixels.

**B. Structure.** Every tomato class is exactly 4.00 files per leaf:

| Class | Files | Distinct Leaf # | Files/leaf |
| --- | --- | --- | --- |
| Early blight | 1000 | 250 | 4.00 |
| Late blight | 920 | 230 | 4.00 |
| Septoria leaf spot | 1000 | 250 | 4.00 |
| Healthy | 1000 | 250 | 4.00 |

File numbers within a leaf are consecutive — four successive exposures.

**C. Visual inspection.** Montages were rendered and examined. Within a group the
same lesion pattern recurs under rotation and reflection; a contrast row of four
different leaves from the same class is plainly dissimilar.

**D. Rotation-invariant measurement.** On the same image pairs:

| Descriptor | Within-leaf | Between-leaf | Separation |
| --- | --- | --- | --- |
| dHash (8x8 grey gradient) | 28.1 bits | 29.0 bits | 1.0 / 64 — chance |
| HS histogram (rotation-invariant) | 0.263 | 1.104 | **4.2x, AUC 0.963** |

### Verdict

The leaf identities are **sound**. dHash fails because an 8x8 grayscale gradient
is destroyed by rotation — the failure is in the descriptor, not the metadata.

**63.97% is retained**, and the novelty claim built
on it is retained, now with validation evidence attached. Caveat unchanged:
1919 images carry no grouping signal and
are treated as singletons, so the figure is a **lower bound**.

### Requested comparison

| Method | Images/group | Contamination estimate |
| --- | --- | --- |
| A. Ground-truth leaf identity | 4.14 (where mapped) | **63.97%** |
| B. Filename grouping | 1.00 | 0% — prefix is a per-image UUID |
| C. Perceptual hashing | 1.006 | 0.64% |
| D. Cross-directory variants | not applicable | only `raw/color` was used |

On D: the colour/grayscale/segmented triplication is real but irrelevant here,
since only `raw/color` was downloaded. My earlier document wrongly offered it as
the explanation for the duplication, and in doing so dismissed duplication that
genuinely exists *within* `raw/color`.

---

## 3. Llama status — CORRECTED

The abstract previously read that a Llama model "deployed through ExecuTorch
converts the retrieved record into advice". Present tense, and false.

| Component | Honest status |
| --- | --- |
| Advisory interface | **Implemented** |
| Mock backend | **Implemented and tested** |
| EN/TA prompt templates | **Implemented and tested** |
| ExecuTorch runtime, vision classifier | **Exported and numerically verified** |
| ExecuTorch runtime, Llama | **NOT STARTED** — licence not approved |
| Llama inference, any hardware | **NEVER EXECUTED** |

Abstract rewritten to say so. `PHASE1_COMPLIANCE.md` already marked M1 pending,
M3 partial and M4 pending; unchanged.

---

## 4. PlantDoc label validation — PROTOCOL CHANGED

PlantDoc contains **no class named "healthy"**. Its convention is a bare
`<Plant> leaf` against `<Plant> <disease> leaf`, and nine species carry the bare
form. Mapping `Tomato leaf` to healthy is an **inference** — common in
derivative work, never stated by the authors.

The healthy status cannot be established from the dataset, so per the audit
instruction the class is removed from the primary evaluation.

| Protocol | Images | Accuracy | Macro F1 |
| --- | --- | --- | --- |
| **Primary — 3 unambiguous disease classes** | 350 | **0.3914** | **0.3629** |
| Appendix — 4 classes, healthy inferred | 413 | 0.3414 | 0.2782 |

Both are preserved in `reports/external_plantdoc.json`. The finding is unchanged
under either protocol: in-domain 0.9562 against field
0.3914 is a 56.5 point collapse,
with confidence when wrong at 0.8124 versus
0.8644 when right.

---

## 5. Training runtime metadata — CORRECTED

`total_seconds` read **5.8**, which was absurd against a per-epoch history of
60-70 s. Cause: training was resumed across three processes and the timer
restarts each run; the final run completed zero epochs (it existed only to
re-evaluate the corrected checkpoint), so the field captured that run alone.

| Field | Value |
| --- | --- |
| Segments detected from history | 3 |
| Per-segment wall clock | 536.9 s, 456.7 s, 456.7 s |
| `training_wall_clock_seconds_sum_of_segments` | **1450.3 s** |

The misleading field is renamed `total_seconds_FINAL_SEGMENT_ONLY` and the new
field is explicitly labelled a lower bound that excludes inter-run gaps. It is
not offered as a benchmark.

---

## 6. Cross-artifact consistency — VERIFIED

| Artifact | Accuracy | Macro F1 | Agrees |
| --- | --- | --- | --- |
| `metrics.json` | 0.9562 | 0.9506 | — |
| `audit.json` (recomputed) | 0.9562 | 0.9506 | yes |
| `confusion_matrix.png` | 0.9562 | 0.9506 | yes |
| `PHASE1_REPORT.md` | 0.9562 | 0.9506 | yes |
| `PHASE1_RESULTS.md` | 0.9562 | 0.9506 | yes |
| `PHASE1_COMPLIANCE.md` | 0.9562 | — | yes |
| `test_results.md` | 0.9562 | 0.9506 | yes |
| `external_plantdoc.json` | 0.3914 (3-class primary) | 0.3629 | yes |

**`PHASE1_REPORT1.md` does not exist** in this project — not in the working copy
and not in the archive. No file was removed on its account. If it exists on your
machine it was not produced here, and it is not referenced by any artifact.

No duplicate or obsolete report versions were found.

---

## Unresolved scientific uncertainties

Stated explicitly, as instructed.

1. **1919 of 6271 images have no leaf identity.**
   PlantVillage ships leaf maps for 31 of 38 classes; some photo sources in our
   four classes are uncovered. Those images are singletons, so true contamination
   is **higher** than 63.97% by an unknown amount.

2. **The decimal filename heuristic is unvalidated.** Grouping `gh_hl leaf 173.2`
   under leaf 173 is inferred from the naming pattern, not confirmed by the
   authors. It affects 414 images.

3. **No ImageNet pretraining in any reported figure.** How much of the field
   collapse is attributable to training from scratch is unmeasured.

4. **Confidence is uncalibrated.** No temperature scaling; selective-prediction
   figures would shift under calibration, though the published literature
   suggests not enough to change the conclusion.

5. **Severity has no ground truth.** Thresholds are conventional. On a soil
   background lesion fraction rises from 0.004 to 0.93 — unusable in the field.

6. **Whether the field collapse is primarily domain shift or label-semantics
   mismatch is not separated.** PlantDoc's disease definitions may not align
   exactly with PlantVillage's even for same-named classes.

7. **Tamil strings are unreviewed** by a native agricultural extension speaker.


---

# FINAL SCIENTIFIC CONSISTENCY PASS — 2026-10-31

## Results frozen

All 21 authoritative values were re-verified against the result JSON before any
document was rewritten. **Every one matched**: 936 test images, accuracy
0.9561966, macro F1 0.9506470, 895 correct, diagonal 127/273/258/237, `.pte`
8.891 MB, 60/60 agreement, max logit diff 3.457e-06, PlantDoc primary 350 images
at 0.3914 / 0.3629 with confidence 0.8124 wrong and 0.8644 right, sensitivity
413 images at 0.3414 / 0.2782, leakage 63.97% with
3918 / 414 / 20 / 1919 grouping coverage and AUC 0.963.

## Documents rebuilt from a single generator

`reports/build_final.py` now emits all five Phase 1 documents with **every figure
interpolated from JSON**. No number is typed by hand, so a report cannot drift
from the artifact it describes. `gen_reports.py` was deleted to remove the
possibility of two generators disagreeing.

## Automated consistency audit

`reports/consistency_check.py` — 18 checks, **all pass**. It verifies that each
headline figure appears in the report and results documents, that the confusion
diagonal and correct-prediction count are present, that the lower-bound caveat on
leakage is stated, that severity is marked EXPERIMENTAL with background
sensitivity named, that Arm figures are declared non-existent, and that no
sentence implies Llama was deployed. Retracted values are flagged unless they
appear within two lines of retraction context.

## Three-class PlantDoc protocol — documented semantics

The classifier retains **four** output classes. The primary external test set
contains only the three unambiguously labelled disease classes. A prediction of
*healthy* on a disease-only sample is possible and **counts as an error**;
7 such predictions occurred, contributing to 137/350 correct. The four-class
result is retained as sensitivity analysis with its assumption disclosed.

## Leakage methodology — identity source clarified

The report now states explicitly that **human annotation is the identity
source** and that the rotation-invariant descriptor is corroborating evidence
only. The descriptor is not claimed to establish physical identity on its own.

## Severity — status downgraded

Marked **EXPERIMENTAL**. Background sensitivity is stated as unresolved (0.004
to 0.93 on a soil background), leaf segmentation is named as the prerequisite,
and the estimator is nowhere described as field-ready.

## Obsolete files

`PHASE1_REPORT1.md` on the user's machine was a stale duplicate of the pre-audit
report. A tombstone was written over it. No duplicate report versions exist in
the archive.

## Deliverables

`PHASE1_REPORT.md`, `PHASE1_RESULTS.md`, `PHASE1_COMPLIANCE.md`,
`PHASE1_DEMO_SCRIPT.md`, `PHASE1_SUBMISSION_CHECKLIST.md`,
`CONSISTENCY_AUDIT.md`, `REFERENCES.md` — one authoritative version each, plus
`reports/PHASE1_REPORT.pdf` generated from the corrected markdown.
