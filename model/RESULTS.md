# Classifier results (authoritative)

Frozen 2026-10-31. Every value below is read from the result JSON in `model/results/`.

## In-domain `[DESK]` — PlantVillage held-out

| Metric | Value |
| --- | --- |
| Test images | 936 |
| Correct predictions | 895 |
| Accuracy | **0.9561966** |
| Macro precision | 0.9560880 |
| Macro recall | 0.9464312 |
| Macro F1 | **0.9506470** |
| Confusion matrix diagonal | 127, 273, 258, 237 |

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

## External `[DESK]` — PlantDoc

| Protocol | Images | Accuracy | Macro F1 |
| --- | --- | --- | --- |
| **Primary (3 disease classes)** | 350 | **0.3914** | **0.3629** |
| Sensitivity (4 classes, healthy inferred) | 413 | 0.3414 | 0.2782 |

Mean confidence when wrong **0.8124**, when correct
0.8644.

The classifier retains 4 output classes; a *healthy* prediction on a disease-only
sample counts as an error.

| Threshold | Coverage | Accuracy on answered | Selective risk |
| --- | --- | --- | --- |
| 0.0 | 1.000 | 0.3914 | 0.6086 |
| 0.7 | 0.800 | 0.425 | 0.575 |
| 0.9 | 0.489 | 0.4737 | 0.5263 |
| 0.95 | 0.277 | 0.5979 | 0.4021 |

## Leakage

| Item | Value |
| --- | --- |
| Random-split contamination | **63.97%** (lower bound) |
| Official human-annotated leaf map | 3918 images |
| Decimal filename heuristic | 414 images |
| Hash grouping | 20 images |
| Ungrouped (singletons) | 1919 images |
| Rotation-invariant descriptor AUC | 0.963 |
| Group-straddle violations | 0 |

## ExecuTorch artifact

| Property | Value |
| --- | --- |
| Size | 8.891 MB |
| PyTorch agreement | 60/60 |
| Max logit difference | 3.457e-06 |
| Tolerance | 1e-3 |
| Audit checks | 17/17 pass |

## Not measured

Llama inference (never executed), Arm performance (no device), calibrated
confidence, severity ground truth, pretrained-backbone training.
