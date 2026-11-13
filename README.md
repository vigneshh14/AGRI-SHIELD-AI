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

## Status (Phase 1, due 23 Nov 2026)

Being completed. See `docs/PHASE1_PLAN_13_to_21_NOV.md` and `docs/SUBMISSION_CHECKLIST.md`.
The vision pipeline, Android app and Phase 1 report are being merged into this repository.

## Known limitations

Tomato only (4 classes) in Phase 1; severity estimate is experimental; TNAU gives no spray
interval for these diseases, so none is stated; Tamil strings await native-speaker review;
the advisory text is generated in English.
