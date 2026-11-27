# Demo video: 2 minutes, 1080p, 16:9, MP4, public

The organisers asked for 2 minutes, 1920x1080, 16:9, MP4, uploaded to YouTube or Drive
and set to Public. Record the laptop screen with the phone mirrored or filmed beside
it; a phone screen recording alone is 9:16 and must be placed on a 16:9 canvas.

Tools that need nothing installed: Windows Game Bar (Win+G) records a window as MP4;
Clipchamp (built into Windows 11) cuts clips and exports 1080p MP4. To show the phone
on the laptop, `scrcpy` mirrors it over the same adb connection.

Say only what the clip on screen proves. Two versions of the middle segment are
given: use A if Llama has run on the phone, B if it has not.

| Time | On screen | Narration (about 260 words in all) |
| --- | --- | --- |
| 0:00-0:12 | Title card: AGRI-SHIELD AI, PS1, your name, CEG | "AGRI-SHIELD AI diagnoses tomato leaf disease and gives treatment advice on an Arm phone, fully offline." |
| 0:12-0:25 | Phone: airplane mode switched on; then the app's About screen showing "no INTERNET permission" | "The phone is in airplane mode, and the app does not even ask for network permission." |
| 0:25-0:55 | Phone: pick a diseased leaf photo; class, confidence and probabilities appear | "A MobileNetV2 classifier runs through ExecuTorch on the phone's Cortex-A76 cores in about 12.5 milliseconds." |
| 0:55-1:25 A | Advisory text streaming, badge "Written by Llama 3.2 1B · ExecuTorch · on this phone, offline", then the TNAU dose table with source link | "Llama 3.2 1B, quantised to 4 bits, writes the advice on the device. It is never given product names or doses: those come straight from TNAU's published recommendations, with the source." |
| 0:55-1:25 B | `results_arm_proot.md` table, then the advisory code and the 73-check test badge on GitHub | "On-device classifier results: 12.5 ms median offline, matching the desktop to 2 millionths of a logit. The Llama advisory stage is built and tested; its on-phone run is the remaining Phase 1 step." |
| 1:25-1:40 | A blurred or non-tomato photo: no product shown, "No product is recommended for this result" | "When the model is unsure, the app recommends nothing and refers the farmer to the extension officer." |
| 1:40-1:55 | Report table: 95.6% lab accuracy vs 39.1% on field photos | "Honest limit: 95.6% on lab images, 39.1% on field photos. That gap is why safety rests on what the model is given, not on its confidence." |
| 1:55-2:00 | GitHub repo URL | "Code, APK and report: github.com/vigneshh14/AGRI-SHIELD-AI." |

## Before uploading

- Length 2:00 or under. Export 1920x1080 MP4.
- Every number spoken appears in the report.
- Upload, set to Public, open the link in a private window to check it plays.
