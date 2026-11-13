# Phase 1 finish plan: 13 → 21 Nov 2026

Official deadline **Mon 23 Nov 2026** (rechecked on the challenge page on 13 Nov; no
changes posted). Internal submit date **Sat 21 Nov**; 22–23 Nov is buffer only.

Phase 1 asks for an *initial solution*: **report + source code + demo**, on GitHub,
via the challenge form. PS1 deliverables: source code, application, demo video,
technical report. A finished product isn't expected; a **working, honest** one
is.

## The order is set by risk

1. Llama on the phone (mandatory; disqualifies if missing)
2. The end-to-end app on the phone (this is the demo)
3. Evidence: [ARM] numbers + video
4. Report + GitHub
5. Everything else

## Day by day

| Day | Goal | Done when |
| --- | --- | --- |
| **Fri 13 (tonight)** | Start the 1 GB download (GATE1 Step 1). Install Git if it's still missing. Create an empty **public** GitHub repo `AGRI-SHIELD-AI`. Copy `android/advisory/*` and `knowledge_base/tomato_tnau_v2.json` into the project. | `.pte` + tokenizer on the laptop with SHA256 noted; repo URL exists |
| **Sat 14** | **GATE 1**: wire `LlamaAdvisoryEngine`, push the model, run in airplane mode (GATE1 Steps 2–5). | Advisory streams on the phone in airplane mode; screen recording saved |
| **Sun 15** | Collect **20–30 real tomato leaf photos** (market, garden, terrace; healthy and diseased). Run the Phase 3 field test. Approve and finish Android Studio, and produce a signed debug APK. | Field-accuracy table filled with real numbers, whatever they are; APK installs fresh |
| **Mon 16** | Full pipeline on the phone: camera → classifier → gate → Llama → KB dose table → source link. Tamil disease names and UI labels. 10-run [ARM] benchmark (GATE1 Step 6). | `benchmarks/results_arm.md` complete; no number without `[ARM]` |
| **Tue 17** | Report: paste the I8MM correction; add the Llama/ExecuTorch section, KB provenance table (TNAU URLs), safety-gate design + 70-check test result, [ARM] tables, field results, limitations. | Report complete as a draft; every number traces to a file |
| **Wed 18** | Record the demo video (≤5 min): problem → airplane mode on → photo → diagnosis → Llama advisory → dose table with TNAU source → low-confidence abstain case → `/proc/cpuinfo` + stats → limitations. Have a Tamil speaker check the Tamil strings. | Video uploaded (YouTube unlisted or Drive), link works signed-out |
| **Thu 19** | GitHub: README with setup + model download URL/SHA256, LICENSE, APK on a Release, report PDF, no secrets, no `.pte` in history. Send to your faculty mentor for a look. | Fresh-clone test: README steps work on a clean folder |
| **Fri 20** | Fix mentor comments. Dry-run the submission form: check every field, link and file is ready. | Nothing left to create, only to paste |
| **Sat 21** | **Submit.** Save the confirmation screenshot/email. | Confirmation received |
| Sun 22 – Mon 23 | Buffer only. No new features. | — |

## If GATE 1 isn't passed by Sun 15 night

Switch fully to the fallback in GATE1 ("If Step 5 fails") and pause everything
else. If Llama runs as a standalone runner on the phone but isn't wired into the
app by 21 Nov, submit it that way and say so plainly in the report. The
requirement is that Llama runs on-device through ExecuTorch; seamless
integration can come in Phase 2.

## Things that must not happen

- Committing the `.pte` (over 100 MB, so the push fails) or a Hugging Face token.
- A performance number from the laptop presented as an on-device result.
- Any chemical or dose shown that isn't in `tomato_tnau_v2.json`.
- Submitting on 23 Nov itself.
