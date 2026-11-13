# AGRI-SHIELD AI — persistent project instructions

Offline crop-disease / pest detection and farmer advisory on Arm SoC.
Bharat AI-SoC Challenge 2026–27, Problem Statement 1. Solo entry: Vignesh S (Vicky), M.E. VLSI Design, CEG Anna University.

## Hard deadlines

| Milestone | Date |
| --- | --- |
| Phase 1 (Open Qualifying) submission | **23 Nov 2026** (internal target: 21 Nov) |
| Phase 1 results | Mid-Dec 2026 |
| Phase 2 (PoC) submission | 5 Feb 2027 |
| Finals (live demo + jury Q&A) | 15–16 Feb 2027 |

23 November is the **qualifying** deadline, not the final one. Phase 1 asks for an initial
solution with report, source code and demo — not a finished product.

## Mandatory requirements (non-negotiable)

1. A **Llama-family model** must own the advisory / reasoning component.
2. It must run on-device through **ExecuTorch** as the runtime.
3. It must run on **Arm hardware**, fully offline.
4. The project must be hosted on **GitHub** and submitted through the challenge form.

Target device: **Arm Android phone** (decided 30 Oct 2026). No Raspberry Pi available.
The department's NXP LPC2148 was surveyed and ruled out — ARM7TDMI-S, 40 KB SRAM, no MMU.

## Claim discipline — enforced everywhere

Every performance number carries exactly one tag:

- `[SIM]` — simulated, no hardware
- `[DESK]` — measured on an x86 development machine
- `[ARM]` — measured on the actual Arm device, offline

Only `[ARM]` numbers support the on-device claim. `benchmarks/results_desk.md` and
`benchmarks/results_arm.md` are separate files so the two can never be confused.

**Never fabricate a measurement.** If a number has not been produced by a run that
actually happened, it does not go in the report. This rule outranks completeness,
deadlines, and how good the number would look.

## Safety rule that outranks everything else

The system gives pesticide advice to farmers. Wrong advice costs money, crops, and
can harm health.

- Llama **never** invents agricultural facts. It rewords a record retrieved from the
  knowledge base and nothing else.
- Every chemical name, dose and interval in the knowledge base traces to a named
  source document (TNAU, ICAR, state agriculture department) with a URL.
- A record with no verifiable source is marked `"sourced": false` and the system
  **abstains** rather than guessing.
- Below the confidence threshold, no chemical name reaches the prompt at all. Safety
  is enforced by what the prompt contains, not by asking the model to behave.

## Architecture

```
M1 acquisition → M2 disease / M3 pest → M4 severity → confidence gate
   gate pass → M6 knowledge retrieval → M5 Llama (ExecuTorch) → M7 UI
   gate fail → abstain record (no chemicals) → M5 → M7
M8: the whole thing runs with no network.
```

## Scope lock for Phase 1

**In:** tomato / chilli / potato disease classification, 3-band severity, 8–12 pest
subset, retrieval-grounded advisory, Llama 3.2 1B via ExecuTorch on Android, Tamil +
English, local UI, Arm benchmarks.

**Out (Phase 2 or never):** Hailo / AI HAT, SWIR, custom Verilog accelerator, Llama
fine-tuning, voice I/O, full 102-class IP102, online model sync.

## Dataset discipline

- Train on PlantVillage, **evaluate on PlantDoc as a held-out field set never trained on**.
- Expect a large accuracy drop (literature reports 20–50 points; one 2026 study saw
  99.73% → 32.05%). **That drop is the finding, not a failure.**
- PlantVillage has multiple photos of the same physical leaf → **group split, never
  random split**, or test accuracy is inflated.
- Run the background-only control probe. If it scores well above chance, say so.

## Working rules

- Two Python environments, never mixed: `vision` (training) and `executorch` (export).
- Record every command that actually worked, with its version, in
  `documentation/executorch_setup.md`, the day it worked.
- Commit at every working state with a message saying what now works.
- Never commit datasets, model weights or credentials.
- Tag the submission commit `phase1-submission`.
