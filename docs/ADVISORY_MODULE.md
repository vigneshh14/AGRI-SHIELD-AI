# AGRI-SHIELD AI: Phase 1 finishing kit (13 Nov 2026)

Drop-in pieces for the existing AGRI-SHIELD AI project. Built in a cloud workspace
with no access to your laptop or GitHub, so it is **additive**: nothing here
replaces your frozen Phase 1/2/3 artifacts.

| Path | What it is | Status |
| --- | --- | --- |
| `docs/PHASE1_PLAN_13_to_21_NOV.md` | Day-by-day plan to submission | — |
| `docs/GATE1_LLAMA_ON_PHONE.md` | Llama 3.2 1B on the phone via ExecuTorch, no export, no NDK | Steps written; **not yet run on the phone** |
| `knowledge_base/tomato_tnau_v2.json` | Early blight, late blight, Septoria, healthy, with TNAU doses and URLs | Each page read twice on 13 Nov; all rows matched |
| `android/advisory/AdvisoryGate.kt` | Confidence gate, Llama prompt, output guard, fallback | Compiled and tested on JVM [DESK] |
| `android/advisory/LlamaAdvisoryEngine.kt` | `LlmModule` wrapper (ExecuTorch 0.7–1.6 API subset) | Compiled against v1.6.0-signature stubs; **not yet run on Android** |
| `android/advisory/KnowledgeBase.kt` | Generated from the JSON | Do not hand-edit |
| `tests/` | 70 checks: gate, prompt-leak sweep, guard, engine end-to-end with a stub runtime | 70/70 pass |
| `docs/REPORT_I8MM_CORRECTION.md` | Replacement text for the withdrawn I8MM claim | Re-check `/proc/cpuinfo` before pasting |
| `docs/SUBMISSION_CHECKLIST.md` | Final gate before the form | — |

## Run the tests

Needs Java 17+ and a Kotlin compiler (`kotlinc`, or the one inside Android Studio):

```bash
python tools/gen_kb_kotlin.py
kotlinc android/advisory/*.kt tests/*.kt tests/stubs/*.kt -d out
kotlin -cp out com.agrishield.advisory.AdvisoryGateTestKt   # expect: ALL 70 CHECKS PASSED
```

Do **not** copy `tests/stubs/` into the Android app. The real `LlmModule` comes from
the `executorch-android` AAR.

## Before merging, check

- **Class labels.** The KB uses PlantVillage names (`Tomato___Early_blight`,
  `Tomato___Late_blight`, `Tomato___Septoria_leaf_spot`, `Tomato___healthy`). They must
  match your classifier's `class_names` exactly. Any class the model has that the KB
  lacks abstains automatically, which is safe but should be a deliberate choice.
- **Threshold.** `AdvisoryGate.DEFAULT_THRESHOLD = 0.80`. Set it to the value used in
  your Python M6 module and the report, so the two agree.
- **Old KB.** `tomato_tnau_v2.json` supersedes the 30 Oct file whose chemical lists
  were empty. Keep the old one in history, not in the app.

## Design decisions to state in the report

- Llama writes the farmer-facing explanation. **Doses and product names come only from
  the KB table**, never from model text. The guard rejects any model output that names
  a chemical, a dose or a spray interval, and the UI then shows a deterministic fallback
  labelled as such.
- TNAU gives **no spray interval** for these three diseases, so the app says so and
  refers the farmer to the extension officer and the product label.
- Septoria's dose is **per hectare** on the source page, unlike the others, which are
  **per acre**. Both are shown as printed, not converted.
- Advisory text is generated in English. Tamil covers the disease names and UI labels
  from the KB. A 1B model writing Tamil pesticide guidance is a Phase 2 item, once it
  can be evaluated.
