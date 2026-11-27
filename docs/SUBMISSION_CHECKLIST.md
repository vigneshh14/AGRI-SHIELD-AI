# Phase 1 submission checklist

Form: https://forms.gle/3KyscquPFG8rS9ASA (one submission only). Original deadline
25 Nov 2026; extension to 30 Nov 2026 offered on 27 Nov against a written justification.
Required: public repo link, public 2-minute 1080p MP4 video link, final report (.pdf/.docx)
covering methodology, results, hardware utilisation and optimisation techniques.

## Mandatory (any unchecked box = do not submit yet)
- [ ] Llama 3.2 1B runs on the phone through ExecuTorch, in airplane mode, with a screen recording
- [ ] Llama produces the advisory text, from the gated prompt
- [ ] The whole pipeline runs with no network (airplane mode visible in the video)
- [ ] The code is in a public GitHub repo that you push to
- [ ] Submitted through the official challenge form (not email)

## Deliverables (PS1)
- [ ] Source code: repo with README, setup steps, model download URL + SHA256
- [ ] Application: APK attached to a GitHub Release
- [ ] Demo video: link opens when signed out
- [ ] Technical report: PDF in the repo and/or uploaded to the form

## Report must contain
- [ ] I8MM correction (`REPORT_I8MM_CORRECTION.md`)
- [ ] Architecture: classifier on CPU (XNNPACK) → confidence gate → KB retrieval → Llama (ExecuTorch, XNNPACK)
- [ ] Every number tagged [SIM] / [DESK] / [ARM]
- [ ] KB provenance: each chemical with its TNAU URL and verification date (13 Nov 2026)
- [ ] Safety design: abstain path, output guard, doses taken only from the KB; test result 70/70 on the JVM [DESK]
- [ ] Field test on real photos, including the poor results
- [ ] Limitations: tomato only; severity experimental; Tamil reviewed or not; no spray interval from source
- [ ] Phase 2 plan: chilli/potato, pests, Tamil generation, NPU/power

## Hygiene
- [ ] No `.pte`, tokenizer, dataset or HF token committed (`git log --stat` checked)
- [ ] `tools/gen_kb_kotlin.py` re-run after any KB edit; tests pass
- [ ] Faculty mentor has seen it
- [ ] Confirmation saved
