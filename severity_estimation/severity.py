#!/usr/bin/env python3
"""
M4 severity estimation, and the tests that decide whether to trust it.

The bug this file fixes
-----------------------
The first version scored a HEALTHY leaf as "moderate". Root cause: the lesion
mask was defined as "leaf pixel that is not green and not bright", i.e.

    lesion = leaf & ~(60 <= hue <= 170) & (value < 0.80)

That catches shadows between leaflets, dark-green veins, specular edges and
anything slightly blue — none of which are lesions. On a healthy leaf with
uneven studio lighting it accumulated enough pixels to cross 10%.

The fix narrows the mask to the colours lesions actually are — yellow through
brown, roughly hue 10-55 degrees, with real saturation — and adds a dark-necrosis
term that requires brown hue rather than mere darkness. Shadows are excluded by
requiring saturation above a floor.

Honesty rule kept throughout: this is a PROXY, not a validated phytopathological
severity score. Thresholds are conventional and have never been calibrated
against expert-scored ground truth, because no severity-labelled data was
available. `reliable` is False whenever the estimate should not be shown as a
finding.

    python severity.py --self-test --manifest datasets/metadata/splits.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

MILD, MODERATE = 0.10, 0.30


def _hsv(rgb: np.ndarray):
    mx, mn = rgb.max(2), rgb.min(2)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(v)
    m = mx == r; h[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g; h[m] = ((b - r)[m] / d[m]) + 2
    m = mx == b; h[m] = ((r - g)[m] / d[m]) + 4
    return h * 60.0, s, v


def estimate_severity(path: Path | None = None, image: Image.Image | None = None,
                      predicted_class: str | None = None) -> dict:
    if image is None:
        with Image.open(path) as im:
            image = im.convert("RGB").copy()
    rgb = np.asarray(image.convert("RGB").resize((256, 256)), dtype=np.float32) / 255.0
    h, s, v = _hsv(rgb)

    leaf = (s > 0.18) & (v > 0.12)
    leaf_px = int(leaf.sum())
    if leaf_px < 1500:
        return {"severity": "unknown", "lesion_fraction": None, "reliable": False,
                "reason": "leaf area too small to segment reliably",
                "leaf_pixels": leaf_px}

    # lesions are yellow -> brown with genuine saturation; shadows are not
    chlorotic = (h >= 25) & (h < 60) & (s > 0.35) & (v > 0.35)      # yellowing
    necrotic = (h >= 8) & (h < 25) & (s > 0.30) & (v > 0.12)        # brown
    dark_necrosis = (h >= 8) & (h < 40) & (s > 0.25) & (v <= 0.35)  # dark brown
    lesion = leaf & (chlorotic | necrotic | dark_necrosis)

    frac = float(lesion.sum()) / leaf_px
    band = "mild" if frac < MILD else ("moderate" if frac < MODERATE else "severe")

    out = {
        "severity": band, "lesion_fraction": round(frac, 4),
        "leaf_pixels": leaf_px, "reliable": True,
        "method": "HSV chlorosis+necrosis fraction of leaf area",
        "thresholds": {"mild<": MILD, "moderate<": MODERATE},
        "note": ("ESTIMATE, not a validated phytopathological score. Thresholds are "
                 "conventional and uncalibrated — no severity-labelled ground truth "
                 "was available."),
    }

    # a leaf classified healthy has no lesions by definition; a nonzero severity
    # there is a contradiction, so suppress rather than display it
    if predicted_class and predicted_class.endswith("healthy"):
        out.update(severity="n/a", reliable=False,
                   reason="classified healthy; severity is not meaningful and is suppressed",
                   raw_lesion_fraction=out["lesion_fraction"])
    return out


# --------------------------------------------------------------------------
def self_test(manifest: str, n: int = 40) -> int:
    rows = list(csv.DictReader(open(manifest, newline="", encoding="utf-8")))
    test = [r for r in rows if r["split"] == "test"]
    by = defaultdict(list)
    for r in test:
        by[r["label"]].append(r)
    rng = random.Random(11)
    fails = []

    print("=== severity by true class (test images) ===")
    stats = {}
    for label in sorted(by):
        sample = rng.sample(by[label], min(n, len(by[label])))
        fracs, bands = [], defaultdict(int)
        for r in sample:
            s = estimate_severity(Path(r["path"]))
            if s["lesion_fraction"] is not None:
                fracs.append(s["lesion_fraction"])
            bands[s["severity"]] += 1
        med = float(np.median(fracs)) if fracs else 0.0
        stats[label] = {"median_lesion_fraction": round(med, 4),
                        "bands": dict(bands), "n": len(sample)}
        print(f"  {label.replace('Tomato___',''):<22} median={med:.4f}  {dict(bands)}")

    print("\n=== TEST: healthy leaves should read mild ===")
    hb = stats["Tomato___healthy"]["bands"]
    hn = stats["Tomato___healthy"]["n"]
    mild_rate = hb.get("mild", 0) / hn
    ok = mild_rate >= 0.80
    print(f"  [{'PASS' if ok else 'FAIL'}] {hb.get('mild',0)}/{hn} healthy leaves "
          f"scored mild ({mild_rate:.0%})")
    if not ok:
        fails.append("healthy leaves not reliably mild")

    print("\n=== TEST: healthy prediction suppresses severity entirely ===")
    r = rng.choice(by["Tomato___healthy"])
    s = estimate_severity(Path(r["path"]), predicted_class="Tomato___healthy")
    ok = s["severity"] == "n/a" and not s["reliable"]
    print(f"  [{'PASS' if ok else 'FAIL'}] severity={s['severity']} reliable={s['reliable']}")
    if not ok:
        fails.append("healthy suppression failed")

    print("\n=== TEST: diseased leaves score higher than healthy ===")
    hmed = stats["Tomato___healthy"]["median_lesion_fraction"]
    for label in ("Tomato___Early_blight", "Tomato___Late_blight",
                  "Tomato___Septoria_leaf_spot"):
        dmed = stats[label]["median_lesion_fraction"]
        ok = dmed > hmed
        print(f"  [{'PASS' if ok else 'FAIL'}] {label.replace('Tomato___',''):<22} "
              f"{dmed:.4f} vs healthy {hmed:.4f}")
        if not ok:
            fails.append(f"{label} not above healthy")

    print("\n=== TEST: robustness to lighting ===")
    r = rng.choice(by["Tomato___Late_blight"])
    with Image.open(r["path"]) as im:
        base = im.convert("RGB").copy()
    ref = estimate_severity(image=base)["lesion_fraction"]
    for name, factor in (("dim x0.6", 0.6), ("bright x1.5", 1.5)):
        alt = ImageEnhance.Brightness(base).enhance(factor)
        got = estimate_severity(image=alt)["lesion_fraction"]
        drift = abs(got - ref)
        ok = drift < 0.15
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<12} {ref:.4f} -> {got:.4f} "
              f"(drift {drift:.4f})")
        if not ok:
            fails.append(f"lighting drift {name}")

    print("\n=== TEST: background interference ===")
    canvas = Image.new("RGB", (512, 512), (120, 90, 60))     # soil-like surround
    canvas.paste(base.resize((256, 256)), (128, 128))
    got = estimate_severity(image=canvas)["lesion_fraction"]
    print(f"  [INFO] lesion fraction on a soil background: {ref:.4f} -> {got:.4f}")
    print("         (PlantVillage has uniform backgrounds; field images do not. "
          "This is a known weakness, reported not hidden.)")

    print()
    if fails:
        print(f"FAILED: {fails}")
        return 1
    print("ALL PASS")
    print("Reminder: passing these tests does NOT make severity a validated "
          "measurement. It remains an uncalibrated proxy.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--manifest", default="datasets/metadata/splits.csv")
    ap.add_argument("--image")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(self_test(a.manifest))
    if a.image:
        print(json.dumps(estimate_severity(Path(a.image)), indent=2))
    else:
        ap.print_help()
