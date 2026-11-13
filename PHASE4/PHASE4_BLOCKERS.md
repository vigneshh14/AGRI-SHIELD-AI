# AGRI-SHIELD AI — Phase 4 Blockers

**As of:** 31 October 2026 · **Deadline:** 21 November 2026 — **21 days remain**

---

## B1 — No Android toolchain anywhere ⛔ **BLOCKS THE APK**

**Blocks:** compilation. There is no APK and none can be produced yet.

| Where | State |
|---|---|
| Build container | `dl.google.com` **blocked**, Maven Central **blocked** → no SDK, no AAR |
| Laptop (measured 10:01 today) | no JDK, no Android SDK, no NDK, no Gradle, no Android Studio, no CMake |

**Needs:** Android Studio (~1.2 GB) plus SDK 34 and Build-Tools (~660 MB). Full accounting in `DEPENDENCY_AND_DOWNLOAD_REPORT.md`.

**Nothing has been downloaded or installed.** This needs your approval.

**Risk worth naming:** your laptop's TLS truncated a 100 MB download today (`SEC_E_DECRYPT_FAILURE` at 12.3 MB of ~100 MB), and Windows `curl` failed on an 8 MB file before PowerShell succeeded. Android Studio is about twelve times the size of the transfer that already failed. Its downloader resumes, so this is recoverable, but expect repeated attempts.

---

## B2 — Android JPEG decoder parity is unmeasured

**Blocks:** the claim that the Phase 4 parity result describes the device.

The 9/9 bit-exact result holds **given identical input pixels**. It says nothing about whether Android's `BitmapFactory` decodes a JPEG to the same bytes Pillow does — JPEG decoding has implementation freedom in chroma upsampling and the IDCT, and the two use different libraries.

**Prepared and waiting:** `DecoderParityTest.decoderParity` measures it on-device against a bundled reference JPEG and its Pillow decode, writes the numbers to JSON, and fails only if the divergence propagates past 0.1 in the tensor — the threshold at which it would rival the `createScaledBitmap` error this project already rejected.

**It cannot run until B1 clears.** Until then, "bit-exact preprocessing" carries that qualifier everywhere it appears.

---

## B3 — Still no real leaf photographs

Carried from Phase 3, unchanged. Without them the app can be demonstrated only on whatever image is to hand, and no real-image result exists on any platform.

This blocks Phase 3's milestone independently of the APK. Shooting guidance is in `PHASE3_BLOCKERS.md` §B1 — centred leaf, filling the frame, square or 4:3, never 16:9.

---

## B4 — ~~Gradle wrapper JAR not included~~ ✅ **Resolved (v3)**

The official wrapper (`gradlew`, `gradlew.bat`, `gradle-wrapper.jar`) is now shipped, generated offline by a local Gradle 8.14.3. JAR SHA-256 `7d3a4ac4…6172` matches Gradle's published checksum. See `PHASE4_ENGINEERING_AUDIT.md` §6.

---

## B4a — 108 MP full-resolution captures will be refused (new)

A 12000×9000 frame needs ~324 MB RGB + ~432 MB native bitmap. The app refuses it with a message instead of crashing or silently shrinking it. Whether this phone delivers full or binned resolution to `ACTION_IMAGE_CAPTURE` is **unverified** — test on device. Supporting it would need a documented downsample with its own parity strategy (your decision).

---

## B5 — Phone storage at 98 %

5.8 GB free when last measured, already carrying Termux and a Debian rootfs. The APK is only ~60–80 MB, so this is not blocking, but it leaves little headroom.

---

## B6 — Llama 3.2 1B — still correctly deferred

Unchanged. Licence unaccepted; the knowledge base still holds **0 source-verified chemical intervention records**. The app ships classification only, with no pesticide, dosage or treatment output of any kind.

---

## What is NOT blocked

- **Preprocessing parity** — 9/9 bit-exact on the JVM, compiled by a real Kotlin compiler and run on OpenJDK 21
- **Runtime compatibility** — resolved from the artifact: `ET12`, XNNPACK-only delegation, zero undelegated operators, and `executorch-android:1.5.1` matches the exporting version exactly
- **The complete project source** — Gradle + verified wrapper, manifest, four screens, ExecuTorch integration, ViewModel lifecycle, memory pre-flight, 31/31 JVM unit tests passing, instrumented decoder test ready
- **Phase 1, 2 and 3 deliverables** — untouched; the `[ARM-PROOT]` result remains the verified fallback
