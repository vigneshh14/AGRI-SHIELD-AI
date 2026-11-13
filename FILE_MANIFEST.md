# FILE_MANIFEST.md

60 files in the archive; 58 checksummed (10.36 MB).

59 files in the archive; 57 checksummed (10.36 MB).

**Self-referential exclusion.** `FILE_MANIFEST.md` and `reports/file_manifest.json` are in the archive but carry no checksum of their own, since a file cannot contain its own hash. If an external checker reports exactly two mismatches, these are they.

## Excluded from the archive, and why
| Item | Reason |
| --- | --- |
| `datasets/raw/` | PlantVillage images, 116 MB; rebuild via `INSTALL_NEXT.md` |
| `*.pt` checkpoints | regenerable by `train.py`; the deployable `.pte` is included |
| `datasets/metadata/leaf-map.json` | 2.4 MB, ships with the dataset repository |
| `models/mobilenet_v2_xnnpack.pte` | the RANDOM-WEIGHT hello-world model; shipping it beside the trained classifier would mislead |
| `logs/` | runtime residue from test runs, not a project artifact |
| `reports/gen_reports.py` | superseded by `build_final.py`; removed so two generators cannot disagree |
| `*.zip` | no nested archives |
| `README2.md`, `USER_ACTIONS2.md`, `CONSISTENCY_AUDIT1.md`, `PHASE1_REPORT1.md` | duplicates created outside this project; tombstoned on the user's machine |
| credentials | none exist in this project |

## Authoritative documents
`README.md` · `PHASE1_REPORT.md` · `PHASE1_RESULTS.md` · `PHASE1_COMPLIANCE.md` · `PHASE1_DEMO_SCRIPT.md` · `PHASE1_SUBMISSION_CHECKLIST.md` · `CONSISTENCY_AUDIT.md` · `REFERENCES.md` · `USER_ACTIONS.md` · `FINAL_AUDIT.md` · `reports/PHASE1_REPORT.pdf`

`PROJECT_PROGRESS.md`, `IMPLEMENTATION_LOG.md` and `VERIFICATION_REPORT.md` are dated historical logs, not status reports.

## Files

| Path | Bytes | SHA256 |
| --- | --- | --- |
| `.gitignore` | 411 | `a273a109afedc6834907a3115b77bfb3569283ca72a44623dec4d809cfeb4218` |
| `CLAUDE.md` | 4061 | `b2207a8b8576797a8b578e5da137a5487f9594c8b436f5b7d2dde909f83de716` |
| `CONSISTENCY_AUDIT.md` | 11186 | `ae4961e4ec265a8941e53333436f8b2f8e4b5275633c61a2036d65fd2269da5e` |
| `FINAL_AUDIT.md` | 6340 | `f44a76bc12f519dc7dfeb808ed55b0a04cd43d494c5dd1610c1d6e2afa18ba21` |
| `IMPLEMENTATION_LOG.md` | 1756 | `bcbc16fa94096e2e920ccc3a1a5b66cbc458f562a0a6d190149f07cedf1407fe` |
| `INSTALL_NEXT.md` | 3994 | `481155093f7b12cf229373b2bb43e2d4d6a13895b8adea46a877860aca5226a7` |
| `PHASE1_COMPLIANCE.md` | 1652 | `01e8f2a4c0ce6dc63148decafd09af566238ff523257d679533a91c0ff8d42b1` |
| `PHASE1_DEMO_SCRIPT.md` | 1910 | `f2afacc28ff00c4a6fd77c780436dc61eefb1109a844f07aa1013577572c6187` |
| `PHASE1_REPORT.md` | 22006 | `9ae3173efaafcd785406a2c0b898b2729be9cddcee90e9d39f7725656db2bd11` |
| `PHASE1_RESULTS.md` | 2347 | `005156c1400e4f2746aea35e4418322d92b58b11cc24a21701a3db16b22d1475` |
| `PHASE1_SUBMISSION_CHECKLIST.md` | 1617 | `90e07c0c53f8dac1f01eb86fe5f660d48dccadb456cc8d5d644d4f3926ba06da` |
| `PROJECT_PROGRESS.md` | 6397 | `3f86f9f722418c8dd48028a99faffe7aee7aae786a47c4eb7fea10f73aea6f72` |
| `README.md` | 5717 | `f5bbdb9bacf28768e07c8ff4f839d602879dfa9c0a6b93ea217f48eb45c5da15` |
| `REFERENCES.md` | 2391 | `430aad8ffdc9d5ab628bc9c7972674301194076712e6c86f6739881c3da65cbb` |
| `USER_ACTIONS.md` | 2655 | `710446e17cf710e165e608643e4a76d614d6e4f167709d0df203cba0057c3209` |
| `VERIFICATION_REPORT.md` | 4384 | `3bbbecea9d0bbdee6b64e441e0615beb0595a2421d09da3cce4b154a970f4289` |
| `application/app.py` | 12671 | `3698bda0bcfe28e9dbd87d040081f98e0fd95da04124d5cb892cd587efabdf72` |
| `audit_windows.bat` | 2290 | `ea00b475cf8368ad960a8aaad31a99f1158339a797aaf4ed88eab36f6db80eb6` |
| `benchmarks/results_arm.md` | 333 | `bd911f07fe097cad2f9829e8d0e89a671cdcfb02e15363f55a95316ac68b8a58` |
| `benchmarks/results_desk.md` | 1017 | `a1dea23d25b98a528d16ef7ab77539da167f2b31855af3564c1f4966692916a0` |
| `datasets/metadata/split_summary.json` | 1131 | `6584a74a3fd1013400f16a10aaed79527c804d99b70cfd85a3056f79867cc4e3` |
| `datasets/metadata/splits.csv` | 888530 | `01610ba556ff9804e96ba76039c8708dbd1041ad51c44df0b33d3ec7a2349290` |
| `deployment/arm/ANDROID_DEPLOYMENT.md` | 5915 | `1cee35f7e388bcf6c6aa8535d4878b2f67ffd10f5ad72cf3f52a041bf31d0325` |
| `disease_detection/evaluation/audit.py` | 8067 | `88a5e1cd9a23bc22b093ba7c5dba4bfe6bbb17dc9c265a0b5354c13823c73bae` |
| `disease_detection/evaluation/external_eval.py` | 7364 | `b40bd98a4468766f620c8e32769c11486c580ad9ce6a24d45c7de5b8603fcd9c` |
| `disease_detection/inference/export_classifier.py` | 2070 | `6aea0374a083443fd011b0aa9af5e1db51437618991336bd64a5b06b1c951f26` |
| `disease_detection/inference/predict.py` | 5444 | `c2e8bd5656475e7502cc4998b6c22c79f00591c5b3b31962f7d07c9953aaf03c` |
| `disease_detection/training/prepare_splits.py` | 9577 | `8ef5a1c6d98a7955bcdb8175ba85638d08783e3198451830c20818bcde776c23` |
| `disease_detection/training/runs/smoke/confusion_matrix.png` | 43453 | `a83815ce7540231e7367224e69fbd8075a10333300fd4e96da167b937b6df5e6` |
| `disease_detection/training/runs/smoke/metrics.json` | 1428 | `9951fa2669311c4424fe36c86331349e62003b32c0001d8c42942e126b64cd84` |
| `disease_detection/training/runs/smoke/training_curves.png` | 67391 | `22d04220a20e2e02b8ccaac9862c4d4283c8c8337482027b0c918ca3b2a7e636` |
| `disease_detection/training/train.py` | 14278 | `27eabbc4092507a29d647907d7b84033b7bde0d2f55dc2289ad3b66b2da5c0c4` |
| `documentation/executorch_setup.md` | 3145 | `960567e7117b0d55a681decd3cd68102bd550f2713a17d1795b5d95df3427186` |
| `environment_audit.md` | 2741 | `4f71af53ec446c1d2e844fb3d2975a7b92bbdc6b2b66a7f8602bc8bee1c61ce6` |
| `environment_audit_raw.txt` | 2403 | `1df130c137d3ffb09942c2dcd884dfac1de12bfa0c21646607b1c1fd68c29d62` |
| `knowledge_base/diseases.json` | 11475 | `b32639f1f7568d3ca2794e70ebce439dc9f1f4c71e4be2a24b8d60dc1766d430` |
| `knowledge_base/retrieval.py` | 9145 | `0d647ac5389ae45a7019eceb0acd52279a166551273f06316519a5b716d24780` |
| `llama_advisory/advisor.py` | 14107 | `1514bfeb73b0a6c6eb6f1fa11e9918ce7d2438b8c180758ecf9c105d6b79154a` |
| `llama_advisory/model/README.txt` | 66 | `34e9a24ab3af4473371c6cf32142779778e628bc417ffe7d73c26d9de1d61395` |
| `llama_advisory/prompts/advisory_en.txt` | 789 | `2a037ec7564792f63087053b1b90be03d9887ee49a1c8cbd72ab4f01bd47dfa7` |
| `llama_advisory/prompts/advisory_ta.txt` | 1893 | `9ecea4b645bff8cd496def14c52ec1ab0cf2fe8e668535261cb926e92550f1b3` |
| `models/agrishield_tomato4.json` | 371 | `3a295c21de032f71d656317a71bbe918b33c6b09b1b4ad3e086bdb43cc52158c` |
| `models/agrishield_tomato4.pte` | 8890640 | `f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b` |
| `probe_phone.bat` | 1939 | `5c6d2e79ff1b896f37af5e10d0f65ed1be6cb3e8e2c6a049f7cfc54e748f2d44` |
| `reports/PHASE1_REPORT.pdf` | 93012 | `8f345d4c09a8757687091e42e0b3274f57c00e7c33f16245d509bc354ea26a1e` |
| `reports/audit.json` | 613 | `04baed08668d6d0515d235cce59c556bd52fdc155de869f6cb5add25862425e3` |
| `reports/build_final.py` | 34477 | `5d9c3fd23bff5db469bcca36a86cd47b0a5a4228da50ac1df2e8cbadff0a3290` |
| `reports/consistency_check.py` | 4803 | `5c3a464c69d9cfe972dc36fd86142d047b6edfb99c074b33adfee0eea4e2c9e7` |
| `reports/external_plantdoc.json` | 4603 | `9a9d454a57a4631d2e0471c7ca78b32dfdcf21e5ecdd5917c784edd986fb959d` |
| `requirements-executorch.txt` | 166 | `c71b53b3c069018501291229e8ea18f5e17c522484640f21435df9b452380098` |
| `requirements-vision.txt` | 158 | `18d37b444cc130e567db7b2c44ebe9ba7fd2682617d9a3c541c4c9e78f6c5dfd` |
| `runs/tomato4_scratch/confusion_matrix.png` | 50354 | `f2977deea95dc206035846861071778a6d64d7b846c9bfcd55599c2a0de249e9` |
| `runs/tomato4_scratch/metrics.json` | 5369 | `d2759182dff6fcd091ed832cc6c34cb0d9ebf9dd6240aab0db9f7ce66adccd03` |
| `runs/tomato4_scratch/training_curves.png` | 64223 | `3deec6705da4d67583859d888a3ef87ff37ba2a998d08c8bb6e8cb232a40b386` |
| `scripts/export_hello.py` | 2866 | `63d1349d4ce46265aacd1b61d2258f1bd73c566c955cb211d06da1c6cef2e77b` |
| `scripts/run_hello.py` | 1806 | `484614244c2e262a36139c0ec92c0ef44cdb4786488edfd86dd1a28393592d51` |
| `severity_estimation/severity.py` | 8248 | `cb63726b6e921d9bdaefb81a782f4d3ebefc4bda7959ba4c1eb94365df215d90` |
| `test_results.md` | 3229 | `441a747ad54ffc985c63ffa10eecad0a2896f1a397f7df333458202a867bfd5e` |
