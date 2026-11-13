# AGRI-SHIELD AI — Phase 2 Device Setup Log

**Date:** 31 October 2026, 10:47–11:07 local
**Device:** Infinix NOTE 30 5G (X6711), serial `103223136P110167`
**Raw logs:** `phase2/adb_setup_raw.txt`, `phase2/adb_setup2_raw.txt`, `phase2/deploy_raw.txt`, `phase2/termux_install_raw.txt`

---

## 1. Headline result — the I8MM question is settled

The phone's own `/proc/cpuinfo`, read over ADB from the physical handset:

```
Features : fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp
           asimdhp cpuid asimdrdm lrcpc dcpop asimddp
```

Identical on all eight cores.

| Extension | Present? | Consequence |
|---|---|---|
| `asimddp` (SDOT/UDOT) | **YES** | 8-bit dot-product acceleration available |
| **`i8mm`** | **NO** | **no 8-bit matrix-multiply acceleration** |
| `bf16` | NO | no bfloat16 |
| `sve` / `sve2` | NO | no scalable vectors |

**This falsifies the Phase 1 report §5 hardware table**, which places the Android phone on the "Armv8.6+/v9, has I8MM" side of its comparison against the Raspberry Pi 5. Measured on the actual device, the phone is **ARMv8.2-A with SDOT only** — the *same* ISA level as the Pi 5's Cortex-A76, not a generation ahead of it.

The correction is now evidence-backed rather than argued from a spec sheet. **The Phase 1 archive has not been edited** — it is frozen, and amending §5 is your decision.

### CPU topology — measured

| Cores | `CPU part` | Identity | Max freq | Min freq |
|---|---|---|---|---|
| cpu0–cpu5 | `0xd05` | **Cortex-A55** ×6 | 2.00 GHz | 0.50 GHz |
| cpu6–cpu7 | `0xd0b` | **Cortex-A76** ×2 | 2.40 GHz | 0.725 GHz |

MIDR `0x412fd050` (A55) and `0x414fd0b0` (A76). This is a 2+6 big.LITTLE arrangement, consistent with the Dimensity 6080.

**Benchmarking implication:** with only two A76 cores and six A55s, thread placement will dominate the latency distribution. An unpinned run will drift between clusters. The benchmark records `nproc` and every individual iteration time so this is visible rather than hidden in an average.

---

## 2. Device profile — all measured

| Property | Value |
|---|---|
| Model | Infinix X6711 (`X6711-GL`) |
| Manufacturer | INFINIX |
| **Android version** | **14** (SDK 34) — *not 17* |
| Security patch | 2024-06-05 |
| ABI | `arm64-v8a` (list: `arm64-v8a, armeabi-v7a, armeabi`) |
| SoC | MediaTek **MT6833GP**, platform `mt6833` |
| RAM | `MemTotal` 7,801,812 kB = **7.44 GiB** |
| Free / available RAM at probe | 110 MiB free, 1.92 GiB available |
| Storage | 227 GB total, 221 GB used, **5.8 GB free (98 % full)** |

Two corrections to the stated specification: Android is **14**, not 17; and usable RAM is 7.44 GiB rather than a flat 8 GB (normal — the remainder is carveout).

**Storage is a live risk.** 5.8 GB free is enough for Termux plus a Debian rootfs (~1.5 GB), but not comfortably. Freeing a few GB before proceeding would be prudent.

---

## 3. Toolchain work completed

### ADB installed without administrator rights

| Attempt | Mechanism | Result |
|---|---|---|
| 1 | Windows `curl` (schannel TLS) | FAILED — `SEC_E_DECRYPT_FAILURE (0x80090330)` |
| 2 | PowerShell `Invoke-WebRequest`, TLS 1.2/1.3 | **SUCCEEDED** — 8,044,989 bytes |

Installed at `phase2\platform-tools\adb.exe`. ADB 1.0.41 / `37.0.1-15733141`. **PATH was deliberately not modified** (`setx` truncates PATH past 1024 characters); all scripts use the absolute path.

### USB debugging

Enabled by the user at 11:02. The device then appeared as `device` — not `unauthorized` — meaning the RSA trust was granted in the same action.

### Payload pushed and verified on the handset

```
7 files pushed, 0 skipped. 27.9 MB/s (15,133,977 bytes in 0.517s)
→ /sdcard/Download/agrishield_phase2/
```

SHA256 computed **on the phone**:

```
f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b
```

Exact match to the Phase 1 artifact. The authentic trained model is on the device, intact. The bridge transfer of the 8.9 MB model had failed earlier; rather than retrying it, the script copied the verified file already present in `models/` — so no unverified bytes reached the phone.

---

## 4. Two obstacles found, and how they were handled

### 4.1 Secondary user profile (`user 999`)

`pm list packages` fails with:

```
java.lang.SecurityException: Shell does not have permission to access user 999
```

The phone has a secondary user or Private Space active, and the shell's default user resolves to one it cannot query. Harmless for file transfer — the push to `/sdcard` worked — but any package query or install from ADB must be explicitly scoped with `--user 0`.

### 4.2 Termux APK download truncated — laptop route abandoned

The F-Droid API answered correctly (`suggestedVersionCode = 1002`), but the APK download died partway:

```
FAILED: The decryption operation failed, see inner exception.
Downloaded 12304056 bytes
```

12.3 MB of an approximately 100 MB file. `adb install` then **correctly refused it**: `INSTALL_PARSE_FAILED_NOT_APK`. Nothing broken was installed.

This is the same TLS instability that killed the first curl attempt, and it scales with file size: 8 MB succeeded, 100 MB did not. **The laptop is not a reliable path for large downloads**, so it was abandoned rather than retried — the phone's own network connection is the right route for the APK.

*(A partial file remains at `%TEMP%\termux-fdroid.apk`; Windows clears `%TEMP%` on its own, and it is not referenced by anything.)*

---

## 5. Status ledger

| Item | Status |
|---|---|
| ADB installed and functional | **VERIFIED ON LAPTOP** |
| Phone reachable over ADB | **VERIFIED ON PHYSICAL PHONE** |
| Device profile captured | **VERIFIED ON PHYSICAL PHONE** |
| CPU features / I8MM absence | **VERIFIED ON PHYSICAL PHONE** |
| Payload on the phone, hash-verified | **VERIFIED ON PHYSICAL PHONE** |
| aarch64 runner executes the real model | **VERIFIED UNDER EMULATION** |
| aarch64 output matches x86_64 | **VERIFIED UNDER EMULATION** — 8/8 bit-identical |
| **Model executed on the phone's CPU** | **NOT DONE** — needs Termux + Debian |
| Any `[ARM-PROOT]` latency figure | **NOT MEASURED** |
| Offline verification | **NOT STARTED** |
| Llama integration | **NOT STARTED** — deferred by directive |

---

## 6. Next action

Install Termux on the phone **from the phone's own browser** — `https://f-droid.org/packages/com.termux/` — not via the laptop. Then four short commands set up the Debian userland, after which `run_bench.sh` executes the model that is already sitting on the device, hash-verified.
