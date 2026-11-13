# AGRI-SHIELD AI — Phase 3 Blockers

**As of:** 31 October 2026
**Deadline:** 21 November 2026 — **21 days remain**

---

## B1 — Real tomato leaf photographs ⛔ **BLOCKS THE MILESTONE**

**Blocks:** the entire primary success condition. Everything else in Phase 3 is built, verified and waiting.

**Why I cannot supply these myself.** Fabricating sample images or labels is forbidden by the brief, and correctly so. The laptop's `datasets/` directory holds only `metadata/split_summary.json` — the PlantVillage images lived in the Phase 1 container, which no longer exists, and the PlantVillage GitHub repository is not reachable from this session.

**Target set** (testing targets, not a promise of availability):

| Class | Wanted |
|---|---|
| Healthy tomato leaf | 5 |
| Early blight | 5 |
| Late blight | 5 |
| Septoria leaf spot | 5 |

Fewer is fine. Even **one** real photograph satisfies the milestone; twenty makes it a result rather than a demonstration. Missing classes will be reported as missing, not quietly dropped.

### How to shoot them — this materially affects the outcome

The preprocessing audit (§3.2) found that the training transform resizes the shorter side to 109 and centre-crops 96. On a 16:9 photo that **discards 56 % of the frame** before the model sees anything. So:

1. **Fill the frame with one leaf, centred.** Anything near the edges is cropped away.
2. **Square (1:1) if your camera offers it.** Otherwise 4:3. Avoid 16:9 — it is the worst case.
3. **Plain background** — a sheet of paper, a table. The model was trained on single detached leaves against uniform backgrounds.
4. **Even daylight.** No flash, no harsh shadow across the lesion.
5. **In focus**, lesions clearly visible.
6. **Name the files by class**, e.g. `early_blight_01.jpg`, `healthy_03.jpg`. That is how the label reaches the manifest, and it must come from you — never from the model's own prediction.

The pipeline records the retained-area fraction for every image and flags anything below 60 %, so bad framing will be visible in the record rather than silently degrading the result.

**Getting them to me:** attach them to this chat, or drop them in `Documents\AGRI_SHIELD_AI\phase3\photos\`. Either works.

### Set expectations before we run

The PlantDoc external evaluation measured **0.3914 accuracy** on real-world images against **0.9562** in-domain. That is a known, documented, measured limitation of a model trained from random initialisation on lab photographs.

**Your photographs may well be misclassified, and that is a finding, not a failure.** It would corroborate the domain-shift limitation already in the Phase 1 report with evidence from the target device. What would be dishonest is quietly presenting whatever the model says as correct.

---

## B2 — No independent ground truth

**Blocks:** any accuracy figure or confusion matrix.

A label supplied by the photographer is a *declared* label, not an independently verified one. The brief is explicit: *"Do not label an image as a disease merely because the model predicts that disease."*

So:

- Predictions will be recorded for every photograph regardless.
- Accuracy and a confusion matrix are computed **only** over images carrying a declared label, and will be reported as *"agreement with declared labels"*, never as validated accuracy.
- `real_image_confusion_matrix.png` is produced **only** if enough labelled samples exist to make it meaningful. With fewer than about two per class it is noise dressed as a figure, and will be omitted with a note.

If a plant pathologist or your faculty mentor can confirm the labels, that upgrades the result materially. Worth asking — it costs them minutes.

---

## B3 — Thermal data remains unavailable

Carried from Phase 2, unchanged. `/sys/class/thermal/*/temp` is unreadable from inside proot without root, and was equally unreadable via the non-root adb shell. Both Phase 2 runs recorded zero thermal zones.

The Phase 3 runner will report the same. **No thermal figure is claimed anywhere.**

---

## B4 — ADB connection is intermittent

The phone dropped off ADB during the Phase 2 result pull while remaining visible over MTP. Files were recovered by MTP copy instead.

Not blocking — MTP is a reliable fallback and the payload is already on the phone. Worth knowing that the transfer step may need the manual route again.

---

## B5 — Native Android APK — unchanged decision

Still needs the Android NDK or Maven Central, both unreachable from the build container; realistically Android Studio (~3 GB) plus a day of build work.

With a verified on-device result in hand and 21 days left, my view is unchanged: this is the expensive option and should be weighed last. Your call.

---

## B6 — Llama 3.2 1B — still correctly deferred

No work done, none should be. Licence unaccepted; the advisory system still holds **0 source-verified chemical intervention records**.

---

## What is NOT blocked

- Preprocessing pipeline — built and **verified bit-exact against torchvision** across nine geometries including 4:3 and 16:9
- Arm runner with per-image latency and probabilities — built, cross-compiled, and regression-checked 8/8 against the frozen desktop reference
- Tensor format — unchanged, so the synthetic validation path cannot be broken by Phase 3
- Phase 1 archive and Phase 2 results — untouched
