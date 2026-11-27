#!/usr/bin/env python3
"""
Leakage-proof train/val/test splitting for PlantVillage.

The finding that drives this file
---------------------------------
PlantVillage photographs each physical leaf roughly FOUR times. A random split
puts some of those views in train and others in test, so the model is tested on
leaves it memorised. Measured on the 4-class tomato subset (6,271 images):

    a random 70/15/15 split leaks 63.87% of test images.

Three grouping signals, applied in priority order:

  1. OFFICIAL leaf map. The dataset ships `leaf-map.json` mapping each image's
     filename suffix to "Class:::LeafID". This is ground truth. Covers 3,918
     of 6,271 images here (62.5%).
  2. DECIMAL heuristic. Images from other photo sources are named like
     'gh_hl leaf 173.2' where 173 is the leaf and .2 the shot index. Grouping
     on the integer part recovers 414 more.
  3. PERCEPTUAL HASH. Last resort for whatever remains.

Signal 3 alone is NOT sufficient and this is worth stating plainly: hashing
found 1.006 images per group where the truth is 4.14, because the four views of
one leaf are shot at different angles and simply do not hash alike. A
hash-only pipeline would have reported a clean split and an inflated accuracy.

Images with no grouping signal become singleton groups. That is optimistic —
some of them certainly do share leaves — so the reported contamination is a
LOWER bound. The summary reports coverage per signal so the report can say so.

Usage
-----
    python prepare_splits.py --root <dataset>/raw/color \
                             --leaf-map <dataset>/leaf-map.json \
                             --out datasets/metadata
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
DECIMAL_RE = re.compile(r"^(.*?)(\d+)\.(\d+)$")


def _dhash_bits(im: Image.Image, size: int = 8) -> np.ndarray:
    g = im.convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten().astype(np.uint8)


def dhash(path: Path) -> np.ndarray | None:
    try:
        with Image.open(path) as im:
            im.load()
            return _dhash_bits(im)
    except Exception:
        return None


def assign_groups(records: list[dict], leaf_map: dict, use_hash: bool,
                  threshold: int) -> dict:
    """Set records[i]['group'] and ['group_source']. Returns coverage counts."""
    for r in records:
        stem = Path(r["path"]).stem
        key = stem.split("___", 1)[1].lower() if "___" in stem else None
        entry = leaf_map.get(key) if key else None
        if entry:
            cls, leaf = entry[0].split(":::")
            r["group"], r["group_source"] = ("official", cls, leaf), "official"
            continue
        m = DECIMAL_RE.match(key) if key else None
        if m:
            r["group"] = ("decimal", r["label"], f"{m.group(1)}{m.group(2)}")
            r["group_source"] = "decimal"
            continue
        r["group"], r["group_source"] = ("single", r["label"], stem), "ungrouped"

    if use_hash:
        rest = defaultdict(list)
        for i, r in enumerate(records):
            if r["group_source"] == "ungrouped":
                rest[r["label"]].append(i)
        merged = 0
        for idxs in rest.values():
            bits, keep = [], []
            for i in idxs:
                h = dhash(Path(records[i]["path"]))
                if h is not None:
                    bits.append(h)
                    keep.append(i)
            if len(keep) < 2:
                continue
            B = np.stack(bits).astype(np.int16)
            d = B @ (1 - B).T + (1 - B) @ B.T
            np.fill_diagonal(d, 65)
            for a, b in np.argwhere(d <= threshold):
                if a < b:
                    ga = records[keep[a]]["group"]
                    if records[keep[b]]["group"] != ga:
                        records[keep[b]]["group"] = ga
                        records[keep[b]]["group_source"] = "hash"
                        merged += 1
        if merged:
            print(f"  hash merged {merged} additional image(s)")

    canon: dict = {}
    for r in records:
        if r["group"] not in canon:
            canon[r["group"]] = len(canon)
        r["group_id"] = canon[r["group"]]
    return dict(Counter(r["group_source"] for r in records))


def split_by_group(records: list[dict], seed: int, ratios=(0.70, 0.15, 0.15)) -> None:
    rng = random.Random(seed)
    by_class = defaultdict(lambda: defaultdict(int))
    for r in records:
        by_class[r["label"]][r["group_id"]] += 1

    assign: dict[int, str] = {}
    for groups in by_class.values():
        gids = sorted(groups)
        rng.shuffle(gids)
        n = sum(groups.values())
        target = dict(zip(("train", "val", "test"), (r * n for r in ratios)))
        run = {"train": 0, "val": 0, "test": 0}
        for g in gids:
            pick = max(target, key=lambda s: target[s] - run[s])
            assign[g] = pick
            run[pick] += groups[g]
    for r in records:
        r["split"] = assign[r["group_id"]]


def naive_contamination(records: list[dict], seed: int) -> dict:
    rng = random.Random(seed)
    sh = records[:]
    rng.shuffle(sh)
    n = len(sh)
    c1, c2 = int(0.70 * n), int(0.85 * n)
    naive = {r["path"]: ("train" if i < c1 else "val" if i < c2 else "test")
             for i, r in enumerate(sh)}
    train_g = {r["group_id"] for r in records if naive[r["path"]] == "train"}
    test = [r for r in records if naive[r["path"]] == "test"]
    leak = sum(1 for r in test if r["group_id"] in train_g)
    return {"naive_test_images": len(test), "naive_leaked": leak,
            "naive_test_contamination_pct": round(100 * leak / max(1, len(test)), 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--leaf-map", default=None,
                    help="path to leaf-map.json shipped with the dataset")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--hamming", type=int, default=5)
    ap.add_argument("--no-hash", action="store_true")
    args = ap.parse_args()

    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    leaf_map = {}
    if args.leaf_map and Path(args.leaf_map).exists():
        leaf_map = json.loads(Path(args.leaf_map).read_text(encoding="utf-8"))
        print(f"leaf map loaded: {len(leaf_map)} entries")
    else:
        print("WARNING: no leaf map. Grouping will be much weaker and the split "
              "may leak. Pass --leaf-map.")

    class_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    records = [{"path": str(p), "label": d.name}
               for d in class_dirs for p in sorted(d.iterdir())
               if p.suffix in IMAGE_SUFFIXES]
    if not records:
        raise SystemExit("no images found")
    print(f"{len(records)} images, {len(class_dirs)} classes")

    coverage = assign_groups(records, leaf_map, not args.no_hash, args.hamming)
    n_groups = len({r["group_id"] for r in records})
    print(f"grouping coverage: {coverage}")
    print(f"{n_groups} groups -> {len(records)/n_groups:.3f} images per group")

    split_by_group(records, args.seed)
    contam = naive_contamination(records, args.seed)

    with (out / "splits.csv").open("w", encoding="utf-8") as f:
        f.write("path,label,group_id,group_source,split\n")
        for r in records:
            f.write(f"\"{r['path']}\",{r['label']},{r['group_id']},"
                    f"{r['group_source']},{r['split']}\n")

    straddle = defaultdict(set)
    gsize = Counter()
    for r in records:
        straddle[r["group_id"]].add(r["split"])
        gsize[r["group_id"]] += 1
    violations = [g for g, s in straddle.items() if len(s) > 1]

    per_class = defaultdict(lambda: defaultdict(int))
    sizes = Counter()
    for r in records:
        sizes[r["split"]] += 1
        per_class[r["label"]][r["split"]] += 1

    summary = {
        "images": len(records), "classes": len(class_dirs), "groups": n_groups,
        "images_per_group": round(len(records) / n_groups, 4),
        "grouping_coverage": coverage,
        "group_size_histogram": {str(k): v for k, v in sorted(Counter(gsize.values()).items())},
        "largest_group": max(gsize.values()),
        "split_sizes": dict(sizes),
        "per_class": {k: dict(v) for k, v in per_class.items()},
        "group_straddle_violations": len(violations),
        "seed": args.seed, **contam,
        "caveat": ("Images with no grouping signal are treated as singletons, so the "
                   "contamination figure is a LOWER bound on true leakage."),
    }
    (out / "split_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({k: summary[k] for k in
                      ("split_sizes", "groups", "images_per_group",
                       "largest_group", "group_straddle_violations",
                       "naive_test_contamination_pct")}, indent=2))
    if violations:
        raise SystemExit(f"FAIL: {len(violations)} groups straddle splits")
    print(f"\nOK  manifests in {out}")
    print(f"REPORTABLE: a random split would have leaked "
          f"{contam['naive_test_contamination_pct']}% of test images.")


if __name__ == "__main__":
    main()
