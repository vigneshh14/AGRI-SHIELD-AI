#!/usr/bin/env python3
"""
ExecuTorch hello-world: export a small vision model to a .pte file.

This is the first rung of the whole project. It proves the three-step
ExecuTorch mental model — export to a graph, lower to a backend, write a .pte —
on a machine you already have, with no 1 GB download and no licence wait.

Everything harder in AGRI-SHIELD (the Llama export, the Android runner) is this
same shape with more moving parts. If this fails, fix it here, not later.

Run:
    python scripts/export_hello.py
Then:
    python scripts/run_hello.py
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import torch
import torchvision

OUT = Path(__file__).resolve().parent.parent / "models" / "mobilenet_v2_xnnpack.pte"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    import executorch
    print(f"executorch {getattr(executorch, '__version__', 'unknown')}")
    print(f"torch       {torch.__version__}")

    # The lowering API has moved between ExecuTorch releases. Try the current
    # name first, then the older one, and say which worked — that goes in
    # documentation/executorch_setup.md.
    api = None
    try:
        from executorch.exir import to_edge_transform_and_lower
        api = "to_edge_transform_and_lower"
    except ImportError:
        from executorch.exir import to_edge
        api = "to_edge"
    from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner
    print(f"lowering via {api}")

    # Pretrained weights are nicer but need network access to download.pytorch.org.
    # The export path does not depend on weight VALUES, so fall back to random
    # init in restricted environments rather than failing the toolchain check.
    try:
        model = torchvision.models.mobilenet_v2(weights="DEFAULT").eval()
        print("weights: pretrained")
    except Exception as e:
        print(f"weights: random (pretrained download failed: {type(e).__name__})")
        model = torchvision.models.mobilenet_v2(weights=None).eval()

    sample = (torch.randn(1, 3, 224, 224),)

    t0 = time.perf_counter()
    with torch.no_grad():
        exported = torch.export.export(model, sample)

    if api == "to_edge_transform_and_lower":
        program = to_edge_transform_and_lower(
            exported, partitioner=[XnnpackPartitioner()]
        ).to_executorch()
    else:
        program = to_edge(exported).to_backend(XnnpackPartitioner()).to_executorch()
    elapsed = time.perf_counter() - t0

    OUT.write_bytes(program.buffer)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]

    print(f"\nwrote {OUT}")
    print(f"  size   {OUT.stat().st_size / 1e6:.2f} MB")
    print(f"  sha256 {digest}")
    print(f"  export {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
