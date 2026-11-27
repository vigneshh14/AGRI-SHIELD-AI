#!/usr/bin/env python3
"""
Train a lightweight disease classifier from a leakage-proof split manifest.

Reads datasets/metadata/splits.csv (produced by prepare_splits.py) and never
re-derives its own split, so training can never silently disagree with the
grouping work.

Honesty rules enforced here
---------------------------
* If ImageNet weights cannot be downloaded, training proceeds from random init
  but every artifact is stamped `pretrained: false`. Results from a
  randomly-initialised backbone are a PIPELINE test, not model performance,
  and metrics.json says so in a field a reader cannot miss.
* All metrics are tagged [DESK] or [ARM] by the caller. This script only ever
  produces [DESK] numbers.

Usage
-----
    python train.py --manifest datasets/metadata/splits.csv \
                    --out model/results/training_run \
                    --epochs 10 --img-size 224 --batch 32
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms


# --------------------------------------------------------------------------
class ManifestDataset(Dataset):
    def __init__(self, rows: list[dict], classes: list[str], tf):
        self.rows, self.tf = rows, tf
        self.class_to_idx = {c: i for i, c in enumerate(classes)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        with Image.open(r["path"]) as im:
            img = im.convert("RGB")
            x = self.tf(img)
        return x, self.class_to_idx[r["label"]]


def load_manifest(path: Path) -> tuple[dict[str, list[dict]], list[str]]:
    by_split: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    labels: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_split.setdefault(row["split"], []).append(row)
            labels.add(row["label"])
    return by_split, sorted(labels)


# --------------------------------------------------------------------------
def build_model(n_classes: int) -> tuple[nn.Module, bool]:
    """Returns (model, pretrained_ok). Falls back to random init, loudly."""
    pretrained = True
    try:
        model = torchvision.models.mobilenet_v2(weights="IMAGENET1K_V1")
    except Exception as e:
        print(f"!! ImageNet weights unavailable ({type(e).__name__}): {e}")
        print("!! Falling back to RANDOM INIT. Results are a PIPELINE TEST ONLY.")
        model = torchvision.models.mobilenet_v2(weights=None)
        pretrained = False
    in_f = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_f, n_classes)
    return model, pretrained


def metrics_from_confusion(cm: np.ndarray) -> dict:
    """Per-class and macro precision / recall / F1 from a confusion matrix."""
    tp = np.diag(cm).astype(float)
    fp = cm.sum(0) - tp
    fn = cm.sum(1) - tp
    prec = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    rec = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(2 * prec * rec, prec + rec,
                   out=np.zeros_like(tp), where=(prec + rec) > 0)
    return {
        "accuracy": float(tp.sum() / cm.sum()) if cm.sum() else 0.0,
        "macro_precision": float(prec.mean()),
        "macro_recall": float(rec.mean()),
        "macro_f1": float(f1.mean()),
        "per_class_precision": [round(float(v), 4) for v in prec],
        "per_class_recall": [round(float(v), 4) for v in rec],
        "per_class_f1": [round(float(v), 4) for v in f1],
    }


@torch.no_grad()
def evaluate(model, loader, n_classes, device) -> tuple[np.ndarray, list[float]]:
    model.eval()
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    confidences: list[float] = []
    for x, y in loader:
        logits = model(x.to(device))
        probs = torch.softmax(logits, 1)
        conf, pred = probs.max(1)
        confidences.extend(conf.cpu().tolist())
        for t, p in zip(y.tolist(), pred.cpu().tolist()):
            cm[t, p] += 1
    return cm, confidences


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--img-size", type=int, default=224)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit-per-split", type=int, default=0,
                    help="cap images per split (smoke testing only)")
    ap.add_argument("--smoke", action="store_true",
                    help="mark this run as a pipeline smoke test, not a real result")
    ap.add_argument("--resume", action="store_true",
                    help="continue from last.pt in --out if present")
    ap.add_argument("--max-seconds", type=float, default=0,
                    help="stop gracefully after this many seconds (0 = no limit)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(1337)

    by_split, classes = load_manifest(Path(args.manifest))
    if args.limit_per_split:
        rng = np.random.default_rng(1337)
        for k, rows in by_split.items():
            if len(rows) > args.limit_per_split:
                idx = rng.choice(len(rows), args.limit_per_split, replace=False)
                by_split[k] = [rows[i] for i in idx]

    print(f"classes ({len(classes)}): {classes}")
    for k in ("train", "val", "test"):
        print(f"  {k:<6} {len(by_split.get(k, []))} images  "
              f"{dict(Counter(r['label'] for r in by_split.get(k, [])))}")

    norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(args.img_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(0.2, 0.2, 0.2, 0.05),
        transforms.ToTensor(), norm,
    ])
    eval_tf = transforms.Compose([
        transforms.Resize(int(args.img_size * 1.14)),
        transforms.CenterCrop(args.img_size),
        transforms.ToTensor(), norm,
    ])

    loaders = {}
    for k, tf in (("train", train_tf), ("val", eval_tf), ("test", eval_tf)):
        ds = ManifestDataset(by_split.get(k, []), classes, tf)
        loaders[k] = DataLoader(ds, batch_size=args.batch, shuffle=(k == "train"),
                                num_workers=args.workers, pin_memory=False)

    model, pretrained = build_model(len(classes))
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, args.epochs))
    crit = nn.CrossEntropyLoss(label_smoothing=0.05)

    history, best_val, t_start = [], -1.0, time.time()
    start_epoch = 1
    last_path = out / "last.pt"
    if args.resume and last_path.exists():
        ck = torch.load(last_path, map_location=device, weights_only=False)
        model.load_state_dict(ck["state_dict"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        history = ck["history"]
        best_val = ck["best_val"]
        start_epoch = ck["epoch"] + 1
        pretrained = ck.get("pretrained", pretrained)
        print(f"resumed from epoch {ck['epoch']} (best val {best_val:.4f})")

    stopped_early = False
    for epoch in range(start_epoch, args.epochs + 1):
        model.train()
        run_loss, seen, correct = 0.0, 0, 0
        for x, y in loaders["train"]:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = crit(logits, y)
            loss.backward()
            opt.step()
            run_loss += loss.item() * y.size(0)
            correct += (logits.argmax(1) == y).sum().item()
            seen += y.size(0)
        sched.step()

        cm_val, _ = evaluate(model, loaders["val"], len(classes), device)
        m_val = metrics_from_confusion(cm_val)
        row = {
            "epoch": epoch,
            "train_loss": round(run_loss / max(1, seen), 4),
            "train_acc": round(correct / max(1, seen), 4),
            "val_acc": round(m_val["accuracy"], 4),
            "val_macro_f1": round(m_val["macro_f1"], 4),
            "secs": round(time.time() - t_start, 1),
        }
        history.append(row)
        print(f"epoch {epoch:>3}  loss {row['train_loss']:.4f}  "
              f"train_acc {row['train_acc']:.4f}  val_acc {row['val_acc']:.4f}  "
              f"val_f1 {row['val_macro_f1']:.4f}  ({row['secs']}s)")

        if m_val["accuracy"] > best_val:
            best_val = m_val["accuracy"]
            torch.save({"state_dict": model.state_dict(), "classes": classes,
                        "pretrained": pretrained, "img_size": args.img_size},
                       out / "best.pt")
        torch.save({"state_dict": model.state_dict(), "opt": opt.state_dict(),
                    "sched": sched.state_dict(), "history": history,
                    "best_val": best_val, "epoch": epoch, "classes": classes,
                    "pretrained": pretrained, "img_size": args.img_size}, last_path)

        if args.max_seconds and (time.time() - t_start) > args.max_seconds:
            print(f"time budget reached after epoch {epoch}; stopping gracefully. "
                  f"Re-run with --resume to continue.")
            stopped_early = True
            break

    # Evaluate the SELECTED model (best validation epoch), not whatever the last
    # epoch happened to leave in memory. Reporting the last epoch's test score
    # while shipping the best-val checkpoint means the headline number does not
    # describe the artifact that gets deployed. Audit caught exactly that.
    best_path = out / "best.pt"
    if best_path.exists():
        bck = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(bck["state_dict"])
        print(f"evaluating BEST checkpoint (val acc {best_val:.4f}) on the test set")
    else:
        print("WARNING: no best.pt; evaluating the final-epoch model instead")

    cm_test, conf_test = evaluate(model, loaders["test"], len(classes), device)
    m_test = metrics_from_confusion(cm_test)

    result = {
        "tag": "[DESK]",
        "SMOKE_TEST_ONLY": bool(args.smoke),
        "pretrained_backbone": pretrained,
        "methodology": ("ImageNet-pretrained backbone, fine-tuned" if pretrained else
                        "trained from random initialisation; NO ImageNet transfer learning"),
        "warning": (None if pretrained else
                    "No ImageNet pretraining. These are real trained-model numbers, but a "
                    "pretrained backbone would normally score higher and converge sooner. "
                    "State the methodology whenever quoting these figures."),
        "classes": classes,
        "epochs_requested": args.epochs,
        "epochs_completed": history[-1]["epoch"] if history else 0,
        "stopped_early": stopped_early,
        "img_size": args.img_size,
        "batch": args.batch,
        "train_images": len(by_split.get("train", [])),
        "val_images": len(by_split.get("val", [])),
        "test_images": len(by_split.get("test", [])),
        "test_metrics": m_test,
        "evaluated_checkpoint": "best.pt (best validation epoch)",
        "test_confusion_matrix": cm_test.tolist(),
        "mean_test_confidence": round(float(np.mean(conf_test)) if conf_test else 0.0, 4),
        "history": history,
        "total_seconds": round(time.time() - t_start, 1),
    }
    (out / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ep = [h["epoch"] for h in history]
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        ax[0].plot(ep, [h["train_loss"] for h in history], marker="o")
        ax[0].set_title("train loss"); ax[0].set_xlabel("epoch"); ax[0].grid(alpha=.3)
        ax[1].plot(ep, [h["train_acc"] for h in history], marker="o", label="train")
        ax[1].plot(ep, [h["val_acc"] for h in history], marker="s", label="val")
        ax[1].set_title("accuracy"); ax[1].set_xlabel("epoch")
        ax[1].legend(); ax[1].grid(alpha=.3)
        fig.tight_layout(); fig.savefig(out / "training_curves.png", dpi=130)

        fig2, ax2 = plt.subplots(figsize=(5.5, 5))
        ax2.imshow(cm_test, cmap="Blues")
        ax2.set_xticks(range(len(classes))); ax2.set_yticks(range(len(classes)))
        ax2.set_xticklabels(classes, rotation=45, ha="right", fontsize=7)
        ax2.set_yticklabels(classes, fontsize=7)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax2.text(j, i, cm_test[i, j], ha="center", va="center", fontsize=8)
        ax2.set_xlabel("predicted"); ax2.set_ylabel("true")
        ax2.set_title("test confusion matrix")
        fig2.tight_layout(); fig2.savefig(out / "confusion_matrix.png", dpi=130)
        print("plots written")
    except Exception as e:
        print(f"plotting skipped: {type(e).__name__}: {e}")

    print("\n=== TEST ===")
    print(f"accuracy        {m_test['accuracy']:.4f}")
    print(f"macro precision {m_test['macro_precision']:.4f}")
    print(f"macro recall    {m_test['macro_recall']:.4f}")
    print(f"macro F1        {m_test['macro_f1']:.4f}")
    if result["SMOKE_TEST_ONLY"]:
        print("\n*** SMOKE TEST ONLY — not valid model performance ***")
    elif not pretrained:
        print("\n*** Trained from scratch (no ImageNet init). Real numbers, "
              "but quote the methodology with them. ***")


if __name__ == "__main__":
    main()
