#!/usr/bin/env python3
"""
M2 inference + M4 severity + M6 retrieval, wired together.

Takes an image, returns the full advisory packet: disease, calibrated
confidence, severity band, and the knowledge-base context that the Llama layer
is allowed to see.

Two entry points:
    python predict.py --image leaf.jpg --checkpoint runs/.../best.pt
    python predict.py --evaluate-unseen --manifest datasets/metadata/splits.csv
                      --checkpoint runs/.../best.pt --n 12

Severity method and its limits
------------------------------
Severity is the fraction of leaf area showing lesion-like colour, computed in
HSV. It is a transparent proxy, NOT a validated phytopathological measurement,
and the output says so. Three bands: mild < 10%, moderate 10-30%, severe > 30%.
Thresholds are conventional, not calibrated against scored ground truth -- no
severity-labelled data was available. Report it as an estimate.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torchvision
import torch.nn as nn
from PIL import Image
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "knowledge_base"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "severity_estimation"))


def load_model(ckpt_path: Path, device):
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    classes = ck["classes"]
    model = torchvision.models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.load_state_dict(ck["state_dict"])
    model.eval().to(device)
    return model, classes, ck


def preprocess(img_size: int):
    return transforms.Compose([
        transforms.Resize(int(img_size * 1.14)),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


from severity import estimate_severity  # corrected module


@torch.no_grad()
def classify(model, classes, tf, path: Path, device):
    with Image.open(path) as im:
        x = tf(im.convert("RGB")).unsqueeze(0).to(device)
    probs = torch.softmax(model(x), 1)[0].cpu().numpy()
    i = int(probs.argmax())
    order = np.argsort(-probs)[:3]
    return {
        "class_label": classes[i],
        "confidence": float(probs[i]),
        "top3": [{"label": classes[j], "p": round(float(probs[j]), 4)} for j in order],
    }


def analyse(model, classes, tf, path: Path, device, kb, threshold: float, lang: str):
    from retrieval import retrieve
    cls = classify(model, classes, tf, path, device)
    sev = estimate_severity(path, predicted_class=cls["class_label"])
    packet = retrieve(kb, cls["class_label"], cls["confidence"],
                      severity=sev["severity"], lang=lang, threshold=threshold)
    return {"image": str(path), "classification": cls, "severity": sev, "advisory": packet}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--kb", default=None)
    ap.add_argument("--image")
    ap.add_argument("--evaluate-unseen", action="store_true")
    ap.add_argument("--manifest")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--lang", default="en", choices=["en", "ta"])
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from retrieval import KnowledgeBase, DEFAULT_KB
    kb = KnowledgeBase(Path(args.kb) if args.kb else DEFAULT_KB)

    device = torch.device("cpu")
    model, classes, ck = load_model(Path(args.checkpoint), device)
    tf = preprocess(ck.get("img_size", 96))
    print(f"model: {len(classes)} classes, img_size={ck.get('img_size')}, "
          f"pretrained_backbone={ck.get('pretrained')}")

    if args.image:
        print(json.dumps(analyse(model, classes, tf, Path(args.image), device,
                                 kb, args.threshold, args.lang),
                         indent=2, ensure_ascii=False))
        return

    if args.evaluate_unseen:
        rows = [r for r in csv.DictReader(open(args.manifest, newline="", encoding="utf-8"))
                if r["split"] == "test"]
        random.Random(args.seed).shuffle(rows)
        picked = rows[:args.n]
        print(f"\n{len(picked)} UNSEEN test images (never in train or val)\n")
        correct = 0
        modes = {}
        for r in picked:
            out = analyse(model, classes, tf, Path(r["path"]), device,
                          kb, args.threshold, args.lang)
            c, s, a = out["classification"], out["severity"], out["advisory"]
            hit = c["class_label"] == r["label"]
            correct += hit
            modes[a["advisory_mode"]] = modes.get(a["advisory_mode"], 0) + 1
            print(f"  {'OK ' if hit else 'MISS'} true={r['label']:<30} "
                  f"pred={c['class_label']:<30} p={c['confidence']:.3f} "
                  f"sev={s['severity']:<9} -> {a['advisory_mode']}")
        print(f"\n  {correct}/{len(picked)} correct on this sample")
        print(f"  advisory modes: {modes}")
        print("  (every mode is 'abstain' while the knowledge base has no "
              "source-verified chemical records -- that is the gate working)")


if __name__ == "__main__":
    main()
