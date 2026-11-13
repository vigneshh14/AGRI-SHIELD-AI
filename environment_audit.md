# Environment audit

Started 30 Oct 2026. **Incomplete** — Windows-side hardware not yet inspected.

## Development laptop (target: project home)

| Property | Value | How observed |
| --- | --- | --- |
| Device name | vibewithvickyy | device bridge |
| OS | Windows (win32) | device bridge |
| Architecture | x64 | device bridge |
| Claude desktop | 4.4212.0 | device bridge |
| CPU model / cores | **not yet measured** | needs Windows shell |
| RAM | **not yet measured** | needs Windows shell |
| Free storage | **not yet measured** | needs Windows shell |
| GPU | **not yet measured** | needs Windows shell |
| Python | **not yet measured** | needs Windows shell |
| Git | **not yet measured** | needs Windows shell |

Granted folders: `C:\Users\VIGNESH\Documents`, `C:\Users\VIGNESH\Downloads`.

Signals from the home directory listing (presence only, versions unknown):
`.android` (Android SDK / adb likely installed — relevant to the phone path),
`.Xilinx`, `.comsol`, `arduino`, `eda`, `.vscode`.

## Build sandbox (Linux, used for verification)

| Property | Value |
| --- | --- |
| Architecture | x86_64 |
| Cores | 2 |
| Python available | 3.11, 3.12, 3.13 |
| Free disk | ~31 GB |
| Role | verify ExecuTorch export/runtime before running on the laptop |

## Target inference device

Arm Android phone. Model, SoC, RAM and Android version **not yet recorded** —
needed for the report, since the I8MM instruction set extension is what makes the
int4 Llama path fast on Arm.

## Open compatibility questions

1. ExecuTorch on Windows — supported for XNNPACK, but the Android NDK
   cross-compilation of the Llama runner is far smoother under Linux/WSL2.
   **Decide: native Windows vs WSL2.** WSL2 is the recommendation.
2. Python version — ExecuTorch documents 3.10–3.12. Confirm what is on the laptop.
3. Phone SoC — determines whether I8MM is available.
