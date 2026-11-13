# PHASE1_COMPLIANCE.md

Status 2026-10-31. **Implemented** = code exists and runs. **Tested** = automated
test passes. **Verified** = measured against an independent reference.
**Hardware-verified** = measured on Arm. **Pending** = not started or blocked.

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| M1 | Llama-family model | **PENDING** | licence not approved; no model obtained |
| M2 | Llama owns advisory/reasoning | Implemented, tested (mock only) | `advisor.py --self-test` |
| M3 | ExecuTorch as on-device runtime | **PARTIAL** — classifier verified, Llama pending | `agrishield_tomato4.pte`, 8.891 MB |
| M4 | Runs on Arm hardware | **PENDING** | adb not installed, no device |
| M5 | Fully offline | **Verified** | 0 outbound connections under socket block |
| M6 | Image disease detection | **Verified** | 0.9562 in-domain / 0.3914 field |
| M7 | Severity classification | Implemented, tested, **EXPERIMENTAL** | background sensitivity unresolved |
| M8 | Treatment recommendations | Implemented; **abstains always** | 0 source-verified records |
| M9 | Multiple local languages | **Tested** | Tamil + English end to end |
| M10 | Region-specific advisory | Partial | TNAU records drafted, unverified |
| M11 | Hosted on GitHub | **PENDING** | Git not installed |
| M12 | Submitted before 23 Nov | **PENDING** | target 21 Nov |

## Honest summary

**M1 and M4 are unsatisfied. M3 is satisfied for the vision classifier only.**
No Arm performance figure exists. A mock backend does not satisfy the Llama
requirement and is nowhere presented as doing so.

M11 is blocked on a five-minute install, not on engineering.
