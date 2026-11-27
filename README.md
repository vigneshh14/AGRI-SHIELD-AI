# AGRI-SHIELD AI

**Offline crop-disease detection and farmer advisory on an Arm phone, with Llama 3.2 1B running through ExecuTorch.**

Bharat AI-SoC Challenge 2026–27 · Problem Statement 1 · Solo entry: Vignesh S, M.E. VLSI Design,
College of Engineering Guindy, Anna University.

[![advisory-safety-tests](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/tests.yml/badge.svg)](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/tests.yml)

A farmer photographs a tomato leaf. The phone, in airplane mode, identifies the disease,
retrieves the official treatment record, and explains it in plain language. No cloud, no
network.

```
camera → MobileNet classifier (ExecuTorch, XNNPACK) → confidence gate
   ├─ confident + sourced record → Llama 3.2 1B (ExecuTorch) explains → output guard → screen
   │                                                     + dose table straight from TNAU record
   └─ not confident / not sourced → abstain: "don't spray, retake photo / see extension officer"
```

## Mandatory requirements

| Requirement | How | Evidence |
| --- | --- | --- |
| Llama-family model owns the advisory | Llama 3.2 1B Instruct (SpinQuant INT4) writes the farmer-facing text | `android/advisory/LlamaAdvisoryEngine.kt` |
| ExecuTorch is the runtime | `org.pytorch:executorch-android` `LlmModule`, XNNPACK | `benchmarks/results_arm.md` |
| Runs on Arm, offline | Infinix NOTE 30 5G (MediaTek Dimensity 6080), airplane mode | demo video, `[ARM]` results |
| Hosted on GitHub | this repository | — |

## Safety design (pesticide advice)

- **Doses never come from the language model.** They are shown from
  `knowledge_base/tomato_tnau_v2.json`; each product traces to a TNAU Agritech page,
  verified 13 Nov 2026.
- **The prompt contains no chemical names or doses at all.** Llama explains the disease and
  field practices only.
- **Output guard:** if the model's text names any pesticide, any dose or any spray interval,
  it's rejected and a fixed, clearly labelled fallback is shown.
- **Abstain below the confidence threshold:** no chemical information is shown anywhere.
- 70 automated checks (gate, prompt-leak sweep over every class × confidence, guard, engine)
  run on every push; see the badge.

## Claim discipline

Every number carries one tag: `[SIM]` simulated, `[DESK]` x86 laptop, `[ARM]` measured on
the phone offline. Only `[ARM]` numbers support on-device claims, and they live only in
`benchmarks/results_arm.md`.

## Repository

| Path | Contents |
| --- | --- |
| `android/advisory/` | Gate, prompt, guard (`AdvisoryGate.kt`), Llama engine, generated KB |
| `knowledge_base/` | TNAU-sourced records (source of truth) |
| `tools/gen_kb_kotlin.py` | Regenerates `KnowledgeBase.kt` from the JSON |
| `tests/` | JVM tests + ExecuTorch API stubs (test-only) |
| `scripts/get_llama_model.ps1` | Downloads and hash-verifies the Llama model + tokenizer |
| `benchmarks/results_arm.md` | On-device measurements |
| `docs/` | Llama-on-phone runbook, plan, checklist, demo script, report corrections |

## Get the model (not stored in Git: 1.1 GB)

```powershell
.\scripts\get_llama_model.ps1                      # download + verify SHA256
.\scripts\get_llama_model.ps1 -Push -Package <applicationId>   # also adb-push to the phone
```

Source: [executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET](https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET).
Llama 3.2 is subject to Meta's Llama 3.2 Community License.

## For evaluators (Phase 1 submission)

| What | Where |
| --- | --- |
| Final report (PDF / DOCX) | [`reports/final/AGRI_SHIELD_AI_Final_Report.pdf`](reports/final/AGRI_SHIELD_AI_Final_Report.pdf), [`.docx`](reports/final/AGRI_SHIELD_AI_Final_Report.docx) |
| Android APK (CI build) | [Releases: apk-latest](https://github.com/vigneshh14/AGRI-SHIELD-AI/releases/tag/apk-latest) |
| Android app source | [`PHASE4/android_app`](PHASE4/android_app) + [`android/advisory`](android/advisory) |
| On-phone classifier results | [`benchmarks/results_arm_proot.md`](benchmarks/results_arm_proot.md) |
| Training, evaluation, leakage audit | [`disease_detection/`](disease_detection), [`PHASE1_RESULTS.md`](PHASE1_RESULTS.md) |
| TNAU treatment knowledge base | [`knowledge_base/tomato_tnau_v2.json`](knowledge_base/tomato_tnau_v2.json) |

The 31 October `PHASE1_REPORT.*` files are an earlier draft, superseded by
`reports/final/`; they are kept for history (for example the withdrawn I8MM claim).

Status as of 27 Nov 2026: the classifier runs on the phone ([ARM-PROOT], 12.538 ms median
offline); the Llama advisory stage is integrated in the app, builds in CI and passes its
tests, and its first run on the phone is pending (report section 3.6).

## Known limitations

Tomato only (4 classes) in Phase 1; severity estimate is experimental; TNAU gives no spray
interval for these diseases, so none is stated; Tamil strings await native-speaker review;
the advisory text is generated in English.
