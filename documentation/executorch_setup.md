# ExecuTorch setup — commands that actually worked

Every entry here was executed and its output observed. Nothing is from memory.

## Verified 30 Oct 2026 — Linux x86_64, 2 cores

### Versions that worked together

| Package | Version |
| --- | --- |
| Python | 3.11.18 |
| executorch | **1.5.1** |
| torch | 2.15.0+cu132 |
| torchvision | 0.29.2 |

Note: the published ExecuTorch tutorials are written against 1.0–1.4. PyPI served
**1.5.1**. The API below is what 1.5.1 actually exposes.

### Install

```bash
uv venv --python 3.11 et-env
uv pip install --python et-env/bin/python executorch torchvision
```

Plain `python -m venv` + `pip install executorch torchvision` works too; `uv` is
just faster. Exit code 0, no dependency conflicts. Keep this environment separate
from the vision-training environment — ExecuTorch pins its own torch build.

### Gotchas found by running it

1. **`executorch.__version__` does not exist** in 1.5.1. `import executorch` then
   reading `__version__` raises `AttributeError`. Use instead:
   ```python
   from importlib.metadata import version
   version("executorch")
   ```
2. **Lowering API**: `to_edge_transform_and_lower` is present and is the one to use.
   ```python
   from executorch.exir import to_edge_transform_and_lower
   from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner
   program = to_edge_transform_and_lower(
       torch.export.export(model, sample), partitioner=[XnnpackPartitioner()]
   ).to_executorch()
   open("out.pte","wb").write(program.buffer)
   ```
3. **Runtime API**:
   ```python
   from executorch.runtime import Runtime
   runtime = Runtime.get()
   program = runtime.load_program("out.pte")
   method  = program.load_method("forward")
   out     = method.execute((torch.randn(1,3,224,224),))
   ```
4. **Harmless warnings at load**: the runtime prints `cpuinfo_utils.cpp` messages
   about failing to read `/sys/.../midr_el1`. That is ExecuTorch probing the **Arm
   MIDR register** for CPU feature detection — it finds nothing on x86 and carries
   on. Seeing these confirms the Arm feature-detection path is compiled in. On the
   Android target these should succeed, and whether they report I8MM is directly
   relevant to the report.
5. A `KernelPreference` / `register_constant()` deprecation warning from
   `torch/utils/_pytree.py` is noise; it does not affect the export.
6. **`weights="DEFAULT"` needs network access** to `download.pytorch.org`. In a
   restricted environment it raises `URLError`. `export_hello.py` falls back to
   random init, which is fine — the export path does not depend on weight values.

### Result

```
lowering via to_edge_transform_and_lower
wrote models/mobilenet_v2_xnnpack.pte
  size   13.94 MB
  export 13.6s
output shape: (1, 1000)
```

Both halves pass: export produces a loadable `.pte`, and the runtime executes it
with the correct output shape.

### Not yet done

- Export on the Windows laptop (versions may differ — re-record here).
- Cross-compile the ExecuTorch Llama runner with the Android NDK.
- Run anything on the Arm device. **No `[ARM]` numbers exist yet.**
