# AGRI-SHIELD AI — Phase 1 Technical Report

**Offline Intelligent Crop Disease Detection and Farmer Advisory System on Arm SoC**

Bharat AI-SoC Challenge 2026-27 · Problem Statement 1 · Solo entry
Vignesh S (Vicky), M.E. VLSI Design, College of Engineering Guindy, Anna University

Version: authoritative, 2026-10-31. Supersedes all earlier drafts. Superseded
figures are preserved only in `CONSISTENCY_AUDIT.md`, marked as retracted.

---

## Executive summary

| | Result |
| --- | --- |
| In-domain accuracy (PlantVillage, 936 held-out images) | **0.9562** |
| In-domain macro F1 | **0.9506** |
| External accuracy (PlantDoc, 350 images, 3-class primary) | **0.3914** |
| External macro F1 | **0.3629** |
| Random-split leaf-level contamination avoided | **63.97%** (lower bound) |
| Classifier ExecuTorch artifact | **8.891 MB**, verified against PyTorch |
| Llama inference executed | **Never, on any hardware** |
| Arm performance figures | **None exist** |

Three findings carry the submission. First, PlantVillage's leaf-level structure
makes a random split leak 63.97% of test images,
and perceptual hashing — the usual ad-hoc remedy — detects almost none of it.
Second, a classifier reaching 95.62% in-domain falls to
39.14% on field imagery while remaining confidently wrong
(confidence 0.8124 on errors against
0.8644 on correct answers). Third, confidence
thresholding does not repair this, so advisory safety is enforced structurally
rather than probabilistically.

**Compliance position.** The mandatory Llama requirement is **unsatisfied**. The
advisory interface and prompts are implemented and tested against a mock
backend; no Llama model has been exported or executed. ExecuTorch is
demonstrated for the vision classifier only.

---

## Abstract

We present AGRI-SHIELD AI, an offline crop-disease detection and advisory system
targeting Arm hardware. A MobileNetV2 classifier identifies four tomato leaf
conditions; an HSV proxy estimates lesion severity; and a local knowledge base
supplies treatment records keyed by condition and severity. The advisory
interface, including Tamil and English prompt templates and a confidence gate,
is implemented and tested against a mock backend. **Llama 3.2 1B deployment
through ExecuTorch is designed and scripted but has not been executed**; no
Llama inference has taken place on any hardware, and the mandatory Llama
requirement is therefore unsatisfied.

The work's substantive contributions are methodological. We show that
PlantVillage's human-annotated leaf identities imply a random train/test split
leaks **63.97%** of test images, and that
perceptual-hash de-duplication underestimates this by two orders of magnitude
because the four views of a leaf are rotated and reflected. We quantify the
field-deployment gap on PlantDoc: **0.9562** in-domain against
**0.3914** external, a 56.5 point collapse, with confidence
barely distinguishing correct from incorrect predictions. We show that selective
prediction does not close this gap, and therefore architect advisory safety so
that chemical recommendations are withheld from the language model's prompt
unless a source-verified record exists, with an independent output filter as a
second, explicitly incomplete, layer.

---

## 1. Introduction and problem definition

PS1 asks for an AI assistant that identifies crop diseases, detects pests,
classifies severity, recommends treatment, supports local languages, and runs
entirely on-device without connectivity [11]. Llama and ExecuTorch are mandatory;
the advisory component must be Llama-driven and ExecuTorch must be the runtime.

Two deployment constraints drive the engineering. Rural connectivity is
intermittent, so cloud inference is unavailable. The user is a smallholder
farmer acting directly on the output, so a wrong pesticide recommendation causes
financial loss and potential health harm. Both push toward the same design: a
small on-device model, and an advisory layer that structurally cannot invent.

## 2. Literature review and positioning

Offline plant-disease classification is mature; Mohanty et al. [1] established
PlantVillage and reported ~99% in-domain accuracy. Two lines of prior work bear
directly on this project.

**Embedded-LLM agricultural advisory is already published.** AgriSentinel [6]
claims the first privacy-enhanced embedded-LLM crop disease alerting system,
pairing a lightweight classifier with a fine-tuned GPT-2 over a curated
knowledge pool. AgriAdvisor [7] combines on-device detection with a small-LLM
advisory and differential privacy. **No novelty is claimed here for the
combination of on-device classification and on-device LLM advisory.**

**Calibration and selective prediction for plant disease are also published.**
The 2026 Frontiers benchmark [4] evaluates temperature scaling, selective
prediction, OOD scoring and deep ensembles under controlled-to-field shift, and
finds they reduce but do not eliminate the reliability gap, with the best
selective risk at 80% coverage remaining above 0.51. **No novelty is claimed for
abstention as a concept.**

Noyan [3] showed PlantVillage carries background bias severe enough that eight
background pixels alone yield 49.0% accuracy. The leakage axis documented in §5
is independent of that one.

## 3. System architecture

```
M1 acquisition -> M2 disease classifier -> M4 severity -> confidence gate
   gate pass  -> M6 knowledge retrieval -> M5 advisory layer -> M7 UI
   gate fail  -> abstain record (no chemicals enter the prompt) -> M5 -> M7
M8: no component makes a network call.
```

Each module sits behind a plain Python interface. That property is what allowed
the full pipeline to be validated end to end while the Llama backend remains
unavailable — the advisory layer runs against a mock that is stamped as such in
every response.

## 4. Dataset methodology

| Property | Value |
| --- | --- |
| Training source | PlantVillage [1], `raw/color` subset |
| Classes | 4 tomato conditions |
| Images | 6271 |
| Acquisition | sparse shallow git clone, 116 MB vs ~2 GB full |
| External test | PlantDoc [2], CC BY 4.0, never trained on |
| Split | 4390 train / 945 val / 936 test |

**Licensing.** The PlantVillage repository contains no LICENSE file; the authors
request citation of [1] via `CITATION.cff`. PlantDoc is explicitly CC BY 4.0.

## 5. Leaf-level leakage analysis

PlantVillage photographs each physical leaf four times. The repository ships
`leaf-map.json`, assigning each image a leaf identity.

### 5.1 Provenance of the leaf identities

`leaf_grouping/aggregate_map.py` constructs the map from human-annotated Excel
spreadsheets whose columns are `File Name` and `Leaf #`. The identity is assigned
by annotators counting physical leaves; it is **not** derived from pixels. This
human annotation is the identity source. Everything in §5.2 is corroboration,
not an independent identity claim.

| Class | Files | Distinct Leaf # | Files per leaf |
| --- | --- | --- | --- |
| Early blight | 1000 | 250 | 4.00 |
| Late blight | 920 | 230 | 4.00 |
| Septoria leaf spot | 1000 | 250 | 4.00 |
| Healthy | 1000 | 250 | 4.00 |

File numbers within a leaf are consecutive, consistent with four successive
exposures of one specimen.

### 5.2 Corroborating evidence

**Visual.** Group montages were rendered and inspected. Within a group the same
lesion pattern recurs under rotation and reflection; a contrast row of four
different leaves from the same class is plainly dissimilar.

**Rotation-invariant measurement.** A hue-saturation histogram descriptor,
invariant to rotation and flips, separates within-leaf from between-leaf pairs:

| Descriptor | Within-leaf | Between-leaf | Separation |
| --- | --- | --- | --- |
| dHash (8x8 grey gradient) | 28.1 bits | 29.0 bits | 1.0 / 64 — chance |
| HS histogram (rotation-invariant) | 0.263 | 1.104 | 4.2x, AUC 0.963 |

The descriptor corroborates the annotation; it does not establish physical
identity on its own, and is not offered as doing so.

### 5.3 Why perceptual hashing is insufficient

On identical image pairs, dHash separates same-leaf from different-leaf at
essentially chance, while the rotation-invariant descriptor reaches AUC 0.963.
The failure is in the descriptor, not the metadata: an 8x8 grayscale gradient is
destroyed by rotation. Loosening the Hamming threshold does not help — at
threshold 12 the largest group reached 769 images through union-find transitive
closure, merging unrelated leaves.

A pipeline relying on hash de-duplication would report a clean split and a
materially inflated accuracy.

| Method | Images per group | Contamination estimate |
| --- | --- | --- |
| A. Ground-truth leaf identity | 4.14 where mapped | **63.97%** |
| B. Filename grouping | 1.00 | 0% — the prefix is a per-image UUID |
| C. Perceptual hashing | 1.006 | 0.64% |
| D. Cross-directory variants | not applicable | only `raw/color` was used |

### 5.4 Grouped split methodology and its limitation

Grouping signals applied in priority order:

| Signal | Images |
| --- | --- |
| Official human-annotated leaf map | 3918 |
| Decimal filename heuristic | 414 |
| Perceptual hash | 20 |
| No signal — treated as singletons | 1919 |

Groups are assigned whole to one split, stratified by class, seed 1337.
Group-straddle violations: **0**.

**Limitation.** 1919 of 6271 images carry no leaf
identity and are treated as singletons. Some of them certainly do share leaves.
**63.97% is therefore a lower bound on true
contamination**, by an unknown margin. The decimal heuristic covering
414 images is inferred from a naming pattern and is not
confirmed by the dataset authors.

## 6. Model and training methodology

| Setting | Value |
| --- | --- |
| Architecture | MobileNetV2 [5] |
| Backbone initialisation | **random — no ImageNet pretraining** |
| Input | 96 px |
| Batch | 32 |
| Optimiser | AdamW, lr 1e-3, cosine schedule, weight decay 1e-4 |
| Loss | cross-entropy, label smoothing 0.05 |
| Epochs completed | 22 |
| Hardware | 2-core x86, CPU only |
| Training wall clock | 1450.3 s, summed over 3 resumed segments (lower bound, excludes gaps) |
| Model selection | best validation accuracy |
| Evaluated checkpoint | best.pt (best validation epoch) |

ImageNet weights could not be downloaded in the build environment, so the
backbone was trained from random initialisation. These are genuine trained-model
results, but transfer learning would normally score higher and converge sooner.
**The methodology must be quoted alongside every figure below.**

## 7. Results

### 7.1 In-domain `[DESK]` — held-out PlantVillage

| Metric | Value |
| --- | --- |
| Accuracy | **0.9561966** |
| Macro precision | 0.9561 |
| Macro recall | 0.9464 |
| Macro F1 | **0.9506470** |
| Test images | 936 |
| Correct predictions | 895 |

| Class | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Early_blight | 0.9478 | 0.8581 | 0.9007 |
| Late_blight | 0.9381 | 0.9545 | 0.9463 |
| Septoria_leaf_spot | 0.9591 | 0.9773 | 0.9681 |
| healthy | 0.9793 | 0.9958 | 0.9875 |

| true \ pred | Early_blight | Late_blight | Septoria_leaf_spot | healthy |
| --- | --- | --- | --- | --- |
| Early_blight | 127 | 15 | 5 | 1 |
| Late_blight | 7 | 273 | 6 | 0 |
| Septoria_leaf_spot | 0 | 2 | 258 | 4 |
| healthy | 0 | 1 | 0 | 237 |

Diagonal: 127, 273, 258, 237; sum 895 of 936.

### 7.2 External generalisation `[DESK]` — PlantDoc

PlantDoc was never trained on; both its folders form one external test set.

**Protocol.** PlantDoc contains no class named "healthy". Its naming convention
is a bare `<Plant> leaf` against `<Plant> <disease> leaf`. Mapping `Tomato leaf`
to healthy is an **inference** common in derivative work but never stated by the
dataset authors, so it is excluded from the primary protocol.

**The classifier retains all four output classes.** The primary external test
set contains only the three unambiguously labelled disease classes. A prediction
of *healthy* on a disease-only sample is therefore possible and is **counted as
an incorrect prediction** — it falls off-diagonal. 7 such predictions occurred.

| Protocol | Images | Accuracy | Macro F1 |
| --- | --- | --- | --- |
| **Primary — 3 unambiguous disease classes** | 350 | **0.3914** | **0.3629** |
| Sensitivity analysis — 4 classes, `Tomato leaf` assumed healthy | 413 | 0.3414 | 0.2782 |

| Metric | In-domain | PlantDoc primary | Change |
| --- | --- | --- | --- |
| Accuracy | 0.9562 | **0.3914** | **-56.5 pp** |
| Macro F1 | 0.9506 | 0.3629 | -58.8 pp |

Under the sensitivity analysis the drop is 61.5 pp. **The conclusion is
unchanged under either protocol.**

Mean confidence when correct 0.8644, **when wrong
0.8124**. The model is not merely inaccurate in the
field; it is confidently inaccurate, with confidence barely separating correct
from incorrect. This reproduces [4] closely.

| true \ pred | Early_blight | Late_blight | Septoria_leaf_spot | healthy |
| --- | --- | --- | --- | --- |
| Early_blight | 27 | 54 | 5 | 2 |
| Late_blight | 20 | 85 | 4 | 2 |
| Septoria_leaf_spot | 43 | 80 | 25 | 3 |
| healthy | 0 | 0 | 0 | 0 |

Rows for the three evaluated classes are populated; the healthy row is empty by
construction because no healthy-labelled samples enter the primary protocol.

### 7.3 Selective prediction — does the confidence gate rescue this?

| Threshold | Coverage | Accuracy on answered | Selective risk |
| --- | --- | --- | --- |
| 0.0 | 1.000 | 0.3914 | 0.6086 |
| 0.7 | 0.800 | 0.425 | 0.575 |
| 0.9 | 0.489 | 0.4737 | 0.5263 |
| 0.95 | 0.277 | 0.5979 | 0.4021 |

**It does not.** At the operating threshold of 0.70 the gate still answers
80.0%
of field cases at
42.5%
accuracy. At 0.95, retaining only
27.7%
of cases, selective risk remains
0.4021.

This is the central safety finding of Phase 1 and motivates §9: confidence
thresholding is **not** a sufficient safety mechanism for a farmer-facing
recommendation.

### 7.4 Independent audit

All 17 checks in `disease_detection/evaluation/audit.py` pass. The audit caught a
real defect: an earlier reported figure had been measured on the final-epoch
model while the deployed `.pte` was exported from the best-validation
checkpoint. See `CONSISTENCY_AUDIT.md`.

| Check | Result |
| --- | --- |
| Leaf groups spanning splits | 0 of 3175 |
| Accuracy reproduces from checkpoint | 0.9562 |
| Macro F1, independent implementation | 0.9506 |
| `.pte` vs PyTorch argmax agreement | 60/60 |
| `.pte` vs PyTorch max logit difference | 3.457e-06 |

## 8. ExecuTorch integration `[DESK]`

| Property | Value |
| --- | --- |
| ExecuTorch | 1.5.1 (torch 2.15.0, Python 3.11.18) |
| Classifier artifact | `models/agrishield_tomato4.pte`, 8.891 MB |
| Backend | XNNPACK |
| Runtime check | loads, accepts (1, 3, 96, 96), returns (1, 4) |
| Numerical agreement | 60/60, max abs logit diff 3.457e-06, tolerance 1e-3 |
| Trained weights confirmed | 0.8167 on a test sample against 0.25 chance |

The ExecuTorch runtime probes the Arm MIDR identification register at load and
logs failure on x86. Arm feature detection is compiled in; what it reports on the
target device bears on whether the KleidiAI I8MM path is taken [9].

**Llama via ExecuTorch: NOT STARTED.** No licence, no export, no `.pte`.
`llama_advisory/advisor.py::ExecuTorchBackend` refuses to construct without the
artifacts, deliberately.

## 9. Advisory safety architecture

Given §7.3, confidence cannot carry the safety argument. Two structural
mechanisms are used instead.

**Input side.** In abstain mode the retrieval layer never copies chemical fields
into the prompt dictionary. The model cannot repeat text it was never given.
This is a property of the data path, not of model compliance.

**Output side.** Generated text is scanned for pesticide actives and dose
patterns; a violating response is **replaced** with a safe fallback. Verified
with a deliberately rogue backend emitting `"Spray chlorothalonil 2 g/L"` — the
text was replaced, not merely flagged.

### 9.1 Stated limitation of the output guard

The output filter is a **finite keyword and regex blocklist and cannot be
claimed to prevent every unsafe recommendation.** It will miss trade names
absent from the list, transliterated or Tamil-script chemical names,
misspellings, and dose formats outside its patterns. It is a second line of
defence, not a guarantee. The guarantee rests on the input side.

### 9.2 Knowledge base status

4 records, **0 with source-verified chemical interventions**. TNAU's portal was
unreachable from the build environment. Each record carries `sourced: false`, the
source URL to verify against, and symptoms and cultural practices in English and
Tamil. Every advisory therefore abstains. Tamil strings are drafted and
**unreviewed by a native agricultural extension speaker**.

## 10. Severity estimation — EXPERIMENTAL

An HSV chlorosis-and-necrosis fraction of leaf area, banded mild / moderate /
severe. A corrected version resolved a healthy-leaf false positive: healthy
leaves now score mild in 40 of 40 sampled test images, with median lesion
fraction 0.0037 against 0.0929 for early blight. It is robust to brightness
changes of 0.6x and 1.5x.

**Background sensitivity remains unresolved.** The estimator performs no leaf
segmentation. Compositing the same leaf onto a soil-coloured background raises
the lesion fraction from 0.004 to **0.93**. Until leaf segmentation is
implemented and validated, **field severity estimation is marked EXPERIMENTAL
and must not be presented as a verified diagnosis.** The system suppresses
severity entirely when the classifier predicts healthy.

Thresholds are conventional and have never been calibrated against expert-scored
ground truth, because no severity-labelled data was available.

## 11. Offline application

`application/app.py`, Python standard-library `http.server`, all CSS and JS
inlined. No Flask, no Gradio, no CDN, no web fonts.

Verified by monkeypatching `socket.socket.connect` to raise on any non-loopback
address and exercising the full pipeline: **0 outbound connection attempts**, 13
of 13 functional checks passing, served page containing 0 external URLs.

Features: image upload, prediction with confidence, severity, advisory,
Tamil/English toggle, diagnosis history. Every advisory is stamped
`is_mock: true`.

## 12. Hardware and compliance status

| Item | Status | Evidence |
| --- | --- | --- |
| Desktop classifier execution | **VERIFIED** | 0.9562 on 936 held-out images |
| Classifier ExecuTorch export | **VERIFIED** | 8.891 MB, 60/60 agreement |
| Offline operation | **VERIFIED** | 0 outbound connections under socket block |
| Real Llama inference | **PENDING** | never executed on any hardware |
| Llama ExecuTorch deployment | **PENDING** | no licence, no export, no `.pte` |
| Android Arm deployment | **PENDING** | adb not installed, no device attached |
| Arm performance figures | **NONE EXIST** | `benchmarks/results_arm.md` is empty |
| GitHub publication | **PENDING** | Git not installed |

**A mock backend does not satisfy the Llama requirement and is never presented
as doing so.** Mandatory requirements M1 and M4 are unsatisfied; M3 is satisfied
for the vision classifier only.

## 13. Contributions and explicit non-claims

**Not claimed as novel:** offline plant disease classification; on-device LLM
advisory [6][7]; calibration or selective prediction for plant disease [4];
severity from affected leaf area.

**Offered as contributions:**

1. A quantified demonstration that perceptual-hash de-duplication underestimates
   PlantVillage leaf-level contamination by two orders of magnitude (0.64% vs
   63.97%), using the dataset's own
   human-annotated leaf map as the identity source, with corroborating visual
   and rotation-invariant evidence.
2. A reproducible in-domain-to-field characterisation for this configuration,
   with a selective-prediction curve showing thresholding does not repair it.
3. An advisory architecture whose safety property is structural rather than
   probabilistic, with an adversarial test demonstrating the failure mode it
   defends against, and an explicit statement of the output filter's
   incompleteness.

Contribution 2 **reproduces rather than extends** [4]; it is offered as
independent replication on a different model and subset.

## 14. Limitations

1. No ImageNet pretraining in any reported figure.
2. **Field accuracy is 39.1%.** The system is not fit for
   unsupervised field use in its current state.
3. Confidence is uncalibrated raw softmax; no temperature scaling.
4. Severity is EXPERIMENTAL; background sensitivity unresolved (§10).
5. The output guard is a finite blocklist (§9.1).
6. Zero source-verified chemical records; Tamil unreviewed.
7. 1919 images lack leaf identity, so
   63.97% is a lower bound.
8. Four classes, one crop. No pest module.
9. **Nothing has executed on Arm.** No `[ARM]` figure exists.
10. Whether the field collapse is primarily domain shift or label-semantics
    mismatch is not separated.

## 15. Conclusions

A complete offline pipeline has been implemented and verified end to end on a
desktop, with the vision classifier exported to ExecuTorch and checked
numerically against PyTorch. The mandatory Llama and Arm requirements are
**not met**, and the report makes no claim otherwise.

The scientific value of Phase 1 lies in two negative results that are
reproducible and consequential. PlantVillage leakage is far larger than hash-based
de-duplication suggests, which means published accuracies on ad-hoc splits of
this dataset should be treated cautiously. And a classifier that scores
95.62% in-domain scores 39.14% on field imagery while
remaining confident, which means confidence cannot be the safety mechanism in a
farmer-facing tool.

Phase 2 priorities follow directly: retrain with transfer learning, execute the
Llama ExecuTorch path on Arm, implement leaf segmentation before any severity
claim, and verify the knowledge base against primary sources.

## 16. References

See `REFERENCES.md`.
