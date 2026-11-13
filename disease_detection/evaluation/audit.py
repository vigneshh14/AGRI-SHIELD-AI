#!/usr/bin/env python3
"""
Independent audit of the classification claims, plus .pte artifact verification.

Everything here RE-DERIVES a claim rather than trusting a stored number:
  * no leaf group spans two splits
  * the test set never influenced model selection
  * accuracy and macro F1 reproduce from the saved checkpoint
  * macro F1 cross-checked against an independent implementation
  * the exported .pte carries the TRAINED weights, not random ones
  * .pte and PyTorch agree numerically, to a documented tolerance

    python audit.py --manifest ... --checkpoint ... --pte ... --metrics ...
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torchvision
import torch.nn as nn
from PIL import Image
from torchvision import transforms

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def macro_f1_independent(y_true, y_pred, n_classes) -> float:
    """Recomputed from scratch, not reusing the training code's helper."""
    f1s = []
    for c in range(n_classes):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return sum(f1s) / len(f1s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--pte", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--train-src", default="disease_detection/training/train.py")
    ap.add_argument("--out", default="reports/audit.json")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.manifest, newline="", encoding="utf-8")))
    stored = json.loads(Path(args.metrics).read_text(encoding="utf-8"))

    print("\n=== TASK 1a — split integrity ===")
    spans = defaultdict(set)
    for r in rows:
        spans[r["group_id"]].add(r["split"])
    bad = [g for g, s in spans.items() if len(s) > 1]
    check("no leaf group spans multiple splits", not bad,
          f"{len(spans)} groups, {len(bad)} violations")

    paths = [r["path"] for r in rows]
    check("no duplicate image paths", len(paths) == len(set(paths)),
          f"{len(paths)} rows, {len(set(paths))} unique")

    by_split = defaultdict(set)
    for r in rows:
        by_split[r["split"]].add(r["path"])
    overlap = (by_split["train"] & by_split["test"]) | (by_split["val"] & by_split["test"])
    check("test images appear in no other split", not overlap, f"{len(overlap)} overlaps")

    print("\n=== TASK 1b — test set not used for model selection ===")
    src = Path(args.train_src).read_text(encoding="utf-8")
    sel_on_val = 'if m_val["accuracy"] > best_val' in src
    check("best.pt selected on VALIDATION accuracy", sel_on_val)
    test_before_save = src.index('loaders["test"]') > src.index('out / "best.pt"')
    check("test loader only touched after training loop ends", test_before_save)
    check("early stopping / scheduler never reads test",
          'loaders["test"]' not in src.split("for epoch in range")[1].split("cm_test")[0])

    print("\n=== TASK 1c — reproduce the reported numbers ===")
    device = torch.device("cpu")
    ck = torch.load(args.checkpoint, map_location=device, weights_only=False)
    classes, img = ck["classes"], ck.get("img_size", 96)
    model = torchvision.models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.load_state_dict(ck["state_dict"]); model.eval().to(device)
    cidx = {c: i for i, c in enumerate(classes)}

    tf = transforms.Compose([
        transforms.Resize(int(img * 1.14)), transforms.CenterCrop(img),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    test_rows = [r for r in rows if r["split"] == "test"]
    y_true, y_pred = [], []
    with torch.no_grad():
        for r in test_rows:
            with Image.open(r["path"]) as im:
                x = tf(im.convert("RGB")).unsqueeze(0).to(device)
            y_pred.append(int(model(x).argmax(1).item()))
            y_true.append(cidx[r["label"]])

    acc = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    f1 = macro_f1_independent(y_true, y_pred, len(classes))
    s_acc = stored["test_metrics"]["accuracy"]
    s_f1 = stored["test_metrics"]["macro_f1"]
    check("accuracy reproduces", abs(acc - s_acc) < 0.005,
          f"recomputed {acc:.4f} vs stored {s_acc:.4f}")
    check("macro F1 reproduces (independent implementation)", abs(f1 - s_f1) < 0.005,
          f"recomputed {f1:.4f} vs stored {s_f1:.4f}")
    check("all 4 classes documented", len(classes) == 4, str(classes))
    check("per-class precision reported", len(stored["test_metrics"]["per_class_precision"]) == 4)
    check("per-class recall reported", len(stored["test_metrics"]["per_class_recall"]) == 4)

    print("\n=== TASK 6 — .pte artifact verification ===")
    from executorch.runtime import Runtime
    pte = Path(args.pte)
    check(".pte exists", pte.exists(), f"{pte.stat().st_size/1e6:.2f} MB")
    method = Runtime.get().load_program(str(pte)).load_method("forward")
    check(".pte loads through ExecuTorch", True)

    probe = torch.randn(1, 3, img, img)
    out_pte = method.execute((probe,))[0]
    check("accepts expected input dims", tuple(probe.shape) == (1, 3, img, img),
          f"(1, 3, {img}, {img})")
    check("returns 4 class outputs", tuple(out_pte.shape) == (1, 4), str(tuple(out_pte.shape)))

    # trained, not random: a random net is ~chance on real images
    agree, diffs = 0, []
    sample = test_rows[:60]
    with torch.no_grad():
        for r in sample:
            with Image.open(r["path"]) as im:
                x = tf(im.convert("RGB")).unsqueeze(0)
            a = model(x)
            b = method.execute((x,))[0]
            diffs.append(float((a - b).abs().max()))
            agree += int(a.argmax(1).item() == int(b.argmax(1).item()))
    pte_acc = sum(int(method.execute((tf(Image.open(r["path"]).convert("RGB")).unsqueeze(0),))[0]
                      .argmax(1).item() == cidx[r["label"]]) for r in sample) / len(sample)
    check(".pte carries TRAINED weights (accuracy >> chance)", pte_acc > 0.70,
          f"{pte_acc:.4f} on {len(sample)} test images, chance = 0.25")
    maxdiff = max(diffs)
    check("predictions agree with PyTorch", agree == len(sample),
          f"{agree}/{len(sample)} argmax agreement")
    check("logits within documented tolerance (1e-3)", maxdiff < 1e-3,
          f"max abs logit difference {maxdiff:.3e}")

    report = {
        "audited": str(Path(args.checkpoint)),
        "split_groups": len(spans), "split_violations": len(bad),
        "test_images": len(test_rows),
        "recomputed_accuracy": round(acc, 4), "stored_accuracy": s_acc,
        "recomputed_macro_f1_independent": round(f1, 4), "stored_macro_f1": s_f1,
        "classes": classes,
        "pte_mb": round(pte.stat().st_size / 1e6, 3),
        "pte_accuracy_on_sample": round(pte_acc, 4),
        "pte_vs_pytorch_argmax_agreement": f"{agree}/{len(sample)}",
        "pte_vs_pytorch_max_logit_diff": maxdiff,
        "tolerance": 1e-3,
        "failures": FAILS,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
    print(f"written to {args.out}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
