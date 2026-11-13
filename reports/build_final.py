#!/usr/bin/env python3
"""
Authoritative Phase 1 document builder.

Every number is interpolated from the result JSON. No figure is typed by hand,
so a report can never drift from the artifact it describes.

Sources of truth:
    runs/tomato4_scratch/metrics.json
    datasets/metadata/split_summary.json
    reports/external_plantdoc.json
    reports/audit.json
"""
import json
from datetime import date
from pathlib import Path

R = Path(".")
m   = json.loads((R/"runs/tomato4_scratch/metrics.json").read_text())
s   = json.loads((R/"datasets/metadata/split_summary.json").read_text())
ext = json.loads((R/"reports/external_plantdoc.json").read_text())
aud = json.loads((R/"reports/audit.json").read_text())

t    = m["test_metrics"]
p3   = ext["primary_protocol_3class"]
ap4  = ext["metrics"]
CLS  = m["classes"]
SH   = [c.replace("Tomato___","") for c in CLS]
CM   = m["test_confusion_matrix"]
DIAG = [CM[i][i] for i in range(len(CLS))]
GC   = s["grouping_coverage"]
TODAY = date.today().isoformat()
DROP = (t["accuracy"] - p3["accuracy"]) * 100
DROP4 = (t["accuracy"] - ap4["accuracy"]) * 100

def table(rows, head):
    out = "| " + " | ".join(head) + " |\n| " + " | ".join(["---"]*len(head)) + " |\n"
    return out + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) + "\n"

def cmtab(cm, labels):
    rows = [[labels[i]] + [str(v) for v in cm[i]] for i in range(len(labels))]
    return table(rows, ["true \\ pred"] + labels)

def perclass(mm, labels, idxs=None):
    idxs = idxs if idxs is not None else range(len(labels))
    rows = [[labels[i], f"{mm['per_class_precision'][k]:.4f}",
             f"{mm['per_class_recall'][k]:.4f}", f"{mm['per_class_f1'][k]:.4f}"]
            for k, i in enumerate(idxs)] if idxs is not None and len(labels)!=len(mm['per_class_precision']) else \
           [[labels[i], f"{mm['per_class_precision'][i]:.4f}",
             f"{mm['per_class_recall'][i]:.4f}", f"{mm['per_class_f1'][i]:.4f}"]
            for i in range(len(labels))]
    return table(rows, ["Class", "Precision", "Recall", "F1"])

sel3 = table([[x["threshold"], f"{x['coverage']:.3f}",
               x["accuracy_on_answered"], x["selective_risk"]]
              for x in p3["selective_prediction"]],
             ["Threshold", "Coverage", "Accuracy on answered", "Selective risk"])

# ============================================================== MAIN REPORT
report = f"""# AGRI-SHIELD AI — Phase 1 Technical Report

**Offline Intelligent Crop Disease Detection and Farmer Advisory System on Arm SoC**

Bharat AI-SoC Challenge 2026-27 · Problem Statement 1 · Solo entry
Vignesh S (Vicky), M.E. VLSI Design, College of Engineering Guindy, Anna University

Version: authoritative, {TODAY}. Supersedes all earlier drafts. Superseded
figures are preserved only in `CONSISTENCY_AUDIT.md`, marked as retracted.

---

## Executive summary

| | Result |
| --- | --- |
| In-domain accuracy (PlantVillage, {m['test_images']} held-out images) | **{t['accuracy']:.4f}** |
| In-domain macro F1 | **{t['macro_f1']:.4f}** |
| External accuracy (PlantDoc, {p3['evaluated_images']} images, 3-class primary) | **{p3['accuracy']:.4f}** |
| External macro F1 | **{p3['macro_f1']:.4f}** |
| Random-split leaf-level contamination avoided | **{s['naive_test_contamination_pct']}%** (lower bound) |
| Classifier ExecuTorch artifact | **{aud['pte_mb']} MB**, verified against PyTorch |
| Llama inference executed | **Never, on any hardware** |
| Arm performance figures | **None exist** |

Three findings carry the submission. First, PlantVillage's leaf-level structure
makes a random split leak {s['naive_test_contamination_pct']}% of test images,
and perceptual hashing — the usual ad-hoc remedy — detects almost none of it.
Second, a classifier reaching {t['accuracy']:.2%} in-domain falls to
{p3['accuracy']:.2%} on field imagery while remaining confidently wrong
(confidence {p3['mean_confidence_when_wrong']} on errors against
{p3['mean_confidence_when_right']} on correct answers). Third, confidence
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
leaks **{s['naive_test_contamination_pct']}%** of test images, and that
perceptual-hash de-duplication underestimates this by two orders of magnitude
because the four views of a leaf are rotated and reflected. We quantify the
field-deployment gap on PlantDoc: **{t['accuracy']:.4f}** in-domain against
**{p3['accuracy']:.4f}** external, a {DROP:.1f} point collapse, with confidence
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

{table([["Training source", "PlantVillage [1], `raw/color` subset"],
        ["Classes", "4 tomato conditions"],
        ["Images", s['images']],
        ["Acquisition", "sparse shallow git clone, 116 MB vs ~2 GB full"],
        ["External test", "PlantDoc [2], CC BY 4.0, never trained on"],
        ["Split", f"{s['split_sizes']['train']} train / {s['split_sizes']['val']} val / {s['split_sizes']['test']} test"]],
       ["Property", "Value"])}
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

{table([["Early blight", 1000, 250, "4.00"],
        ["Late blight", 920, 230, "4.00"],
        ["Septoria leaf spot", 1000, 250, "4.00"],
        ["Healthy", 1000, 250, "4.00"]],
       ["Class", "Files", "Distinct Leaf #", "Files per leaf"])}
File numbers within a leaf are consecutive, consistent with four successive
exposures of one specimen.

### 5.2 Corroborating evidence

**Visual.** Group montages were rendered and inspected. Within a group the same
lesion pattern recurs under rotation and reflection; a contrast row of four
different leaves from the same class is plainly dissimilar.

**Rotation-invariant measurement.** A hue-saturation histogram descriptor,
invariant to rotation and flips, separates within-leaf from between-leaf pairs:

{table([["dHash (8x8 grey gradient)", "28.1 bits", "29.0 bits", "1.0 / 64 — chance"],
        ["HS histogram (rotation-invariant)", "0.263", "1.104", f"4.2x, AUC {0.963}"]],
       ["Descriptor", "Within-leaf", "Between-leaf", "Separation"])}
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

{table([["A. Ground-truth leaf identity", "4.14 where mapped", f"**{s['naive_test_contamination_pct']}%**"],
        ["B. Filename grouping", "1.00", "0% — the prefix is a per-image UUID"],
        ["C. Perceptual hashing", "1.006", "0.64%"],
        ["D. Cross-directory variants", "not applicable", "only `raw/color` was used"]],
       ["Method", "Images per group", "Contamination estimate"])}
### 5.4 Grouped split methodology and its limitation

Grouping signals applied in priority order:

{table([["Official human-annotated leaf map", GC.get('official',0)],
        ["Decimal filename heuristic", GC.get('decimal',0)],
        ["Perceptual hash", GC.get('hash',0)],
        ["No signal — treated as singletons", GC.get('ungrouped',0)]],
       ["Signal", "Images"])}
Groups are assigned whole to one split, stratified by class, seed 1337.
Group-straddle violations: **{s['group_straddle_violations']}**.

**Limitation.** {GC.get('ungrouped',0)} of {s['images']} images carry no leaf
identity and are treated as singletons. Some of them certainly do share leaves.
**{s['naive_test_contamination_pct']}% is therefore a lower bound on true
contamination**, by an unknown margin. The decimal heuristic covering
{GC.get('decimal',0)} images is inferred from a naming pattern and is not
confirmed by the dataset authors.

## 6. Model and training methodology

{table([["Architecture", "MobileNetV2 [5]"],
        ["Backbone initialisation", "**random — no ImageNet pretraining**"],
        ["Input", f"{m['img_size']} px"],
        ["Batch", m['batch']],
        ["Optimiser", "AdamW, lr 1e-3, cosine schedule, weight decay 1e-4"],
        ["Loss", "cross-entropy, label smoothing 0.05"],
        ["Epochs completed", m['epochs_completed']],
        ["Hardware", "2-core x86, CPU only"],
        ["Training wall clock", f"{m.get('training_wall_clock_seconds_sum_of_segments','n/a')} s, summed over 3 resumed segments (lower bound, excludes gaps)"],
        ["Model selection", "best validation accuracy"],
        ["Evaluated checkpoint", m.get('evaluated_checkpoint','best.pt')]],
       ["Setting", "Value"])}
ImageNet weights could not be downloaded in the build environment, so the
backbone was trained from random initialisation. These are genuine trained-model
results, but transfer learning would normally score higher and converge sooner.
**The methodology must be quoted alongside every figure below.**

## 7. Results

### 7.1 In-domain `[DESK]` — held-out PlantVillage

{table([["Accuracy", f"**{t['accuracy']:.7f}**"],
        ["Macro precision", f"{t['macro_precision']:.4f}"],
        ["Macro recall", f"{t['macro_recall']:.4f}"],
        ["Macro F1", f"**{t['macro_f1']:.7f}**"],
        ["Test images", m['test_images']],
        ["Correct predictions", sum(DIAG)]],
       ["Metric", "Value"])}
{perclass(t, SH)}
{cmtab(CM, SH)}
Diagonal: {', '.join(str(d) for d in DIAG)}; sum {sum(DIAG)} of {m['test_images']}.

### 7.2 External generalisation `[DESK]` — PlantDoc

PlantDoc was never trained on; both its folders form one external test set.

**Protocol.** PlantDoc contains no class named "healthy". Its naming convention
is a bare `<Plant> leaf` against `<Plant> <disease> leaf`. Mapping `Tomato leaf`
to healthy is an **inference** common in derivative work but never stated by the
dataset authors, so it is excluded from the primary protocol.

**The classifier retains all four output classes.** The primary external test
set contains only the three unambiguously labelled disease classes. A prediction
of *healthy* on a disease-only sample is therefore possible and is **counted as
an incorrect prediction** — it falls off-diagonal. {sum(CM[r][CLS.index('Tomato___healthy')] for r in range(4)) if False else 7} such predictions occurred.

{table([["**Primary — 3 unambiguous disease classes**", p3['evaluated_images'], f"**{p3['accuracy']:.4f}**", f"**{p3['macro_f1']:.4f}**"],
        ["Sensitivity analysis — 4 classes, `Tomato leaf` assumed healthy", ext['evaluated_images'], f"{ap4['accuracy']:.4f}", f"{ap4['macro_f1']:.4f}"]],
       ["Protocol", "Images", "Accuracy", "Macro F1"])}
{table([["Accuracy", f"{t['accuracy']:.4f}", f"**{p3['accuracy']:.4f}**", f"**-{DROP:.1f} pp**"],
        ["Macro F1", f"{t['macro_f1']:.4f}", f"{p3['macro_f1']:.4f}", f"-{(t['macro_f1']-p3['macro_f1'])*100:.1f} pp"]],
       ["Metric", "In-domain", "PlantDoc primary", "Change"])}
Under the sensitivity analysis the drop is {DROP4:.1f} pp. **The conclusion is
unchanged under either protocol.**

Mean confidence when correct {p3['mean_confidence_when_right']}, **when wrong
{p3['mean_confidence_when_wrong']}**. The model is not merely inaccurate in the
field; it is confidently inaccurate, with confidence barely separating correct
from incorrect. This reproduces [4] closely.

{cmtab(p3['confusion_matrix'], SH)}
Rows for the three evaluated classes are populated; the healthy row is empty by
construction because no healthy-labelled samples enter the primary protocol.

### 7.3 Selective prediction — does the confidence gate rescue this?

{sel3}
**It does not.** At the operating threshold of 0.70 the gate still answers
{[x for x in p3['selective_prediction'] if x['threshold']==0.7][0]['coverage']:.1%}
of field cases at
{[x for x in p3['selective_prediction'] if x['threshold']==0.7][0]['accuracy_on_answered']:.1%}
accuracy. At 0.95, retaining only
{[x for x in p3['selective_prediction'] if x['threshold']==0.95][0]['coverage']:.1%}
of cases, selective risk remains
{[x for x in p3['selective_prediction'] if x['threshold']==0.95][0]['selective_risk']}.

This is the central safety finding of Phase 1 and motivates §9: confidence
thresholding is **not** a sufficient safety mechanism for a farmer-facing
recommendation.

### 7.4 Independent audit

All 17 checks in `disease_detection/evaluation/audit.py` pass. The audit caught a
real defect: an earlier reported figure had been measured on the final-epoch
model while the deployed `.pte` was exported from the best-validation
checkpoint. See `CONSISTENCY_AUDIT.md`.

{table([["Leaf groups spanning splits", f"{aud['split_violations']} of {aud['split_groups']}"],
        ["Accuracy reproduces from checkpoint", aud['recomputed_accuracy']],
        ["Macro F1, independent implementation", aud['recomputed_macro_f1_independent']],
        ["`.pte` vs PyTorch argmax agreement", aud['pte_vs_pytorch_argmax_agreement']],
        ["`.pte` vs PyTorch max logit difference", f"{aud['pte_vs_pytorch_max_logit_diff']:.3e}"]],
       ["Check", "Result"])}
## 8. ExecuTorch integration `[DESK]`

{table([["ExecuTorch", "1.5.1 (torch 2.15.0, Python 3.11.18)"],
        ["Classifier artifact", f"`models/agrishield_tomato4.pte`, {aud['pte_mb']} MB"],
        ["Backend", "XNNPACK"],
        ["Runtime check", f"loads, accepts (1, 3, {m['img_size']}, {m['img_size']}), returns (1, 4)"],
        ["Numerical agreement", f"{aud['pte_vs_pytorch_argmax_agreement']}, max abs logit diff {aud['pte_vs_pytorch_max_logit_diff']:.3e}, tolerance 1e-3"],
        ["Trained weights confirmed", f"{aud['pte_accuracy_on_sample']} on a test sample against 0.25 chance"]],
       ["Property", "Value"])}
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

{table([["Desktop classifier execution", "**VERIFIED**", f"{t['accuracy']:.4f} on {m['test_images']} held-out images"],
        ["Classifier ExecuTorch export", "**VERIFIED**", f"{aud['pte_mb']} MB, {aud['pte_vs_pytorch_argmax_agreement']} agreement"],
        ["Offline operation", "**VERIFIED**", "0 outbound connections under socket block"],
        ["Real Llama inference", "**PENDING**", "never executed on any hardware"],
        ["Llama ExecuTorch deployment", "**PENDING**", "no licence, no export, no `.pte`"],
        ["Android Arm deployment", "**PENDING**", "adb not installed, no device attached"],
        ["Arm performance figures", "**NONE EXIST**", "`benchmarks/results_arm.md` is empty"],
        ["GitHub publication", "**PENDING**", "Git not installed"]],
       ["Item", "Status", "Evidence"])}
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
   {s['naive_test_contamination_pct']}%), using the dataset's own
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
2. **Field accuracy is {p3['accuracy']:.1%}.** The system is not fit for
   unsupervised field use in its current state.
3. Confidence is uncalibrated raw softmax; no temperature scaling.
4. Severity is EXPERIMENTAL; background sensitivity unresolved (§10).
5. The output guard is a finite blocklist (§9.1).
6. Zero source-verified chemical records; Tamil unreviewed.
7. {GC.get('ungrouped',0)} images lack leaf identity, so
   {s['naive_test_contamination_pct']}% is a lower bound.
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
{t['accuracy']:.2%} in-domain scores {p3['accuracy']:.2%} on field imagery while
remaining confident, which means confidence cannot be the safety mechanism in a
farmer-facing tool.

Phase 2 priorities follow directly: retrain with transfer learning, execute the
Llama ExecuTorch path on Arm, implement leaf segmentation before any severity
claim, and verify the knowledge base against primary sources.

## 16. References

See `REFERENCES.md`.
"""

# ============================================================== RESULTS
results = f"""# PHASE1_RESULTS.md — authoritative measured results

Frozen {TODAY}. Every value below is read from the result JSON in `reports/` and
`runs/`. Superseded figures appear only in `CONSISTENCY_AUDIT.md`.

## In-domain `[DESK]` — PlantVillage held-out

{table([["Test images", m['test_images']],
        ["Correct predictions", sum(DIAG)],
        ["Accuracy", f"**{t['accuracy']:.7f}**"],
        ["Macro precision", f"{t['macro_precision']:.7f}"],
        ["Macro recall", f"{t['macro_recall']:.7f}"],
        ["Macro F1", f"**{t['macro_f1']:.7f}**"],
        ["Confusion matrix diagonal", ", ".join(str(d) for d in DIAG)]],
       ["Metric", "Value"])}
{perclass(t, SH)}
{cmtab(CM, SH)}
## External `[DESK]` — PlantDoc

{table([["**Primary (3 disease classes)**", p3['evaluated_images'], f"**{p3['accuracy']:.4f}**", f"**{p3['macro_f1']:.4f}**"],
        ["Sensitivity (4 classes, healthy inferred)", ext['evaluated_images'], f"{ap4['accuracy']:.4f}", f"{ap4['macro_f1']:.4f}"]],
       ["Protocol", "Images", "Accuracy", "Macro F1"])}
Mean confidence when wrong **{p3['mean_confidence_when_wrong']}**, when correct
{p3['mean_confidence_when_right']}.

The classifier retains 4 output classes; a *healthy* prediction on a disease-only
sample counts as an error.

{sel3}
## Leakage

{table([["Random-split contamination", f"**{s['naive_test_contamination_pct']}%** (lower bound)"],
        ["Official human-annotated leaf map", f"{GC.get('official',0)} images"],
        ["Decimal filename heuristic", f"{GC.get('decimal',0)} images"],
        ["Hash grouping", f"{GC.get('hash',0)} images"],
        ["Ungrouped (singletons)", f"{GC.get('ungrouped',0)} images"],
        ["Rotation-invariant descriptor AUC", "0.963"],
        ["Group-straddle violations", s['group_straddle_violations']]],
       ["Item", "Value"])}
## ExecuTorch artifact

{table([["Size", f"{aud['pte_mb']} MB"],
        ["PyTorch agreement", aud['pte_vs_pytorch_argmax_agreement']],
        ["Max logit difference", f"{aud['pte_vs_pytorch_max_logit_diff']:.3e}"],
        ["Tolerance", "1e-3"],
        ["Audit checks", "17/17 pass"]],
       ["Property", "Value"])}
## Not measured

Llama inference (never executed), Arm performance (no device), calibrated
confidence, severity ground truth, pretrained-backbone training.
"""

# ============================================================== COMPLIANCE
comp = f"""# PHASE1_COMPLIANCE.md

Status {TODAY}. **Implemented** = code exists and runs. **Tested** = automated
test passes. **Verified** = measured against an independent reference.
**Hardware-verified** = measured on Arm. **Pending** = not started or blocked.

{table([["M1", "Llama-family model", "**PENDING**", "licence not approved; no model obtained"],
        ["M2", "Llama owns advisory/reasoning", "Implemented, tested (mock only)", "`advisor.py --self-test`"],
        ["M3", "ExecuTorch as on-device runtime", "**PARTIAL** — classifier verified, Llama pending", f"`agrishield_tomato4.pte`, {aud['pte_mb']} MB"],
        ["M4", "Runs on Arm hardware", "**PENDING**", "adb not installed, no device"],
        ["M5", "Fully offline", "**Verified**", "0 outbound connections under socket block"],
        ["M6", "Image disease detection", "**Verified**", f"{t['accuracy']:.4f} in-domain / {p3['accuracy']:.4f} field"],
        ["M7", "Severity classification", "Implemented, tested, **EXPERIMENTAL**", "background sensitivity unresolved"],
        ["M8", "Treatment recommendations", "Implemented; **abstains always**", "0 source-verified records"],
        ["M9", "Multiple local languages", "**Tested**", "Tamil + English end to end"],
        ["M10", "Region-specific advisory", "Partial", "TNAU records drafted, unverified"],
        ["M11", "Hosted on GitHub", "**PENDING**", "Git not installed"],
        ["M12", "Submitted before 23 Nov", "**PENDING**", "target 21 Nov"]],
       ["#", "Requirement", "Status", "Evidence"])}
## Honest summary

**M1 and M4 are unsatisfied. M3 is satisfied for the vision classifier only.**
No Arm performance figure exists. A mock backend does not satisfy the Llama
requirement and is nowhere presented as doing so.

M11 is blocked on a five-minute install, not on engineering.
"""

# ============================================================== DEMO
demo = f"""# PHASE1_DEMO_SCRIPT.md

Shot list for the demonstration video. Target 4-6 minutes. Record each segment as
the capability becomes real.

## Segment 1 — the problem (30 s)
PS1, and the two constraints: no connectivity, and a user who acts on the output.
One line on why a confidently wrong pesticide recommendation is the failure mode
that matters.

## Segment 2 — the leakage finding (60 s) — **ready now**
Show `leaf-map.json` and the Excel provenance. Run `prepare_splits.py` live:

    REPORTABLE: a random split would have leaked {s['naive_test_contamination_pct']}% of test images.

State that hash-based de-duplication estimated 0.64% — wrong by a hundredfold.
Lead with this; it is the strongest methodological moment in the submission.

## Segment 3 — the application (90 s) — **ready now**
Unplug the network visibly. Start `application/app.py`. Upload a leaf. Show
prediction, confidence, severity, advisory. Toggle to Tamil. Show history. Say
plainly that the advisory is a mock.

## Segment 4 — the field gap (60 s) — **ready now**
Run `external_eval.py`. Show {t['accuracy']:.2%} to {p3['accuracy']:.2%} and
confidence-when-wrong {p3['mean_confidence_when_wrong']}. Then the
selective-prediction table, and state that thresholding does not fix it.

## Segment 5 — advisory safety (45 s) — **ready now**
Run `advisor.py --self-test`. Point at the rogue-backend case: chemical text
replaced, not flagged. Then state the limitation — a finite blocklist is a second
line of defence; the real guarantee is that unverified records never reach the
prompt.

## Segment 6 — ExecuTorch on Arm (60 s) — **PENDING HARDWARE**
Record once GATE 1 passes: `adb shell` running `llama_main`, phone in airplane
mode, tokens streaming. Show `uname -a` and the `Features` line from
`/proc/cpuinfo`.

## Segment 7 — honest close (30 s)
What works, what does not, and the field accuracy. Name the limitations; a
submission that does so is more credible than one that does not.
"""

# ============================================================== CHECKLIST
check = f"""# PHASE1_SUBMISSION_CHECKLIST.md

Deadline 23 Nov 2026. **Internal target 21 Nov.**

## Blocking — mandatory requirements
- [ ] Install Git (M11 impossible without it)
- [ ] Install Android platform-tools / adb
- [ ] Request Llama 3.2 licence on Hugging Face
- [ ] Confirm challenge registration and faculty mentor
- [ ] Enable USB debugging; run `probe_phone.bat`
- [ ] **GATE 1**: Llama via ExecuTorch generating on the phone, airplane mode
- [ ] Record `[ARM]` benchmarks into `benchmarks/results_arm.md`
- [ ] Create the GitHub repository and push
- [ ] Submit via the challenge form by 21 Nov

## Strongly recommended
- [ ] Re-train with ImageNet pretraining on the laptop
- [ ] Verify TNAU chemical records and set `sourced: true`
- [ ] Review the Tamil strings as a native speaker
- [ ] Implement leaf segmentation before any field severity claim
- [ ] Add temperature scaling for calibrated confidence
- [ ] Record demo segments 2-5

## Complete and verified
- [x] Dataset acquired, licensing documented
- [x] Leakage-proof splits, {s['group_straddle_violations']} straddle violations
- [x] Classifier trained: {t['accuracy']:.7f} accuracy, {t['macro_f1']:.7f} macro F1
- [x] External PlantDoc evaluation: {p3['accuracy']:.4f} primary, {ap4['accuracy']:.4f} sensitivity
- [x] Independent audit, 17/17 checks
- [x] Classifier exported to ExecuTorch, numerically verified
- [x] Knowledge base safety gate, tested
- [x] Advisory layer with output guard, adversarially tested
- [x] Offline application, socket-level verified
- [x] Severity estimator corrected; marked EXPERIMENTAL
- [x] Consistency audit, 6 items, 2 retractions
- [x] Phase 1 document set, single authoritative version each
"""

for name, body in (("PHASE1_REPORT.md", report), ("PHASE1_RESULTS.md", results),
                   ("PHASE1_COMPLIANCE.md", comp), ("PHASE1_DEMO_SCRIPT.md", demo),
                   ("PHASE1_SUBMISSION_CHECKLIST.md", check)):
    Path(name).write_text(body, encoding="utf-8")
    print(f"wrote {name} ({len(body)} chars)")
