# Verification report — 30 Oct 2026

Everything below was re-executed from scratch this session. No claim here rests
on an earlier terminal message.

## CRITICAL: two environments, do not confuse them

| | Windows laptop (`vibewithvickyy`) | Build sandbox (Linux) |
| --- | --- | --- |
| Role | project home, where YOU work | where Claude verifies before handing over |
| Python / ExecuTorch | **none installed — not yet audited** | 3.11.18 / executorch 1.5.1 |
| `.pte` artifact | **none** | present, re-created this session |
| Trained checkpoint | **none** | smoke-test checkpoint only |

The versions quoted in earlier messages (Python 3.11.18, torch 2.15.0,
torchvision 0.29.2, executorch 1.5.1) are the **sandbox's**. Nothing is yet
installed on the Windows laptop. `device_bash` is a Linux VM with your folders
mounted — it is **not** a Windows shell.

## Re-verified this session

| Check | Result |
| --- | --- |
| Package versions via `importlib.metadata` | python 3.11.18, executorch 1.5.1, torch 2.15.0, torchvision 0.29.2, numpy 2.4.6, pillow 13.0.0 |
| `.pte` export, from a deleted start | PASS — 13.94 MB written |
| ExecuTorch runtime load + execute | PASS — output shape `(1, 1000)` |
| Desktop latency, 20 runs | median 5.0 ms, mean 5.2, min 4.6, max 7.4 `[DESK]` |
| Split script, synthetic fixture | PASS — 90/90 groups, 0 straddle violations |
| Split script, real PlantVillage | PASS — 0 straddle violations |
| Training pipeline, end to end | PASS — checkpoint, metrics.json, 2 PNGs produced |
| Files on laptop | 13 present and readable |

**Reproducibility caveat found:** re-running the export produced a different
SHA256 (`7a14df69` then `81d5cf3d`). Cause: ImageNet weights cannot be
downloaded in the sandbox, so the backbone is randomly initialised each run.
With pretrained weights the export is deterministic. This is a sandbox
limitation, not a code defect.

## Real dataset acquired

4 tomato classes from `spMohanty/PlantVillage-Dataset` via a sparse, shallow
git clone (only route available — direct HTTP to GitHub, Hugging Face, Kaggle
and download.pytorch.org are all blocked by the sandbox proxy).

| Class | Images |
| --- | --- |
| Tomato___Early_blight | 1,000 |
| Tomato___Late_blight | 1,909 |
| Tomato___Septoria_leaf_spot | 1,771 |
| Tomato___healthy | 1,591 |
| **Total** | **6,271** (116 MB) |

## Two assumptions this session DISPROVED

### 1. Filename prefixes do not group PlantVillage images

Sample: `0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B 8389.JPG`. The prefix
before `___` is a per-image UUID. The filename signal groups nothing on this
dataset. Kept in the code for datasets that do use a shared prefix.

### 2. RETRACTED — "the colour subset has almost no detectable near-duplicates"

**This section's original conclusion was WRONG and is retracted
(2026-10-31).**

It reported that perceptual hashing found ~1.006 images per group and inferred
that `raw/color` carried little duplication, attributing PlantVillage's known
duplication to cross-directory colour/grayscale/segmented variants instead.

The dataset's own human-annotated `leaf-map.json` shows **4.00 files per physical
leaf within `raw/color`**, and a random split leaks
**63.97%** of test images. Perceptual hashing
missed this because an 8x8 grayscale gradient is destroyed by rotation; the four
views of a leaf are rotated and reflected. A rotation-invariant descriptor
separates same-leaf from different-leaf at AUC 0.963 where dHash is at chance.

Full evidence and the retraction rationale: `CONSISTENCY_AUDIT.md` §2.

The hash-threshold sweep table that followed is retained below as a record of
the failed method, not as a finding about the dataset.


Hamming-threshold sweep over all 6,271 images:

| Threshold | Groups | Images/group | Hash links | Largest group | Naive-split leak |
| --- | --- | --- | --- | --- | --- |
| 0 | 6,257 | 1.002 | 14 | 2 | 0.11% |
| 3 | 6,254 | 1.003 | 17 | 2 | 0.21% |
| **5** | **6,235** | **1.006** | **36** | **3** | **0.64%** |
| 8 | 5,966 | 1.051 | 334 | 50 | 6.38% |
| 12 | 3,547 | 1.768 | 6,660 | **769** | 44.74% |

The largest group exploding to 769 at threshold 12 is union-find transitive
closure chaining unrelated leaves (A~B, B~C, therefore A~C), not duplicate
recovery. A looser threshold is **not** safer.


(Original erroneous conclusion removed; see the retraction above.)
