# AGRI-SHIELD AI

Offline crop-disease detection and farmer advisory for Arm hardware.
Bharat AI-SoC Challenge 2026-27, Problem Statement 1.

A leaf photo goes in. A disease name, a calibration-free confidence, an estimated
severity band and an advisory in Tamil or English come out, with no network
connection at any point.

> **Status, stated plainly.** The vision pipeline is implemented, trained and
> verified. **Llama inference has never been executed, on any hardware**, and
> nothing in this project has run on an Arm device. The advisory layer currently
> runs against a mock backend and **always abstains**, because the knowledge base
> holds zero source-verified chemical interventions. The mandatory Llama and Arm
> requirements are unsatisfied. See `PHASE1_COMPLIANCE.md`.

## Implemented and verified

| Capability | Evidence |
| --- | --- |
| Disease classifier, 4 tomato classes | 0.9562 accuracy, 0.9506 macro F1 on 936 held-out images |
| External field evaluation (PlantDoc) | 0.3914 accuracy — see "Honest performance" below |
| Leakage-proof dataset splitting | 0 group-straddle violations; 63.97% random-split leakage avoided |
| ExecuTorch export of the classifier | 8.891 MB `.pte`, 60/60 agreement with PyTorch, max logit diff 3.457e-06 |
| Severity estimation | **EXPERIMENTAL** — see limitations |
| Knowledge-base retrieval + confidence gate | `retrieval.py --self-test`, 6 abstain cases + 2 controls |
| Advisory layer with output guard | `advisor.py --self-test`, including an adversarial rogue-backend case |
| Offline desktop application | 0 outbound connections under a socket-level block, 13/13 checks |
| Independent audit | 17/17 checks, `audit.py` |

## Planned — NOT implemented

| Capability | Blocker |
| --- | --- |
| **Llama 3.2 1B inference** | Meta licence not approved; no model obtained, no export, no execution |
| **Llama via ExecuTorch** | depends on the above |
| **Arm / Android deployment** | adb not installed, no device attached |
| **Any `[ARM]` performance figure** | none exist; `benchmarks/results_arm.md` is deliberately empty |
| Source-verified chemical advice | 0 of 4 knowledge-base records verified against TNAU/ICAR |
| Pest identification module | deferred to Phase 2 |
| GitHub publication | Git not installed |

## Honest performance

| | In-domain (PlantVillage) | Field (PlantDoc) |
| --- | --- | --- |
| Accuracy | 0.9562 | **0.3914** |
| Macro F1 | 0.9506 | 0.3629 |

Mean confidence when **wrong** on field imagery: 0.8124,
against 0.8644 when right. The model is confidently
inaccurate outside the lab. **This system is not fit for unsupervised field use.**

No ImageNet pretraining was used — the backbone was trained from random
initialisation. Quote that methodology with every figure above.

## Why the splitting script matters

PlantVillage photographs each physical leaf about four times, and the repository
ships `leaf-map.json`: **human-annotated leaf identities**, built from Excel
sheets whose columns are `File Name` and `Leaf #`. Annotators counted physical
leaves; the identity is not derived from pixels.

`prepare_splits.py` groups images by that human-assigned leaf ID, falls back to a
filename-decimal heuristic, then to perceptual hashing, and keeps every group
inside one split. Coverage on the four tomato classes:

| Signal | Images |
| --- | --- |
| Human-annotated leaf map | 3918 |
| Decimal filename heuristic | 414 |
| Perceptual hash | 20 |
| No signal, treated as singletons | 1919 |

A random split leaks **63.97%** of test images.
Perceptual hashing alone estimated this at 0.64% — a hundredfold underestimate,
because the four views of a leaf are rotated and reflected and do not hash alike.

Because 1919 images carry no leaf identity,
63.97% is a **lower bound**.

## Safety

The system would advise farmers on pesticides, so safety is enforced structurally
rather than by trusting the model:

- **Input side.** Chemical fields are never copied into the prompt unless the
  record is source-verified and confidence clears the threshold.
- **Output side.** Generated text is scanned for pesticide actives and dose
  patterns; a violating response is replaced, not merely flagged.

**The knowledge base currently holds 0 source-verified chemical interventions**,
so every advisory abstains and refers the user to a local agricultural extension
officer. That is the gate working as designed, not a defect.

The output filter is a finite blocklist and **cannot be claimed to catch every
unsafe recommendation**. The guarantee rests on the input side.

## Quickstart

```bash
python -m venv env-executorch
env-executorch/bin/pip install -r requirements-executorch.txt
python scripts/export_hello.py
python scripts/run_hello.py            # expect: output shape: (1, 1000)
```

```bash
python -m venv env-vision
env-vision/bin/pip install -r requirements-vision.txt

python disease_detection/training/prepare_splits.py \
    --root datasets/raw/PlantVillage/raw/color \
    --leaf-map datasets/raw/PlantVillage/leaf-map.json \
    --out datasets/metadata
```

Run the offline application:

```bash
python application/app.py --checkpoint runs/tomato4_scratch/best.pt \
    --kb knowledge_base/diseases.json
```

Dataset acquisition is in `INSTALL_NEXT.md`.

## Claim discipline

Every measurement carries `[SIM]`, `[DESK]` or `[ARM]`. Only `[ARM]` figures
support an on-device claim, and **none exist**. Desktop and device results live
in separate files so they cannot be confused.

## Where to look

`PHASE1_REPORT.md` (and `reports/PHASE1_REPORT.pdf`) · `PHASE1_RESULTS.md` ·
`PHASE1_COMPLIANCE.md` · `CONSISTENCY_AUDIT.md` (two retracted claims) ·
`USER_ACTIONS.md` · `CLAUDE.md` for project rules.
