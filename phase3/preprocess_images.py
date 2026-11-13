#!/usr/bin/env python3
"""
AGRI-SHIELD AI — Phase 3 real-image preprocessing.

Turns real tomato-leaf photographs into the exact [1,3,96,96] float32 tensors
the trained model expects, in the binary format the Phase 2 Arm runner reads.

The transform is NOT invented here. It is copied from the training code
(`train.py` eval_tf, `predict.py` preprocess, `external_eval.py`), which are
identical to one another:

    Resize(int(96 * 1.14) == 109)   # shorter side, aspect preserved, BILINEAR
    CenterCrop(96)
    ToTensor()                      # HWC uint8 [0,255] -> CHW float32 [0,1]
    Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])

See PHASE3_PREPROCESSING_AUDIT.md for the provenance of every constant.

ONE deliberate deviation: EXIF orientation is applied. The training code does
not do this, because PlantVillage files carry no EXIF orientation tag — so it
is a no-op on the training distribution. Phone cameras DO write that tag, and
without it a portrait photo reaches the model rotated 90 degrees. Declared in
the audit, recorded per-image in the manifest.

Usage:
    python preprocess_images.py --images photos/ --outdir out/
    python preprocess_images.py --verify        # check against torchvision
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

# ----------------------------------------------------------------- constants
# Every value below is read from the training code. Do not edit without
# re-running the preprocessing audit.
IMG_SIZE = 96
RESIZE_SHORT = int(IMG_SIZE * 1.14)          # 109
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
CLASSES = [
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Septoria_leaf_spot",
    "Tomato___healthy",
]
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif"}

# Below this fraction of the original frame surviving the centre crop, the
# image is flagged: a lesion outside the central square is invisible to the
# model, and the brief forbids cropping symptoms away silently.
RETENTION_WARN = 0.60


# ------------------------------------------------------- torchvision parity
def resize_shorter_side(img: Image.Image, size: int) -> Image.Image:
    """Replicates torchvision F.resize(img, size) for a PIL input and an int size.

    torchvision computes the output as: shorter side -> size, longer side
    scaled by int(size * long / short), then calls PIL resize with BILINEAR.
    """
    w, h = img.size
    short, long_ = (w, h) if w <= h else (h, w)
    if short == size:
        return img                                  # torchvision early-returns
    new_short = size
    new_long = int(size * long_ / short)
    new_w, new_h = (new_short, new_long) if w <= h else (new_long, new_short)
    return img.resize((new_w, new_h), Image.BILINEAR)


def center_crop(img: Image.Image, size: int) -> Image.Image:
    """Replicates torchvision F.center_crop for a PIL input."""
    w, h = img.size
    if w < size or h < size:                        # torchvision pads with 0
        pad_l = max((size - w) // 2, 0)
        pad_t = max((size - h) // 2, 0)
        pad_r = max(size - w - pad_l, 0)
        pad_b = max(size - h - pad_t, 0)
        img = ImageOps.expand(img, (pad_l, pad_t, pad_r, pad_b), fill=0)
        w, h = img.size
    top = int(round((h - size) / 2.0))
    left = int(round((w - size) / 2.0))
    return img.crop((left, top, left + size, top + size))


def to_tensor_normalize(img: Image.Image) -> np.ndarray:
    """ToTensor() then Normalize(), as float32 CHW."""
    a = np.asarray(img, dtype=np.uint8)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"expected HxWx3 RGB, got shape {a.shape}")
    x = a.astype(np.float32) / 255.0               # ToTensor
    x = (x - MEAN) / STD                           # Normalize (HWC broadcast)
    return np.ascontiguousarray(x.transpose(2, 0, 1))   # HWC -> CHW


def preprocess_one(path: Path, apply_exif: bool = True) -> tuple[np.ndarray, dict]:
    """Full pipeline for one photograph. Returns (CHW float32 tensor, record)."""
    with Image.open(path) as im:
        orig_w, orig_h = im.size
        orig_mode = im.mode
        exif_applied = False
        if apply_exif:
            before = im.size
            im = ImageOps.exif_transpose(im)
            exif_applied = (im.size != before) or _has_orientation(path)
        rgb = im.convert("RGB")
        w, h = rgb.size

        resized = resize_shorter_side(rgb, RESIZE_SHORT)
        rw, rh = resized.size
        cropped = center_crop(resized, IMG_SIZE)
        tensor = to_tensor_normalize(cropped)

    retained = (IMG_SIZE * IMG_SIZE) / float(rw * rh) if rw * rh else 0.0
    rec = {
        "filename": path.name,
        "original_width": orig_w,
        "original_height": orig_h,
        "original_mode": orig_mode,
        "aspect_ratio": round(max(orig_w, orig_h) / max(min(orig_w, orig_h), 1), 4),
        "exif_orientation_applied": exif_applied,
        "size_after_exif": f"{w}x{h}",
        "size_after_resize": f"{rw}x{rh}",
        "retained_area_fraction": round(retained, 4),
        "retention_flag": "LOW_RETENTION" if retained < RETENTION_WARN else "ok",
        "tensor_shape": "1x3x96x96",
        "tensor_dtype": "float32",
        "sha256_original": _sha256(path),
    }
    return tensor, rec


def _has_orientation(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            return bool(ex and ex.get(274, 1) not in (1, None))
    except Exception:
        return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------- binary writer
def write_tensor_bin(tensors: list[np.ndarray], out: Path) -> None:
    """The exact format the Phase 2 Arm runner reads:
       int32 n, int32 C, int32 H, int32 W, then n*C*H*W float32 little-endian.
    """
    n = len(tensors)
    with open(out, "wb") as f:
        f.write(struct.pack("<4i", n, 3, IMG_SIZE, IMG_SIZE))
        for t in tensors:
            if t.shape != (3, IMG_SIZE, IMG_SIZE):
                raise ValueError(f"bad tensor shape {t.shape}")
            if t.dtype != np.float32:
                raise ValueError(f"bad dtype {t.dtype}")
            f.write(t.astype("<f4").tobytes())


# ------------------------------------------------------------- verification
def verify_against_torchvision() -> int:
    """Compare this implementation against torchvision on random images.

    This is the whole point of the exercise: the pipeline must reproduce the
    training-time transform, not merely resemble it.
    """
    try:
        import torch
        from torchvision import transforms
    except ImportError:
        print("torchvision not available — cannot verify. NOT a pass.")
        return 2

    tf = transforms.Compose([
        transforms.Resize(RESIZE_SHORT),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN.tolist(), STD.tolist()),
    ])

    rng = np.random.default_rng(20261031)
    sizes = [(640, 480), (480, 640), (4000, 3000), (3000, 4000),
             (1920, 1080), (256, 256), (109, 109), (100, 130), (97, 96)]
    worst = 0.0
    results = []
    for (w, h) in sizes:
        arr = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")

        ref = tf(img).numpy()
        mine = to_tensor_normalize(center_crop(resize_shorter_side(img, RESIZE_SHORT),
                                               IMG_SIZE))
        d = float(np.abs(ref - mine).max())
        worst = max(worst, d)
        results.append({"size": f"{w}x{h}", "max_abs_diff": d,
                        "exact": bool(np.array_equal(ref, mine))})
        print(f"  {w:>5}x{h:<5}  max|diff| = {d:.3e}   "
              f"{'EXACT' if np.array_equal(ref, mine) else 'differs'}")

    print(f"\nworst max|diff| across {len(sizes)} geometries: {worst:.3e}")
    ok = worst == 0.0
    print("VERDICT:", "BIT-EXACT match with torchvision" if ok
          else "MISMATCH — do not use this pipeline")
    Path("preprocess_verification.json").write_text(json.dumps(
        {"bit_exact": ok, "worst_max_abs_diff": worst, "cases": results,
         "torchvision": __import__("torchvision").__version__,
         "transform": {"resize_shorter_side": RESIZE_SHORT,
                       "center_crop": IMG_SIZE,
                       "mean": MEAN.tolist(), "std": STD.tolist(),
                       "interpolation": "BILINEAR"}}, indent=2))
    return 0 if ok else 1


# -------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", help="directory of photographs, or a single file")
    ap.add_argument("--outdir", default="out", help="where tensors/manifest go")
    ap.add_argument("--no-exif", action="store_true",
                    help="skip EXIF orientation (matches training code literally)")
    ap.add_argument("--verify", action="store_true",
                    help="verify against torchvision and exit")
    args = ap.parse_args()

    if args.verify:
        return verify_against_torchvision()

    if not args.images:
        ap.error("--images is required unless --verify is given")

    src = Path(args.images)
    files = sorted([p for p in ([src] if src.is_file() else src.rglob("*"))
                    if p.is_file() and p.suffix.lower() in EXTS])
    if not files:
        print(f"No images found under {src}")
        print(f"Recognised extensions: {' '.join(sorted(EXTS))}")
        return 1

    outdir = Path(args.outdir)
    originals = outdir / "originals"
    outdir.mkdir(parents=True, exist_ok=True)
    originals.mkdir(exist_ok=True)

    tensors, records, failures = [], [], []
    for p in files:
        try:
            t, rec = preprocess_one(p, apply_exif=not args.no_exif)
        except Exception as e:                      # never silently skip
            failures.append({"filename": p.name, "error": f"{type(e).__name__}: {e}"})
            print(f"  FAILED  {p.name}: {type(e).__name__}: {e}")
            continue
        rec["index"] = len(tensors)
        # every original is preserved, untouched
        shutil.copy2(p, originals / p.name)
        tensors.append(t)
        records.append(rec)
        flag = "  <-- LOW RETENTION" if rec["retention_flag"] != "ok" else ""
        print(f"  [{rec['index']:>2}] {p.name:<34} "
              f"{rec['original_width']}x{rec['original_height']} -> "
              f"{rec['size_after_resize']} -> 96x96   "
              f"kept {rec['retained_area_fraction']*100:5.1f}%"
              f"{'  EXIF' if rec['exif_orientation_applied'] else ''}{flag}")

    if not tensors:
        print("\nNo images preprocessed successfully.")
        return 1

    binp = outdir / "real_image_inputs.bin"
    write_tensor_bin(tensors, binp)

    manifest = outdir / "real_image_manifest.csv"
    cols = ["index", "filename", "original_width", "original_height",
            "original_mode", "aspect_ratio", "exif_orientation_applied",
            "size_after_exif", "size_after_resize", "retained_area_fraction",
            "retention_flag", "tensor_shape", "tensor_dtype", "sha256_original",
            "declared_label", "label_source", "lighting", "background",
            "ambiguous", "notes"]
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        for r in records:
            # Label columns are left EMPTY on purpose. A label must come from
            # the person who took the photograph or from an independent source,
            # never from the model's own prediction.
            for k in ("declared_label", "label_source", "lighting",
                      "background", "ambiguous", "notes"):
                r.setdefault(k, "")
            wr.writerow(r)

    stats = {
        "n_images": len(tensors),
        "n_failed": len(failures),
        "failures": failures,
        "tensor_bin": str(binp),
        "tensor_bin_sha256": _sha256(binp),
        "low_retention_count": sum(1 for r in records
                                   if r["retention_flag"] != "ok"),
        "exif_applied_count": sum(1 for r in records
                                  if r["exif_orientation_applied"]),
        "transform": {"resize_shorter_side": RESIZE_SHORT,
                      "center_crop": IMG_SIZE,
                      "mean": MEAN.tolist(), "std": STD.tolist(),
                      "interpolation": "BILINEAR",
                      "exif_transpose": not args.no_exif},
        "classes": CLASSES,
    }
    (outdir / "preprocess_summary.json").write_text(json.dumps(stats, indent=2))

    print(f"\n  {len(tensors)} image(s) -> {binp}")
    print(f"  manifest  -> {manifest}")
    print(f"  originals -> {originals}/")
    if stats["low_retention_count"]:
        print(f"\n  WARNING: {stats['low_retention_count']} image(s) lost more than "
              f"{int((1-RETENTION_WARN)*100)}% of the frame to the centre crop.")
        print("  Lesions outside the central square are invisible to the model.")
        print("  Re-shoot with the leaf centred and filling the frame, square if possible.")
    print("\n  Label columns in the manifest are intentionally blank — fill them in")
    print("  from your own knowledge of each photograph. Never from the prediction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
