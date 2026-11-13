# Implementation log

## 2026-10-30, session 2

**Implemented**
- `disease_detection/training/train.py` — MobileNetV2 training from a split
  manifest. Accuracy / macro P / R / F1, confusion matrix, training curves,
  checkpointing, and a hard `SMOKE_TEST_ONLY` stamp when the backbone is not
  pretrained.
- `prepare_splits.py` rewritten: Hamming-tolerant near-duplicate grouping across
  three orientations (original, h-flip, 180°), vectorised via matrix products.
  Added group-size histogram and largest-group diagnostics.

**Commands run**
- `git init` + sparse shallow fetch of 4 tomato classes from PlantVillage
- `prepare_splits.py` at Hamming 0, 3, 5, 8, 12 over 6,271 images
- `train.py --smoke --epochs 2 --img-size 96 --limit-per-split 240`
- `uv pip install matplotlib`

**Errors hit and fixed**
1. `torchvision` pretrained download → `URLError` (proxy 403). Added a
   loud random-init fallback that stamps every artifact.
2. Exact dHash grouped nothing on real data (1.002 images/group). Root cause:
   duplicate views are rotated/mirrored. Fixed with three-orientation hashing
   plus Hamming tolerance.
3. `python -m pip` absent in the uv-created venv → used `uv pip install`.
4. Earlier file count reported as 16; actual is 13. Corrected.

**Findings for the report**
- Threshold sweep shows transitive-closure chaining above Hamming 8.
- PlantVillage `color` has far less intra-variant duplication than assumed.
- ExecuTorch runtime probes the Arm MIDR register at load — Arm feature
  detection is compiled in, and what it reports on the phone is worth capturing.

**Next**
- Windows environment audit (needs computer-use approval)
- Real training with ImageNet weights on the laptop
- Knowledge base sourcing from TNAU / ICAR
