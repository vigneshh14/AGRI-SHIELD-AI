#!/usr/bin/env python3
"""Export the trained disease classifier to an ExecuTorch .pte for Arm deployment."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
import torch, torchvision, torch.nn as nn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    classes, img = ck["classes"], ck.get("img_size", 96)
    model = torchvision.models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.load_state_dict(ck["state_dict"]); model.eval()

    from executorch.exir import to_edge_transform_and_lower
    from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner

    sample = (torch.randn(1, 3, img, img),)
    t0 = time.perf_counter()
    with torch.no_grad():
        ep = torch.export.export(model, sample)
    prog = to_edge_transform_and_lower(ep, partitioner=[XnnpackPartitioner()]).to_executorch()
    dt = time.perf_counter() - t0

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(prog.buffer)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    meta = {"pte": str(out), "bytes": out.stat().st_size,
            "mb": round(out.stat().st_size/1e6, 3), "sha256": digest,
            "classes": classes, "img_size": img,
            "pretrained_backbone": ck.get("pretrained"),
            "export_seconds": round(dt, 2)}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))

    # verify it loads and runs
    from executorch.runtime import Runtime
    m = Runtime.get().load_program(str(out)).load_method("forward")
    o = m.execute((torch.randn(1, 3, img, img),))
    print(f"\nruntime check: output shape {tuple(o[0].shape)} "
          f"(expect (1, {len(classes)}))")

if __name__ == "__main__":
    main()
