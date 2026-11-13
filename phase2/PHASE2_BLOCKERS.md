# AGRI-SHIELD AI — Phase 2 Blockers

**As of:** 31 October 2026
**Submission deadline:** 21 November 2026 — **21 days remain**

Ordered by what stands between you and the Phase 2 milestone, not by effort.

---

## B1 — Termux + Debian userland on the phone ⛔ **BLOCKS THE MILESTONE**

**Blocks:** the model actually running on the Infinix NOTE 30 5G — the single most important Phase 2 objective.
**Cost:** ~15 minutes, ~200 MB over wifi, no laptop involvement.
**Who:** you, on the phone.
**Instructions:** `ANDROID_DEPLOYMENT_GUIDE.md` §2–4.

Everything on my side is finished and verified. The payload is built, the Arm binary is cross-compiled and tested, and its output has been proven numerically identical to the desktop build. This is the only thing standing between the project and a real on-device result.

**It also settles an open scientific dispute.** The phone's own `/proc/cpuinfo` `Features` line is captured automatically, which resolves the I8MM contradiction in the Phase 1 report (§5) with measured evidence instead of a spec sheet. See `PHASE2_ENVIRONMENT_AUDIT.md` §5.

---

## B2 — Android platform-tools (ADB)

**Blocks:** USB-based file transfer, `adb shell` measurement, screen capture for the demo video, and the native-app route in B4.
**Cost:** ~5 minutes, 15 MB, no installer — it is a zip you unpack.
**Who:** you, on the laptop.

Verified absent today: `where adb` → not found.

1. Download **SDK Platform-Tools for Windows** from the Android developer site.
2. Unzip to something like `C:\platform-tools`.
3. Add that folder to **PATH**: Start → "Edit the system environment variables" → Environment Variables → under *User variables* select `Path` → Edit → New → `C:\platform-tools` → OK.
4. On the phone: Settings → About phone → tap **Build number** seven times → back → System → Developer options → enable **USB debugging**.
5. Open a **new** terminal and run `adb devices`. Accept the RSA prompt on the phone.

Then re-run `phase2_audit.bat` — its phone section will populate instead of reporting `ADB NOT ON PATH`.

B1 does not depend on this. Do B1 first.

---

## B3 — Git

**Blocks:** version control, and the "reproducible repository" expectation in the submission.
**Cost:** ~5 minutes.
**Who:** you, on the laptop.

Verified absent today. Carried over from Phase 1 and still unresolved. Install Git for Windows, accept the defaults, then `git init` in the project root. The `.gitignore` is already written.

---

## B4 — Android SDK/NDK — **a decision, not a task**

**Blocks:** a native Android application (APK) with ExecuTorch compiled against Bionic.
**Cost:** ~3 GB download, and realistically a full day of build debugging.
**Who:** your call.

I cannot do any part of this from the build container: `dl.google.com` and Maven Central are both blocked, so neither the NDK nor the prebuilt ExecuTorch AAR can be fetched. Confirmed by measurement, not assumption (`PHASE2_ENVIRONMENT_AUDIT.md` §4).

**What it buys:** a latency figure from a real Android app, which is the strongest possible claim for an Arm-SoC competition, plus a demoable APK.

**What B1 already buys:** execution on the same physical cores, the same XNNPACK kernels, the same `/proc/cpuinfo`, and a defensible latency number — with the proot caveat stated plainly.

**My recommendation:** do B1 and B2 first, see the real numbers, and only then decide whether an APK is worth a day of the 21 remaining. If the demo video can show the model running in Termux on the actual phone, the marginal gain from an APK may not justify the risk this close to the deadline. That is your call, not mine.

---

## B5 — Real leaf images for on-device semantic validation

**Blocks:** showing the phone correctly classifying an actual diseased leaf. Does not block B1.

The validation tensors shipped with the payload are deterministic synthetic arrays. They prove the Arm port is *numerically exact* — which is what they are for — but they say nothing about classification accuracy, and all eight happen to predict `healthy`.

The laptop's `datasets/` folder holds only `metadata/split_summary.json`; the images lived in the Phase 1 container, which no longer exists. The PlantVillage GitHub repository is not reachable from this session.

Options, cheapest first: photograph a few tomato leaves with the phone; or re-download a small PlantVillage subset. I have **not** downloaded any dataset — you asked to be consulted before large downloads. Say the word and I will add an image-preprocessing path to the runner.

---

## B6 — Llama 3.2 1B — correctly deferred

Your directive is explicit: *"Do not integrate Llama yet. First prove the vision model works."* No work has been done and none should be until B1 is cleared.

Note for planning: the advisory system still has **0 source-verified chemical intervention records**, and the Llama licence is still unaccepted. Neither has changed since Phase 1.

---

## B7 — Carried-over Phase 1 items, unchanged

- Competition registration and faculty mentor confirmation
- Verification of TNAU records before any chemical recommendation is published
- Tamil-language review by a native speaker
- Demo video
- Five tombstoned files plus `reports.zip` still need manual deletion (I cannot delete files on your machine)
- **Submission by 21 November 2026**

---

## What is NOT blocked

For the avoidance of doubt, none of the following is waiting on anything:

- The trained model — verified authentic on disk today, SHA256 matched
- The aarch64 runner — cross-compiled, emulation-tested, numerically exact against the desktop build
- The payload — complete, self-contained, 13 MB, needs no network once on the phone
- Phase 1 archive — untouched and frozen, as instructed
