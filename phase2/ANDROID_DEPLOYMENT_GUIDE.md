# AGRI-SHIELD AI — Android Deployment Guide

**Target:** Infinix NOTE 30 5G
**Goal of this guide:** get the *actual trained* `agrishield_tomato4.pte` executing on the phone's Arm cores and produce a measurement file that can be defended.

Everything that could be prepared without the phone has been prepared. What remains is roughly fifteen minutes of work on the device.

---

## 0. What you are installing, and why

The ExecuTorch Arm runtime available to this project is **glibc**-linked. Android's own C library is Bionic, so those libraries cannot run directly under Android or under Termux's native environment. They run inside a small **Debian aarch64 userland** supplied by `proot-distro`, which provides glibc.

This matters for how the result is described:

- The model executes on the phone's **real Cortex-A76 / A55 cores** with real Arm kernels. The arithmetic and the instruction mix are genuine.
- `proot` intercepts system calls via `ptrace`. Syscall-heavy work pays overhead; the convolution inner loops do not.
- **This is not a native Android application**, and the resulting latency must never be presented as one. Section 6 covers what that route would need.

Nothing below requires the phone to be rooted, and nothing requires USB debugging.

---

## 1. Transfer the payload (phone already connected)

Your phone is already mounted — it appears in File Explorer under **This PC → Infinix NOTE 30 5G**.

1. Open the `agrishield_phase2` payload folder on the laptop.
2. Drag the **whole folder** to the phone's **Internal storage → Download**.

The folder is ~13 MB and contains:

| File | Purpose |
|---|---|
| `agrishield_bench` | aarch64 benchmark runner, 2.3 MB |
| `lib/libexecutorch.so` | ExecuTorch Arm runtime |
| `lib/libexecutorch_backend_xnnpack.so` | XNNPACK backend |
| `lib/libexecutorch_threadpool.so` | thread pool |
| `agrishield_tomato4.pte` | **the trained model** |
| `validation_inputs.bin` | deterministic test tensors |
| `run_bench.sh` | the script you run |

The runner checks the model's SHA256 on startup and **refuses to benchmark** anything that isn't the authentic Phase 1 artifact — so a corrupted MTP copy cannot silently produce a fake result.

---

## 2. Install Termux

Install from **F-Droid**, not the Play Store — the Play Store build is unmaintained and `proot-distro` fails on it.

1. On the phone, open <https://f-droid.org/packages/com.termux/> in a browser.
2. Download the APK and allow installation from unknown sources when prompted.
3. Open Termux.

---

## 3. Set up the Debian userland

In Termux, type each line and press enter. The first two need wifi.

```sh
pkg update -y && pkg upgrade -y
pkg install -y proot-distro
termux-setup-storage
proot-distro install debian
```

`termux-setup-storage` pops a permission dialog — accept it. That is what makes `/sdcard` readable.

`proot-distro install debian` downloads a small rootfs (~70 MB). Let it finish.

---

## 4. Move the payload in and run

Still in Termux:

```sh
cp -r /sdcard/Download/agrishield_phase2 \
      $PREFIX/var/lib/proot-distro/installed-rootfs/debian/root/
proot-distro login debian
```

You are now inside Debian. Then:

```sh
cd /root/agrishield_phase2
sh run_bench.sh
```

That is the whole thing.

---

## 5. What you should see, and what to send back

The script prints, in order:

1. `model SHA256 OK` — the artifact is authentic.
2. The CPU **`Features`** line from the phone's own `/proc/cpuinfo`. **This is the line that settles the I8MM question**, which the Phase 1 report currently gets wrong (see `PHASE2_ENVIRONMENT_AUDIT.md` §5). Look for `asimddp` and whether `i8mm` is present or absent.
3. Thermal readings and per-core frequencies.
4. Timing for 50 inferences after 10 warm-up runs: median, mean, P90, min, max, and peak RSS.

It writes two files into the same folder:

- `android_inference_results.json`
- `device_sysinfo.txt`

**Send both back.** The simplest route: from inside Debian,

```sh
cp android_inference_results.json device_sysinfo.txt /sdcard/Download/
```

then copy them off the phone with File Explorer, or just attach them to the chat.

### If something fails

The script exits non-zero and says so rather than printing a number. Report the error verbatim — no measurement is better than an invented one.

Two failures worth anticipating:

- **`cannot execute binary file`** — the copy was corrupted or truncated. Re-copy the folder.
- **`error while loading shared libraries`** — run from inside `/root/agrishield_phase2`, not from elsewhere; the script sets `LD_LIBRARY_PATH` relative to its own location.

You can change the iteration count: `ITERS=200 sh run_bench.sh`.

---

## 6. The native Android route (not yet possible here)

A native Android application — ExecuTorch compiled against Bionic, wrapped in a Gradle APK — is the stronger result for the competition, and remains the eventual target. It needs either:

- **Android NDK** (~700 MB) to cross-compile the runtime against Bionic, or
- **ExecuTorch's prebuilt Android AAR** from Maven Central plus a JDK and the Android SDK.

Both `dl.google.com` and Maven Central are blocked from the build container, so neither can be fetched or built on my side. Both would need Android Studio installed on the laptop (~3 GB total). `PHASE2_BLOCKERS.md` sets out what that would cost and what it would buy, so you can decide whether it is worth the time before 21 November.

The proot route above gets a genuine, defensible Arm measurement **today**, which is the right first milestone either way — and the `/proc/cpuinfo` data it captures is identical to what a native app would see.
