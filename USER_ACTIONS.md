# USER_ACTIONS.md — blockers that need you

Current 2026-10-31. Everything not listed here is either done or
is work I can continue without you.

## Toolchain status

Last **verified** reading: `audit_windows.bat`, 30 Oct 2026 20:53.

| Tool | Status at last audit | Needed for |
| --- | --- | --- |
| Git | **NOT INSTALLED** | M11 — GitHub hosting is mandatory |
| adb / platform-tools | **NOT INSTALLED** | every `[ARM]` figure, M3 and M4 |
| Python 3.13.15 | present | ExecuTorch range is 3.10-3.12; untested at 3.13 |
| WSL | not installed | recommended for the Android NDK cross-compile |

**This has not been re-verified since.** `environment_audit_raw.txt` is unchanged
since that reading, so if you have installed Git or adb, the audit has not picked
it up. Double-click `audit_windows.bat` and tell me — it rewrites the file and I
read it directly.

## Blockers, ordered by cost of leaving them late

| # | Action | Why it blocks | Time |
| --- | --- | --- | --- |
| 1 | Install Git for Windows | M11 is impossible without it — no repo, no submission | 5 min |
| 2 | Install Android platform-tools, add to PATH | No adb means no model on the phone, so no `[ARM]` number, so M3 and M4 stay unsatisfied | 5 min |
| 3 | Request the Llama 3.2 licence on Hugging Face (`meta-llama/Llama-3.2-1B-Instruct`) | Approval is not instant and is outside both our control. M1 blocked | 5 min |
| 4 | Confirm challenge registration + faculty mentor are on record | If this is wrong, nothing else matters. Registration closed 19 Oct | 15 min |
| 5 | Enable USB debugging, plug the phone in, tap "Allow" | Required before any on-device run | 2 min |
| 6 | Verify TNAU/ICAR chemical records and set `sourced: true` | Until then every advisory abstains | 1-2 hr |
| 7 | Review the Tamil strings | They are mine and unreviewed; you are the native speaker | 30 min |
| 8 | Record the demo video | Segments 2-5 are recordable today; see `PHASE1_DEMO_SCRIPT.md` | 1 hr |
| 9 | Submit the form by 21 Nov | Only you can | 20 min |

## Phone details I need

From Settings → About phone: model and chipset, Android version, total RAM, free
storage (need ~3 GB). Or just run `probe_phone.bat` once adb works — it writes
`phone_profile.txt` and I read it directly.

The chipset decides whether the CPU has **I8MM**, which determines the int4 Llama
performance story on Arm. It goes in the report either way.

## Completed — no longer needs you

- Windows environment audit (done 30 Oct via computer use; results in `environment_audit.md`)
- Dataset acquisition and licensing review
- Hardware target decision (Arm Android phone; LPC2148 surveyed and ruled out)
