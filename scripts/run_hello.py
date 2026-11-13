#!/usr/bin/env python3
"""
ExecuTorch hello-world, part 2: load the .pte back and execute it.

Proves the RUNTIME path, which is separate from the export path. Keeping the
two failures distinguishable ("my export is broken" vs "my runtime is broken")
is worth a lot when the schedule is tight.

Also prints a [DESK] latency figure. That tag matters: it is a desktop number
and must never be presented as an on-device one.

Run:
    python scripts/run_hello.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import torch

PTE = Path(__file__).resolve().parent.parent / "models" / "mobilenet_v2_xnnpack.pte"


def main() -> int:
    if not PTE.exists():
        print(f"missing {PTE} — run scripts/export_hello.py first")
        return 1

    from executorch.runtime import Runtime

    runtime = Runtime.get()
    program = runtime.load_program(str(PTE))
    method = program.load_method("forward")

    x = (torch.randn(1, 3, 224, 224),)

    out = method.execute(x)
    shape = tuple(out[0].shape)
    print(f"output shape: {shape}")
    if shape != (1, 1000):
        print(f"WARNING: expected (1, 1000), got {shape}")

    for _ in range(3):                     # warm up
        method.execute(x)
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        method.execute(x)
        times.append((time.perf_counter() - t0) * 1000)

    print(f"\n[DESK] latency over 20 runs")
    print(f"  median {statistics.median(times):.1f} ms")
    print(f"  mean   {statistics.mean(times):.1f} ms")
    print(f"  min    {min(times):.1f} ms")
    print(f"  max    {max(times):.1f} ms")
    print("\nTag: [DESK] — x86 development machine. NOT an on-device result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
