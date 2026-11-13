# AGRI-SHIELD AI — Phase 2 Live Device Audit

**Audit date:** 31 October 2026, 10:47–10:54 local
**Method:** scripts executed on the actual Windows laptop; raw logs preserved at `phase2/phase2_audit_raw.txt`, `phase2/adb_setup_raw.txt`, `phase2/adb_setup2_raw.txt`
**Target device:** Infinix NOTE 30 5G (X6711)

Every row below is either a direct measurement or is explicitly marked as unmeasured. Nothing is carried over from an earlier session.

---

## 1. Headline

**ADB is now installed and working.** It was not, three hours ago. It found **no device**, because USB debugging is still off on the phone. That is the single remaining blocker, and it needs about sixty seconds of tapping on the handset.

MTP visibility was correctly *not* treated as evidence of ADB access — and the audit proves why that caution was right: the phone is plainly visible in File Explorer while `adb devices` returns an empty list.

---

## 2. Laptop toolchain — state change since the 10:01 audit

| Component | 10:01 | 10:54 | Evidence |
|---|---|---|---|
| **ADB / platform-tools** | not installed | **INSTALLED** | `adb version` → 1.0.41, `37.0.1-15733141` |
| Git | not installed | not installed | `where git` → not found |
| Java / JDK | not installed | not installed | `where java` → not found |
| Android SDK / NDK | not installed | not installed | env vars empty, SDK dir absent |
| CMake | not installed | not installed | `where cmake` → not found |
| Python | 3.13.15 | 3.13.15 | `C:\Users\VIGNESH\AppData\Local\Programs\Python\Python313` |
| `env-executorch` / `env-vision` | absent | absent | not in project root |
| Windows build | — | 10.0.26200 | reported by adb |
| Free space on C: | — | 64.5 GB | `dir` footer |

**ADB install details.** Installed **without administrator rights** and **without modifying PATH**, at:

```
C:\Users\VIGNESH\Documents\AGRI_SHIELD_AI\phase2\platform-tools\adb.exe
```

PATH was deliberately left alone — `setx` truncates PATH beyond 1024 characters and can corrupt it. All project scripts call adb by absolute path. If you want `adb` available from any terminal, add that folder to PATH yourself through the Environment Variables dialog.

**How the download succeeded, after failing.** Worth recording, because the first failure looks like a block and is not one:

| Attempt | Mechanism | Result |
|---|---|---|
| 1 | Windows `curl` (schannel TLS) | **FAILED** — `SEC_E_DECRYPT_FAILURE (0x80090330)` |
| 2 | PowerShell `Invoke-WebRequest`, TLS 1.2/1.3 forced (.NET TLS stack) | **SUCCEEDED** — 8,044,989 bytes |

The file came from the official Google endpoint (`dl.google.com/android/repository/platform-tools-latest-windows.zip`). The failure was a TLS-stack problem on this machine, not a firewall or a missing file — so a second mechanism was tried once, and it worked. No endpoint was retried repeatedly.

---

## 3. Phone connectivity — measured

| Check | Result |
|---|---|
| Physically connected over USB | **YES** |
| Detected by Windows via MTP | **YES** — appears in File Explorer under *This PC* as "Infinix NOTE 30 5G" |
| USB cable carries data | **YES** — proven by MTP enumeration |
| adb daemon starts | **YES** — `daemon started successfully` on tcp:5037 |
| **Appears in `adb devices`** | **NO** — list empty |
| State reported | no `unauthorized` entry, no `offline` entry — **no entry at all** |

**Diagnosis.** An empty list, rather than an `unauthorized` entry, means the phone is not offering an ADB interface at all. The USB cable and port are proven good by MTP. Therefore: **USB debugging is disabled in Developer options.** Had it been enabled but untrusted, the device would have appeared as `unauthorized` and the phone would have shown an RSA prompt.

---

## 4. Phone hardware — NOT MEASURED

No property, CPU feature, memory figure or thermal reading has been taken from the phone. Every adb query returned `no devices/emulators found`, verbatim.

The following are **user-stated, not verified**, and are recorded here only as expectations to be confirmed:

- Model X6711, MediaTek Dimensity 6080, 8 GB RAM, 256 GB storage, Android reported as 17

**Still unresolved, and consequential:** whether the CPU exposes **I8MM**. The Phase 1 report §5 places this phone on the "has I8MM" side of its comparison against the Raspberry Pi 5. If the SoC is a Dimensity 6080 (Cortex-A76 + A55, ARMv8.2-A), that is wrong — ARMv8.2-A provides SDOT but not I8MM. **The Phase 1 archive has not been edited.** The contradiction stands recorded until the phone's own `Features` line settles it, which `deploy_phone.bat` captures automatically the moment debugging is enabled.

---

## 5. Payload staged on the laptop

Ready at `phase2\agrishield_phase2\`:

| File | Size | Status |
|---|---|---|
| `agrishield_bench` | 2,340,464 B | aarch64 ELF, cross-compiled and emulation-tested |
| `lib/libexecutorch.so` | 564,305 B | ExecuTorch Arm runtime |
| `lib/libexecutorch_backend_xnnpack.so` | 2,181,728 B | XNNPACK backend |
| `lib/libexecutorch_threadpool.so` | 268,208 B | thread pool |
| `run_bench.sh` | 3,880 B | benchmark driver, verifies model hash before running |
| `validation_inputs.bin` | 884,752 B | deterministic test tensors |
| `agrishield_tomato4.pte` | 8,890,640 B | **copied locally by `deploy_phone.bat`** from `models/`, not re-transferred |

The direct transfer of the 8.9 MB model over the bridge failed once; rather than retrying it, `deploy_phone.bat` copies the authentic file already present in `models/` and verifies its SHA256 against `f57f5ec3…37f4b` before anything is pushed. The runner independently re-checks the hash on the phone and **aborts** on mismatch.

---

## 6. Status ledger

| Item | Status |
|---|---|
| Laptop toolchain audited | **VERIFIED ON LAPTOP** |
| ADB installed and functional | **VERIFIED ON LAPTOP** |
| Payload built and staged | **VERIFIED ON LAPTOP** |
| aarch64 runner executes the real model | **VERIFIED UNDER EMULATION** |
| aarch64 output matches x86_64 reference | **VERIFIED UNDER EMULATION** — 8/8 vectors bit-identical |
| Phone reachable over ADB | **BLOCKED** — USB debugging off |
| Phone CPU features / I8MM | **BLOCKED** |
| Model executed on the physical phone | **NOT STARTED** |
| Offline verification | **NOT STARTED** |
| Llama integration | **NOT STARTED** — correctly deferred |

---

## 7. Next action

Enable USB debugging on the phone (steps supplied separately), then run `deploy_phone.bat`. That single script captures the full device profile, pushes the payload, and verifies the model hash on the handset — no further laptop work is needed from you.
