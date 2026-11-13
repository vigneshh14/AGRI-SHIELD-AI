# References

[1] Mohanty, S.P., Hughes, D.P. & Salathe, M. (2016). "Using Deep Learning for
Image-Based Plant Disease Detection." *Frontiers in Plant Science*, 7:1419.
Dataset: https://github.com/spMohanty/PlantVillage-Dataset
Note: the repository carries no LICENSE file; the authors request citation of
this paper (see its `CITATION.cff`).

[2] Singh, D., Jain, N., Jain, P., Kayal, P., Kumawat, S. & Batra, N. (2020).
"PlantDoc: A Dataset for Visual Plant Disease Detection." *CoDS-COMAD 2020*.
Dataset: https://github.com/pratikkayal/PlantDoc-Dataset — licence CC BY 4.0.
arXiv: https://arxiv.org/abs/1911.10317

[3] Noyan, M.A. (2022). "Uncovering bias in the PlantVillage dataset."
arXiv:2206.04374. Reports that a model trained on eight background pixels alone
reaches 49.0% accuracy on PlantVillage.

[4] "Quantifying the reliability gap in cross-domain plant disease
classification." *Frontiers in Plant Science* (2026). Reports a 99.73% to 32.05%
collapse from PlantVillage to PlantDoc with mean confidence remaining at 79.76%,
and finds selective prediction reduces but does not eliminate the gap.
https://doi.org/10.3389/fpls.2026.1826962

[5] Sandler, M., Howard, A., Zhu, M., Zhmoginov, A. & Chen, L-C. (2018).
"MobileNetV2: Inverted Residuals and Linear Bottlenecks." *CVPR 2018*.
arXiv:1801.04381

[6] "AgriSentinel: Privacy-Enhanced Embedded-LLM Crop Disease Alerting System."
arXiv:2509.09103. Claims the first embedded-LLM crop disease alerting system,
using a fine-tuned GPT-2 over a curated knowledge pool.

[7] "AGRIADVISOR: On-Device Embedded LLM for Crop Disease Advisory." IRJMETS.
On-device detection plus small-LLM advisory with differential privacy.

[8] ExecuTorch: "A Unified PyTorch Solution to Run AI Models On-Device."
*MLSys 2026*. Documentation: https://docs.pytorch.org/executorch/

[9] Arm (2025). "Arm & ExecuTorch 0.7: Bringing Generative AI to the masses."
https://huggingface.co/blog/Arm/executorch-0-dot-7 — describes KleidiAI int4
matrix-multiply acceleration on Arm CPUs and the role of the I8MM extension
(Armv8.6+) versus SDOT-only cores.

[10] Arm Learning Path: "Run Llama 3 on a Raspberry Pi 5 using ExecuTorch."
https://learn.arm.com/learning-paths/embedded-and-microcontrollers/rpi-llama3/llama3/

[11] Bharat AI-SoC Challenge 2026-27, Problem Statement 1.
https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html
