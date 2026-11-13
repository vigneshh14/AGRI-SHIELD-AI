# PHASE1_SUBMISSION_CHECKLIST.md

Deadline 23 Nov 2026. **Internal target 21 Nov.**

## Blocking — mandatory requirements
- [ ] Install Git (M11 impossible without it)
- [ ] Install Android platform-tools / adb
- [ ] Request Llama 3.2 licence on Hugging Face
- [ ] Confirm challenge registration and faculty mentor
- [ ] Enable USB debugging; run `probe_phone.bat`
- [ ] **GATE 1**: Llama via ExecuTorch generating on the phone, airplane mode
- [ ] Record `[ARM]` benchmarks into `benchmarks/results_arm.md`
- [ ] Create the GitHub repository and push
- [ ] Submit via the challenge form by 21 Nov

## Strongly recommended
- [ ] Re-train with ImageNet pretraining on the laptop
- [ ] Verify TNAU chemical records and set `sourced: true`
- [ ] Review the Tamil strings as a native speaker
- [ ] Implement leaf segmentation before any field severity claim
- [ ] Add temperature scaling for calibrated confidence
- [ ] Record demo segments 2-5

## Complete and verified
- [x] Dataset acquired, licensing documented
- [x] Leakage-proof splits, 0 straddle violations
- [x] Classifier trained: 0.9561966 accuracy, 0.9506470 macro F1
- [x] External PlantDoc evaluation: 0.3914 primary, 0.3414 sensitivity
- [x] Independent audit, 17/17 checks
- [x] Classifier exported to ExecuTorch, numerically verified
- [x] Knowledge base safety gate, tested
- [x] Advisory layer with output guard, adversarially tested
- [x] Offline application, socket-level verified
- [x] Severity estimator corrected; marked EXPERIMENTAL
- [x] Consistency audit, 6 items, 2 retractions
- [x] Phase 1 document set, single authoritative version each
