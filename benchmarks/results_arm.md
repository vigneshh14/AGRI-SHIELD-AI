# [ARM] results: Infinix NOTE 30 5G (MediaTek Dimensity 6080), airplane mode

Every number here was measured on the phone, offline. Nothing is copied from the laptop.
Empty cells mean "not yet measured", never "zero".

## Device
| Item | Value | How measured |
| --- | --- | --- |
| `/proc/cpuinfo` Features line | | `adb shell cat /proc/cpuinfo` |
| Android version | | `adb shell getprop ro.build.version.release` |
| ExecuTorch AAR version | | `app/build.gradle` |

## Llama model files
| File | Size (bytes) | SHA256 | Source URL |
| --- | --- | --- | --- |
| `llama3_2_1b_spinquant.pte` | | | https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET |
| `tokenizer.model` | | | same repo |

## Llama advisory, 10 consecutive runs (stats copied verbatim from logcat `AGRI_ARM`)
| Run | Class / conf | wallMs | stats JSON | fromLlama | violations |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

## Classifier
| Metric | Value |
| --- | --- |
| Median latency (ms) | |

## Memory
| Phase | PSS (MB) | Command |
| --- | --- | --- |
| Idle, app open | | `dumpsys meminfo <pkg>` |
| During Llama generation | | |
