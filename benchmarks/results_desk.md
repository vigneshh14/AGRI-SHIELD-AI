# [DESK] results — x86 development machine

These are desktop numbers. They do NOT support any on-device claim.
See `results_arm.md` for `[ARM]` figures.

Environment: Linux x86_64, 2 cores, Python 3.11.18, executorch 1.5.1, torch 2.15.0.

| Date | What | Metric | Value | Command |
| --- | --- | --- | --- | --- |
| 2026-10-30 | MobileNetV2 → ExecuTorch export | `.pte` size | 13.94 MB | `scripts/export_hello.py` |
| 2026-10-30 | MobileNetV2 → ExecuTorch export | export time | 13.6 s | `scripts/export_hello.py` |
| 2026-10-30 | MobileNetV2 XNNPACK inference | median latency, 20 runs | 5.9 ms | `scripts/run_hello.py` |
| 2026-10-30 | MobileNetV2 XNNPACK inference | mean latency | 6.0 ms | `scripts/run_hello.py` |
| 2026-10-30 | MobileNetV2 XNNPACK inference | min / max | 4.9 / 8.2 ms | `scripts/run_hello.py` |

Caveat: random-initialised weights (pretrained download was blocked in that
sandbox). Weight values do not affect latency or `.pte` size materially, but the
model is not accuracy-meaningful.
