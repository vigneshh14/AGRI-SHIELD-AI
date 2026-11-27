"""Python (Pillow) vs Kotlin (JVM) preprocessing parity test.

Both sides consume byte-identical source images and must produce the same
[1,3,96,96] float32 tensor. The Python side is the Phase 3 pipeline that every
verified result in this project was produced with.
"""
import json, struct, subprocess, sys, os
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
JARS = "/tmp/kjk/x/run_kotlin_kernel/jars"
KOUT = "/tmp/kout"


def python_tensor(img: Image.Image) -> np.ndarray:
    """The verified Phase 3 transform: Resize(109) shorter side, CenterCrop(96),
    ToTensor, Normalize."""
    w, h = img.size
    short = min(w, h)
    if short != 109:
        long_ = max(w, h)
        ns, nl = 109, int(109 * long_ / short)
        nw, nh = (ns, nl) if w <= h else (nl, ns)
        img = img.resize((nw, nh), Image.BILINEAR)
    w, h = img.size
    top = int(round((h - 96) / 2.0)); left = int(round((w - 96) / 2.0))
    img = img.crop((left, top, left + 96, top + 96))
    a = np.asarray(img, np.uint8).astype(np.float32) / 255.0
    return np.ascontiguousarray(((a - MEAN) / STD).transpose(2, 0, 1))


def kotlin_tensor(arr: np.ndarray, tag: str) -> np.ndarray:
    h, w, _ = arr.shape
    rgb = f"/tmp/par_{tag}.rgb"; out = f"/tmp/par_{tag}.f32"
    with open(rgb, "wb") as f:
        f.write(struct.pack(">ii", w, h)); f.write(arr.tobytes())
    env = dict(os.environ); env.pop("JAVA_TOOL_OPTIONS", None)
    r = subprocess.run(
        ["java", "-cp", f"{KOUT}:{JARS}/kotlin-stdlib-2.3.10-RC.jar",
         "org.agrishield.ai.preprocess.AgriShieldPreprocess", rgb, out],
        capture_output=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:400])
    data = open(out, "rb").read()
    n = 3 * 96 * 96
    return np.array(struct.unpack(">%df" % n, data[:4 * n]), np.float32).reshape(3, 96, 96)


def main():
    rng = np.random.default_rng(31102026)
    cases = []

    def leaf_like(w, h):
        base = (120 + 60 * np.sin(np.linspace(0, 90, h))[:, None]
                + 40 * np.cos(np.linspace(0, 120, w))[None, :]
                + rng.normal(0, 18, (h, w)))
        return np.clip(base[:, :, None] * np.array([0.45, 0.85, 0.35]), 0, 255).astype(np.uint8)

    cases.append(("leaf_4000x3000", leaf_like(4000, 3000)))
    cases.append(("leaf_3000x4000", leaf_like(3000, 4000)))
    cases.append(("leaf_1920x1080", leaf_like(1920, 1080)))
    cases.append(("square_1024", leaf_like(1024, 1024)))
    cases.append(("noise_640x480", rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)))
    cases.append(("noise_480x640", rng.integers(0, 256, (640, 480, 3), dtype=np.uint8)))
    cases.append(("small_109x140", rng.integers(0, 256, (140, 109, 3), dtype=np.uint8)))
    cases.append(("tiny_97x96", rng.integers(0, 256, (96, 97, 3), dtype=np.uint8)))
    cases.append(("exact_109", rng.integers(0, 256, (109, 109, 3), dtype=np.uint8)))

    results, worst_max = [], 0.0
    print(f"{'case':<18} {'size':>12}  {'max|d|':>10} {'mean|d|':>10} {'RMS':>10}  verdict")
    print("-" * 74)
    for tag, arr in cases:
        h, w, _ = arr.shape
        ref = python_tensor(Image.fromarray(arr, "RGB"))
        kot = kotlin_tensor(arr, tag)
        d = np.abs(ref - kot)
        mx, mn, rms = float(d.max()), float(d.mean()), float(np.sqrt((d ** 2).mean()))
        worst_max = max(worst_max, mx)
        verdict = "BIT-EXACT" if mx == 0.0 else "differs"
        print(f"{tag:<18} {w:>5}x{h:<6}  {mx:>10.3e} {mn:>10.3e} {rms:>10.3e}  {verdict}")
        results.append({"case": tag, "width": w, "height": h,
                        "max_abs_diff": mx, "mean_abs_diff": mn, "rms_diff": rms,
                        "bit_exact": mx == 0.0})

    n_exact = sum(1 for r in results if r["bit_exact"])
    print("-" * 74)
    print(f"bit-exact: {n_exact}/{len(results)}   worst max|diff| = {worst_max:.6e}")

    json.dump({
        "python_side": "Pillow BILINEAR + torchvision-equivalent CenterCrop/ToTensor/Normalize",
        "kotlin_side": "AgriShieldPreprocess.kt, compiled by K2JVMCompiler, run on OpenJDK 21",
        "cases": results,
        "n_cases": len(results), "n_bit_exact": n_exact,
        "worst_max_abs_diff": worst_max,
        "all_bit_exact": n_exact == len(results),
    }, open("kotlin_parity_report.json", "w"), indent=2)
    print("wrote kotlin_parity_report.json")
    return 0 if n_exact == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
