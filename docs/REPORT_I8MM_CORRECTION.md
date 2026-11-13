# Report correction: the target phone does NOT support I8MM

**Where:** `PHASE1_REPORT.md`, the hardware / KleidiAI discussion, and the
compliance table if it repeats the claim.

**What was wrong:** The provisional report said the Infinix NOTE 30 5G (MediaTek
Dimensity 6080) supports the Armv8.6 I8MM extension. That was measured on 31 Oct 2026:
the CPU reports **Armv8.2-A without I8MM**. The comparison against Raspberry Pi 5
built on that claim is withdrawn.

**Replacement text** (paste in place of the old paragraph):

> **Target CPU features.** The deployment device is an Infinix NOTE 30 5G
> (MediaTek Dimensity 6080, 8 GB RAM). Reading the `Features` line of
> `/proc/cpuinfo` on the device shows the dot-product extension (`asimddp`)
> and no `i8mm` flag [ARM]. The provisional version of this report stated that the device
> supports I8MM. That statement was wrong and is withdrawn, together with the
> comparison against the Raspberry Pi 5 that depended on it.
>
> **Consequence.** KleidiAI's int4 matrix-multiply kernels have an I8MM path
> (Armv8.6+) and an SDOT path. On this device only the SDOT path can run.
> All Llama throughput figures in this report are therefore SDOT-path numbers.
> We make no claim about I8MM-class performance on this device.

**Before pasting:** run `adb shell cat /proc/cpuinfo | findstr Features` and
check the line still matches. If it shows anything other than what the box
above says, correct the box to match the device. Put the raw output in
`benchmarks/results_arm.md`.

Keep one line in `PROJECT_PROGRESS.md` under "Retractions" so the correction is
visible. A self-corrected claim reads well with a jury; a wrong claim a juror
finds on their own does not.
