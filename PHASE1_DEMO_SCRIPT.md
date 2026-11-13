# PHASE1_DEMO_SCRIPT.md

Shot list for the demonstration video. Target 4-6 minutes. Record each segment as
the capability becomes real.

## Segment 1 — the problem (30 s)
PS1, and the two constraints: no connectivity, and a user who acts on the output.
One line on why a confidently wrong pesticide recommendation is the failure mode
that matters.

## Segment 2 — the leakage finding (60 s) — **ready now**
Show `leaf-map.json` and the Excel provenance. Run `prepare_splits.py` live:

    REPORTABLE: a random split would have leaked 63.97% of test images.

State that hash-based de-duplication estimated 0.64% — wrong by a hundredfold.
Lead with this; it is the strongest methodological moment in the submission.

## Segment 3 — the application (90 s) — **ready now**
Unplug the network visibly. Start `application/app.py`. Upload a leaf. Show
prediction, confidence, severity, advisory. Toggle to Tamil. Show history. Say
plainly that the advisory is a mock.

## Segment 4 — the field gap (60 s) — **ready now**
Run `external_eval.py`. Show 95.62% to 39.14% and
confidence-when-wrong 0.8124. Then the
selective-prediction table, and state that thresholding does not fix it.

## Segment 5 — advisory safety (45 s) — **ready now**
Run `advisor.py --self-test`. Point at the rogue-backend case: chemical text
replaced, not flagged. Then state the limitation — a finite blocklist is a second
line of defence; the real guarantee is that unverified records never reach the
prompt.

## Segment 6 — ExecuTorch on Arm (60 s) — **PENDING HARDWARE**
Record once GATE 1 passes: `adb shell` running `llama_main`, phone in airplane
mode, tokens streaming. Show `uname -a` and the `Features` line from
`/proc/cpuinfo`.

## Segment 7 — honest close (30 s)
What works, what does not, and the field accuracy. Name the limitations; a
submission that does so is more credible than one that does not.
