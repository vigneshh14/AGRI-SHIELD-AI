# AGRI-SHIELD AI

Offline tomato-disease detection and farmer advisory on an Arm Android phone, with Llama 3.2 1B through ExecuTorch.

Bharat AI-SoC Challenge 2026-27, Problem Statement 1, Phase 1 submission. Solo entry: Vignesh S, M.E. VLSI Design, College of Engineering Guindy, Anna University, Chennai.

[![advisory-safety-tests](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/tests.yml/badge.svg)](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/tests.yml)
[![android-apk](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/android-apk.yml/badge.svg)](https://github.com/vigneshh14/AGRI-SHIELD-AI/actions/workflows/android-apk.yml)

A farmer photographs a tomato leaf. The phone, offline, classifies it, and Llama 3.2 1B explains the result in plain language. Product names and doses never come from the language model: they are shown from a local copy of Tamil Nadu Agricultural University's published recommendations, and only when the classifier is confident.

```
photo -> MobileNetV2 (ExecuTorch, XNNPACK, Arm CPU) -> confidence gate (p >= 0.80, margin >= 0.20)
   pass -> TNAU record -> prompt without products or doses -> Llama 3.2 1B (ExecuTorch) -> output guard -> screen
                       -> dose table straight from the TNAU record ------------------------------------> screen
   fail -> "no product recommended; retake the photo or see the extension officer"
```

## Phase 1 deliverables

| Deliverable | Where |
| --- | --- |
| Technical report | [`report/AGRI_SHIELD_AI_Final_Report.pdf`](report/AGRI_SHIELD_AI_Final_Report.pdf) ([.docx](report/AGRI_SHIELD_AI_Final_Report.docx)) |
| Application (Android APK) | [Releases: apk-latest](https://github.com/vigneshh14/AGRI-SHIELD-AI/releases/tag/apk-latest), built by CI from this repository |
| Source code | this repository (layout below) |
| Demonstration video | link in the submission form |

## Repository layout

| Folder | Contents |
| --- | --- |
| [`android_app/`](android_app) | Kotlin Android app: camera/gallery, preprocessing, ExecuTorch classifier, result screen with the Llama advisory |
| [`advisory/`](advisory) | Confidence gate, Llama prompt, output guard, `LlmModule` engine, generated knowledge base, and their 73-check test suite |
| [`knowledge_base/`](knowledge_base) | `tomato_tnau_v2.json`, treatment records copied from the TNAU Agritech portal with source URLs |
| [`model/`](model) | Leakage-safe split, MobileNetV2 training, PlantDoc evaluation, audit, ExecuTorch export; results in `model/results/` and [`model/RESULTS.md`](model/RESULTS.md) |
| [`benchmarks/`](benchmarks) | Measurements on the phone: [`results_arm_proot.md`](benchmarks/results_arm_proot.md) (classifier), [`results_arm.md`](benchmarks/results_arm.md) (app, Llama) |
| [`report/`](report) | Final report: Markdown source, figures, PDF, DOCX |
| [`scripts/`](scripts) | Download and verify the Llama model, push models to the phone, install and run the app |
| [`docs/`](docs) | How to run on the phone, ExecuTorch setup log, demo video script |

## Key results

| | Result | Tag |
| --- | --- | --- |
| Accuracy, held-out PlantVillage (936 images) | 0.9562, macro F1 0.9506 | [DESK] |
| Accuracy, PlantDoc field photos (350, never trained on) | 0.3914 | [DESK] |
| Classifier on the phone, airplane mode | 12.538 ms median, 23.7 MB peak RSS | [ARM-PROOT] |
| Phone vs x86 agreement | 8/8 top-1, max logit difference 2.384e-6 | [ARM-PROOT] |
| Llama advisory on the phone | integrated and built; first on-phone run pending | none |

[DESK]: x86 development machine. [ARM-PROOT]: the phone's own Arm cores, Debian userland under proot. [ARM]: inside the native app on the phone. Report section 3.6 states the Llama status in full.

## Run it

```powershell
git clone https://github.com/vigneshh14/AGRI-SHIELD-AI.git
cd AGRI-SHIELD-AI
.\scripts\run_on_phone.ps1 -Classifier <path to agrishield_tomato4.pte>
```

This downloads the CI-built APK, installs it, verifies and copies the classifier and the Llama model (1.1 GB, fetched and SHA-256 checked by `scripts/get_llama_model.ps1`), and shows the on-device log. Details: [`docs/RUN_ON_PHONE.md`](docs/RUN_ON_PHONE.md). Model files are never committed.

Llama model: [executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET](https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET), subject to Meta's Llama 3.2 Community License. Datasets: PlantVillage (Mohanty et al. 2016), PlantDoc (Singh et al. 2020, CC BY 4.0).

## Limitations

Tomato only, 4 classes, no pest module. Field accuracy 39.1%. Severity banding is an experimental desktop script (`model/severity_experimental.py`), not in the app. TNAU gives no spray interval for these diseases, so none is stated. Tamil disease names await native-speaker review; advisory text is in English.
