# Test results

Every row below was executed and its output observed. Nothing is marked pass
without a run.

## Automated tests

| Date | Test | Command | Result |
| --- | --- | --- | --- |
| 10-30 | ExecuTorch export | `scripts/export_hello.py` | PASS — 13.94 MB `.pte` |
| 10-30 | ExecuTorch runtime | `scripts/run_hello.py` | PASS — shape `(1, 1000)`, median 5.0 ms `[DESK]` |
| 10-30 | Split, synthetic fixture | `prepare_splits.py --root /tmp/fakepv` | PASS — 90 groups, 0 violations |
| 10-30 | Split, real data + leaf map | `prepare_splits.py --leaf-map ...` | PASS — 3,175 groups, 0 violations, 63.97% leakage avoided |
| 10-31 | Classifier training | `train.py` 22 epochs | PASS — test acc **0.9562**, macro F1 **0.9506** (best.pt; corrected from 0.9615 by audit) |
| 10-31 | External PlantDoc, 3-class primary | `external_eval.py` | PASS — acc 0.3914, macro F1 0.3629 |
| 10-31 | Leaf-identity validation | provenance + structure + visual + rotation-invariant | PASS — AUC 0.963, 63.97% retained |
| 10-31 | Confusion matrix regeneration | from `best.pt` + manifest | PASS — total 936, diagonal 895 |
| 10-30 | Unseen-image inference | `predict.py --evaluate-unseen --n 14` | PASS — 13/14; the miss had the lowest confidence (0.528) |
| 10-30 | Trained-model export | `export_classifier.py` | PASS — 8.89 MB `.pte`, runtime shape `(1, 4)` |
| 10-30 | KB safety gate | `retrieval.py --self-test` | PASS — 6 abstain cases + positive + negative control |
| 10-30 | Advisory layer | `advisor.py --self-test` | PASS — see below |
| 10-30 | Application | `app.py --selftest` | PASS — **0 external URLs in served page** |
| 10-30 | Application end to end | POST `/analyze`, EN + TA | PASS — pred 0.979, both languages, history recorded |

## Advisory safety tests (`advisor.py --self-test`)

| Case | Expected | Result |
| --- | --- | --- |
| Mock advisory, English | no blocked content | PASS |
| Mock advisory, Tamil | no blocked content | PASS |
| `"Spray mancozeb 2 g/L every 7 days"` | blocked | PASS — caught term + dose |
| `"Apply 3 ml/L of the solution"` | blocked (bare dose) | PASS |
| `"Remove affected leaves..."` | allowed through | PASS — no false positive |
| Rogue backend emits chlorothalonil | text **replaced**, not just flagged | PASS |
| `ExecuTorchBackend` with no `.pte` | refuses to construct | PASS |

Two independent mechanisms: retrieval withholds chemical fields from the prompt,
and the output guard scans generated text and substitutes a safe fallback. The
rogue-backend case proves the second one works even when the first is bypassed.

## Not yet tested — and why

| Area | Blocker |
| --- | --- |
| Anything on Windows | no Python env on the laptop yet |
| Anything on Arm | adb not installed, no device attached |
| Real Llama inference | licence not approved; `ExecuTorchBackend` correctly refuses |
| PlantDoc cross-domain | not downloaded; expected large accuracy drop unmeasured |
| Pretrained-backbone training | `download.pytorch.org` blocked in sandbox |
| Tamil wording quality | needs a native agricultural speaker |
| Severity accuracy | no severity-labelled ground truth exists |

**`benchmarks/results_arm.md` is still empty. That is correct.**
