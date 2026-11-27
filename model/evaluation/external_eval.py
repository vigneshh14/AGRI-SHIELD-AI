#!/usr/bin/env python3
"""
External generalisation: PlantVillage-trained model evaluated on PlantDoc.

PlantVillage is shot in a lab on uniform backgrounds. PlantDoc is internet-
scraped field imagery with clutter, varied lighting and multiple leaves per
frame. Testing across that gap is the honest measure of field usefulness.

PlantDoc is NEVER trained on. Both its train/ and test/ folders are used
together as one external test set.

Label mapping is EXPLICIT. PlantDoc classes with no counterpart in the model's
label space are EXCLUDED and counted, never silently folded into a nearby class.

Datasets
--------
PlantDoc: Singh et al., CoDS-COMAD 2020. Licence CC BY 4.0.
PlantVillage: Mohanty, Hughes & Salathe 2016.

Usage
-----
    python external_eval.py --plantdoc /path/to/PlantDoc-Dataset \
                            --checkpoint model/results/training_run/best.pt \
                            --out model/results/external_plantdoc.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torchvision
import torch.nn as nn
from PIL import Image
from torchvision import transforms

# explicit, auditable mapping
PLANTDOC_TO_PV = {
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato leaf late blight": "Tomato___Late_blight",
    "Tomato Septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "Tomato leaf": "Tomato___healthy",
}
# present in PlantDoc, absent from our label space -> excluded on purpose
EXCLUDED = [
    "Tomato leaf yellow virus", "Tomato mold leaf", "Tomato leaf mosaic virus",
    "Tomato two spotted spider mites leaf", "Tomato leaf bacterial spot",
]


def metrics_from_cm(cm: np.ndarray) -> dict:
    tp = np.diag(cm).astype(float)
    fp = cm.sum(0) - tp
    fn = cm.sum(1) - tp
    prec = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    rec = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(tp),
                   where=(prec + rec) > 0)
    return {"accuracy": float(tp.sum() / cm.sum()) if cm.sum() else 0.0,
            "macro_precision": float(prec.mean()), "macro_recall": float(rec.mean()),
            "macro_f1": float(f1.mean()),
            "per_class_precision": [round(float(v), 4) for v in prec],
            "per_class_recall": [round(float(v), 4) for v in rec],
            "per_class_f1": [round(float(v), 4) for v in f1]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plantdoc", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    classes, img = ck["classes"], ck.get("img_size", 96)
    idx = {c: i for i, c in enumerate(classes)}
    model = torchvision.models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.load_state_dict(ck["state_dict"]); model.eval()

    tf = transforms.Compose([
        transforms.Resize(int(img * 1.14)), transforms.CenterCrop(img),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    root = Path(args.plantdoc)
    items, excluded_counts = [], {}
    for split in ("train", "test"):
        d = root / split
        if not d.exists():
            continue
        for sub in sorted(d.iterdir()):
            if not sub.is_dir():
                continue
            n = sum(1 for p in sub.iterdir() if p.suffix.lower() in
                    (".jpg", ".jpeg", ".png"))
            if sub.name in PLANTDOC_TO_PV:
                for p in sorted(sub.iterdir()):
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        items.append((p, PLANTDOC_TO_PV[sub.name]))
            elif sub.name.lower().startswith("tomato"):
                excluded_counts[sub.name] = excluded_counts.get(sub.name, 0) + n

    print(f"evaluating {len(items)} PlantDoc images across {len(PLANTDOC_TO_PV)} mapped classes")
    print(f"excluded tomato classes (no counterpart in model): "
          f"{sum(excluded_counts.values())} images in {len(excluded_counts)} classes")

    cm = np.zeros((len(classes), len(classes)), dtype=np.int64)
    confs, correct_flags, failed = [], [], 0
    with torch.no_grad():
        for p, true in items:
            try:
                with Image.open(p) as im:
                    x = tf(im.convert("RGB")).unsqueeze(0)
            except Exception:
                failed += 1
                continue
            probs = torch.softmax(model(x), 1)[0].numpy()
            pred = int(probs.argmax())
            cm[idx[true], pred] += 1
            confs.append(float(probs[pred]))
            correct_flags.append(pred == idx[true])

    m = metrics_from_cm(cm)
    confs = np.array(confs); ok = np.array(correct_flags)

    # selective prediction: what the confidence gate would do here
    selective = []
    for t in (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        keep = confs >= t
        selective.append({
            "threshold": t,
            "coverage": round(float(keep.mean()), 4),
            "accuracy_on_answered": round(float(ok[keep].mean()), 4) if keep.any() else None,
            "selective_risk": round(float(1 - ok[keep].mean()), 4) if keep.any() else None,
        })

    result = {
        "tag": "[DESK]",
        "external_dataset": "PlantDoc (Singh et al. 2020), CC BY 4.0",
        "train_dataset": "PlantVillage (Mohanty et al. 2016)",
        "note": "PlantDoc was never trained on. Both its folders form one external test set.",
        "label_mapping": PLANTDOC_TO_PV,
        "excluded_classes": excluded_counts,
        "excluded_image_total": sum(excluded_counts.values()),
        "evaluated_images": int(cm.sum()),
        "unreadable_images": failed,
        "classes": classes,
        "metrics": m,
        "confusion_matrix": cm.tolist(),
        "mean_confidence": round(float(confs.mean()), 4),
        "mean_confidence_when_wrong": round(float(confs[~ok].mean()), 4) if (~ok).any() else None,
        "mean_confidence_when_right": round(float(confs[ok].mean()), 4) if ok.any() else None,
        "selective_prediction": selective,
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\n=== EXTERNAL (PlantDoc) ===")
    print(f"accuracy        {m['accuracy']:.4f}")
    print(f"macro F1        {m['macro_f1']:.4f}")
    print(f"mean confidence {result['mean_confidence']:.4f}")
    print(f"  when correct  {result['mean_confidence_when_right']}")
    print(f"  when WRONG    {result['mean_confidence_when_wrong']}")
    print("\nselective prediction (what the advisory gate would do):")
    for s in selective:
        print(f"  t={s['threshold']:<5} coverage={s['coverage']:<7} "
              f"acc_answered={s['accuracy_on_answered']}  risk={s['selective_risk']}")
    print(f"\nconfusion (rows true, cols pred): {[c.replace('Tomato___','') for c in classes]}")
    for i, row in enumerate(cm.tolist()):
        print(f"  {classes[i].replace('Tomato___',''):<22} {row}")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
