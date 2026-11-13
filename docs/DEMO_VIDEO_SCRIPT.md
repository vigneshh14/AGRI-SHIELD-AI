# Demo video script (Phase 1, ≤ 5 min)

Record the phone screen (Android screen recorder) plus a second camera or the laptop
webcam showing the phone in your hand, so the jury can see it's real. One take per
segment is fine; cut them together afterwards.

| # | Time | Show | Say (short) |
| --- | --- | --- | --- |
| 1 | 0:00–0:25 | Title card: AGRI-SHIELD AI, PS1, your name, CEG | "Farmers lose crops to leaf diseases, and many fields have no reliable internet. This runs entirely on the phone." |
| 2 | 0:25–0:45 | Swipe down: **airplane mode ON**, Wi-Fi off, mobile data off | "Everything you see from here is offline." |
| 3 | 0:45–1:45 | Open app → photograph a diseased tomato leaf → diagnosis + confidence appears → advisory text **streams** | "MobileNet classifies the leaf on the CPU. Then Llama 3.2 1B, running through ExecuTorch on this phone, writes the advice." |
| 4 | 1:45–2:20 | Scroll to the dose table + "Source: TNAU" link + the no-interval note | "Product names and doses never come from the language model. They come from TNAU's published recommendations, shown with the source." |
| 5 | 2:20–2:50 | Photograph something unclear (blurred leaf / non-tomato leaf) → **abstain** message, no chemicals | "When the model isn't confident, it refuses to recommend any chemical and refers the farmer to the extension officer." |
| 6 | 2:50–3:20 | Tamil UI: disease name in Tamil | "Disease names and the interface are in Tamil and English." |
| 7 | 3:20–4:05 | Laptop: `adb shell cat /proc/cpuinfo` (Features line), `adb logcat -s AGRI_ARM` showing the stats line; `benchmarks/results_arm.md` | "Measured on this phone: Dimensity 6080, Armv8.2 with dot-product, no I8MM. These are the real timings." Read 2–3 numbers. |
| 8 | 4:05–4:40 | GitHub repo page with the green test check | "The safety gate is tested on every push: 70 checks." |
| 9 | 4:40–5:00 | Limitations slide | "Tomato only for now; severity is experimental; field accuracy on real photos is X%. Phase 2 adds chilli, potato and pests." |

## Rules
- Only show numbers that are in `benchmarks/results_arm.md`.
- If Llama isn't integrated into the app by recording day, show segment 3 with the
  ExecuTorch runner on the phone instead, and say so in the narration.
- Upload as YouTube **unlisted** (or Drive "anyone with the link"). Test the link in a
  private window before submitting.
