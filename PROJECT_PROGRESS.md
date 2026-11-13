# Project progress — HISTORICAL SESSION LOG

> **This file is a dated append-only log, not a status report.**
> Entries below record what was true on the date in their heading. Earlier
> entries contain figures and conclusions that later sessions corrected or
> retracted — they are preserved deliberately.
>
> **For current status, read these instead:**
> `README.md` (what is implemented vs planned) ·
> `PHASE1_COMPLIANCE.md` (requirement-by-requirement) ·
> `PHASE1_RESULTS.md` (authoritative figures) ·
> `CONSISTENCY_AUDIT.md` (what was retracted and why) ·
> `USER_ACTIONS.md` (what is blocked on you).
>
> Authoritative headline as of 2026-10-31:
> in-domain accuracy **0.9561966**, macro F1 **0.9506470**;
> field accuracy **0.3914**; **no Llama inference and no Arm execution have
> occurred**.

---


## 30 Oct 2026 — session 1 (historical entry, superseded by later sessions)

### Done
- Official PS1 requirements read and verified against the challenge site.
  **Key finding: 23 Nov is the Phase 1 qualifying deadline, not the final
  submission.** Phase 2 PoC is due 5 Feb 2027; finals 15–16 Feb 2027.
- Target hardware decided: **Arm Android phone**. No Raspberry Pi available.
  Department LPC2148 surveyed and ruled out (ARM7TDMI-S, 40 KB SRAM, no MMU).
- Repository scaffolded with the full module structure.
- `prepare_splits.py` written **and tested** on a synthetic 180-image / 90-leaf
  dataset: 90 groups recovered exactly, 0 group-straddle violations, and the
  naive-split contamination metric fired correctly (59.26% on that fixture).
- ExecuTorch hello-world scripts written **and executed successfully** in a
  Linux sandbox: export produced a 13.94 MB `.pte`, the runtime loaded it and
  returned output shape `(1, 1000)`, median latency 5.9 ms `[DESK]`.
  Working stack: **executorch 1.5.1**, torch 2.15.0, Python 3.11.18.
  Gotchas recorded in `documentation/executorch_setup.md` — notably that
  `executorch.__version__` does not exist in 1.5.1.

### In progress
- Nothing blocking in the sandbox. Next step moves to the laptop and the phone.

### Blocked
- **Llama weights**: Meta licence access on Hugging Face not yet requested.
  This is on the critical path — request it immediately.
- **Windows environment audit**: CPU/RAM/GPU/Python on the laptop not yet
  inspected. The device Linux VM was still downloading at session end.
- **Phone**: USB debugging not yet enabled; no device attached.

### Next actions
1. Request Llama 3.2 licence access on Hugging Face.
2. Confirm challenge registration + faculty mentor are on record.
3. Complete the Windows environment audit.
4. Run `export_hello.py` / `run_hello.py` on the laptop; record versions in
   `documentation/executorch_setup.md`.
5. Get a Llama `.pte` running through the ExecuTorch runner on the phone — GATE 1.


## 30 Oct 2026 — session 3 (historical entry, superseded by later sessions)

### Done
- **Windows audit complete** (`audit_windows.bat` executed via computer use).
  i3-1215U, 6C/8T, 7.73 GB RAM, Intel UHD (no CUDA), Win 11 build 26200,
  Python 3.13.15. **Git, adb and WSL all missing.**
- Real dataset acquired: 6,271 PlantVillage tomato images, 4 classes, 116 MB,
  via sparse shallow git clone.
- `prepare_splits.py` v2: Hamming-tolerant grouping across 3 orientations.
  Threshold sweep run on real data.
- `train.py` written and smoke-tested end to end on real images.
- **Knowledge base built with its safety gate, and the gate is tested.**
  `retrieval.py --self-test` passes 6 abstain cases plus a positive and a
  negative control. No chemical text can reach the prompt below threshold or
  from an unverified record.
- Android deployment plan written; `probe_phone.bat` ready to profile the device.

### Blocked on user
Git, adb, Llama licence, registration confirmation, phone USB debugging.

### Deliberately incomplete
`knowledge_base/diseases.json` has **zero verified chemical interventions**.
TNAU's site is not reachable from this session, so every record carries
`sourced: false` and the system abstains. Populating those fields requires a
human reading the cited TNAU page. This is correct behaviour, not a gap to
paper over.


## 30 Oct 2026 — session 4 (historical entry, superseded by later sessions)

### Completed
- **Priority 1 fully done.** Dataset acquired (6,271 images), leakage-proof
  splits via the dataset's OWN `leaf-map.json`, MobileNetV2 trained 22 epochs,
  **test accuracy 0.9562, macro F1 0.9506** (corrected 10-31; the earlier
  0.9615/0.9563 was measured on the final-epoch model, not the deployed
  checkpoint), unseen spot check 13/14,
  exported to an 8.89 MB ExecuTorch `.pte` that loads and runs.
- **Priority 3 done except real inference.** `llama_advisory/advisor.py` with
  structured request/response schemas, EN + TA prompt templates, a MockBackend
  and an ExecuTorchBackend that refuses to construct without a real `.pte`.
  Output guard added as a second safety layer.
- **Priority 4 done.** `application/app.py` — stdlib http.server, zero
  dependencies, zero external requests. Upload, predict, confidence, severity,
  advisory, EN/TA toggle, history. Verified end to end.

### The session's most important finding
The repo ships `leaf-map.json` with ground-truth leaf IDs. PlantVillage
photographs each leaf ~4 times. **A random split leaks 63.97% of test images.**
The earlier perceptual-hash estimate of 0.64% was a hundredfold underestimate.

### Still blocked on hardware or the user
Git, adb, Llama licence, registration confirmation, phone, Tamil review.


## 2026-10-31 — session 6 (current)

### Documentation correction pass
- `README.md` rewritten: removed the statement that Llama runs through
  ExecuTorch on device; added an implemented-versus-planned split; corrected the
  splitting description to human-annotated leaf-ID grouping; stated that the
  advisory always abstains because 0 chemical records are source-verified.
- `USER_ACTIONS.md` rewritten: completed Windows audit removed; Git and adb
  status reported as of the last verified audit with an explicit note that it is
  unconfirmed since.
- This file re-headed as a dated historical log so earlier entries cannot be
  mistaken for current status.
- `CONSISTENCY_AUDIT1.md` identified on the user's machine as a stale duplicate.

### No experimental change
No model was retrained and no result was recomputed in this session.
