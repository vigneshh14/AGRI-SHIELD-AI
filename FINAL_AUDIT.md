# FINAL_AUDIT.md — archive cleanup and verification

2026-10-31. Nine items raised; all nine resolved. No model was
retrained and no frozen scientific result was altered.

---

## 1. Authoritative documents retained

`README.md`, `USER_ACTIONS.md`, `CONSISTENCY_AUDIT.md` and `PHASE1_REPORT.md`
are the single authoritative versions, together with `PHASE1_RESULTS.md`,
`PHASE1_COMPLIANCE.md`, `PHASE1_DEMO_SCRIPT.md`,
`PHASE1_SUBMISSION_CHECKLIST.md`, `REFERENCES.md` and this file.

## 2. Stale duplicates — provenance established, tombstoned

None of these were produced by the project build. Each appeared on the user's
machine after the authoritative file was written, and each is byte-identical in
size to its original.

| File | Size | Origin | Action |
| --- | --- | --- | --- |
| `README2.md` | 5,717 B | copy of `README.md`, created 64 s later | tombstoned |
| `USER_ACTIONS2.md` | 2,655 B | copy of `USER_ACTIONS.md`, created 77 s later | tombstoned |
| `CONSISTENCY_AUDIT1.md` | — | stale pre-final-pass copy | tombstoned earlier |
| `PHASE1_REPORT1.md` | — | stale pre-audit copy | tombstoned earlier |
| `reports/gen_reports.py` | 29,546 B | superseded generator | tombstoned, now raises on execution |

**On deletion.** The file-transfer mechanism available to this session writes
files but cannot delete them. Each duplicate has therefore been **overwritten
with a tombstone** explaining what it was and that it is safe to delete. None is
listed in `FILE_MANIFEST.md`; none is in the archive. The user must delete them
manually.

`reports/gen_reports.py` deserves note: it was deleted from the project during
the consistency pass precisely so two generators could not disagree about the
same numbers, but it survived on disk because writes do not propagate deletions.
Its tombstone now raises `SystemExit` rather than silently regenerating reports
from an older template.

## 3. Three manifest files absent from the archive — investigated

All three existed in the build workspace. Each was assessed on whether it is a
genuine submission artifact. **None was fabricated.**

| File | Size | Assessment | Action |
| --- | --- | --- | --- |
| `datasets/metadata/splits.csv` | 888,530 B | Genuine. The per-image group assignment record; the audit reproduces split integrity from it. | **Restored to the archive** |
| `models/mobilenet_v2_xnnpack.pte` | 13,938,208 B | Genuine file, but it is the **random-weight hello-world** model from the ExecuTorch smoke test — not the trained classifier. Shipping it beside `agrishield_tomato4.pte` invites confusion about which artifact carries trained weights. | **Excluded, with the reason recorded** |
| `logs/diagnosis_history.json` | 331 B | Runtime residue: two diagnosis entries produced by the offline test run. Not a project artifact. | **Excluded** |

Note on `splits.csv`: its path column holds build-environment paths. It is
retained as the record of group assignments and is regenerated locally by
`prepare_splits.py`; `INSTALL_NEXT.md` gives the command.

## 4. Two checksum mismatches — explained and a real bug fixed

**The two mismatches are `FILE_MANIFEST.md` and `reports/file_manifest.json`.**
A manifest cannot contain its own hash, so any checker that does not honour the
self-referential exclusion reports exactly these two. Both are now declared in
`reports/file_manifest.json` under `self_excluded`, and `FILE_MANIFEST.md` states
it in prose so an external checker's operator can recognise the result.

Separately, the audit exposed a **genuine defect in the archive filter**: it
skipped every file whose name begins with a dot, which silently dropped
`.gitignore` — a real project file. Fixed with an explicit allow-list for
project dotfiles. `environment_audit_raw.txt`, the raw Windows audit evidence,
was also missing from the archive and has been restored; the copy now included
is the complete 2,403-byte version read back from the user's machine, replacing
a 1,937-byte copy that had been captured while the audit script was still
writing.

## 5. Nested `reports.zip` — removed

A 117,133-byte `reports.zip` was present on the user's machine, created after the
last build. It is not required, was not produced by this project, and nested
archives are now excluded by extension. It is not in the submission archive.

## 6. Archive contents

57 checksummed files
plus the two self-excluded manifests. Exclusions and their reasons are tabulated
in `FILE_MANIFEST.md`.

Verified from extraction: **0 unlisted files**, **0 banned items** (no `.pt`,
`.pyc`, `.zip`, no `logs/`, no `datasets/raw/`, none of the tombstoned
duplicates), **0 duplicate entries**.

## 7. Consistency checks — 27/27 pass

`reports/consistency_check.py`, run both in the workspace and **inside the
extracted archive**. Covers: every headline figure present and matching the
authoritative JSON; the confusion diagonal and correct-prediction count; the
leakage lower-bound caveat; severity marked EXPERIMENTAL with background
sensitivity named; Arm figures declared non-existent; no sentence implying Llama
was deployed; README implemented-versus-planned separation; USER_ACTIONS dating.

## 8. Checksum verification — 57/57

Every checksummed file verified by SHA-256 against the extracted archive.

## 9. Frozen results — unchanged

| Metric | Value |
| --- | --- |
| In-domain accuracy | 0.9561966 |
| In-domain macro F1 | 0.9506470 |
| Test images / correct | 936 / 895 |
| PlantDoc primary (3-class) | 0.3914 accuracy, 0.3629 macro F1 |
| PlantDoc sensitivity (4-class) | 0.3414 accuracy |
| Random-split leakage avoided | 63.97% (lower bound) |
| `.pte` agreement with PyTorch | 60/60, max logit diff 3.457e-06 |

## Pending requirements — unchanged and preserved

- **Llama inference has never been executed on any hardware.** M1 unsatisfied.
- **Llama via ExecuTorch not started.** M3 satisfied for the vision classifier only.
- **No Arm execution.** M4 unsatisfied; `benchmarks/results_arm.md` is empty and
  stays empty until a measurement exists.
- **GitHub publication pending** — Git not installed as of the last verified audit.
- Severity remains EXPERIMENTAL; background sensitivity unresolved.
- Knowledge base holds 0 source-verified chemical interventions; every advisory
  abstains.
- Field accuracy 39.1%. Not fit for unsupervised field use.
