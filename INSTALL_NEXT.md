# Install these four things — then training and the phone path unblock

All four are quick. Items 1 and 2 are on the critical path for mandatory
requirements; do them first.

## 1. Git for Windows — REQUIRED, blocks GitHub hosting

https://git-scm.com/download/win — run the installer, accept the defaults.

Verify (new terminal): `git --version`

## 2. Android platform-tools (adb) — REQUIRED, blocks every [ARM] number

https://developer.android.com/studio/releases/platform-tools

Download "SDK Platform-Tools for Windows", unzip to a stable location such as
`C:\platform-tools`, then add that folder to PATH:

> Settings -> System -> About -> Advanced system settings -> Environment
> Variables -> under "User variables", select `Path` -> Edit -> New ->
> `C:\platform-tools` -> OK

Verify (new terminal): `adb version`

You do **not** need the full Android Studio for Phase 1 — platform-tools alone
is enough to push a model and run the ExecuTorch binary over `adb shell`.

## 3. Test whether Python 3.13 works with ExecuTorch

Try the Python you already have first:

```
cd %USERPROFILE%\Documents\AGRI_SHIELD_AI
py -3.13 -m venv env-executorch
env-executorch\Scripts\python -m pip install --upgrade pip
env-executorch\Scripts\pip install executorch torchvision
```

If that resolves, run the verification:

```
env-executorch\Scripts\python scripts\export_hello.py
env-executorch\Scripts\python scripts\run_hello.py
```

Expect `output shape: (1, 1000)`.

If pip cannot find an `executorch` wheel for 3.13, install **Python 3.12** from
python.org (tick "Add python.exe to PATH"), then repeat with `py -3.12`.

Either way, tell me which Python worked and I will pin it in
`documentation/executorch_setup.md`.

## 4. WSL2 — recommended, not yet required

Needed later for the Android NDK cross-compile, which is painful on native
Windows. Needs admin and a reboot, so do it when convenient:

```
wsl --install
```

Not needed for training or for anything in the next few days.

## A note on training speed

No CUDA GPU, so training is CPU-only on 8 threads. Use a smaller image size and
a modest batch:

```
env-vision\Scripts\python disease_detection\training\train.py ^
  --manifest datasets\metadata\splits.csv ^
  --out disease_detection\training\runs\run1 ^
  --epochs 12 --img-size 176 --batch 16 --workers 4
```

Expect this to take a few hours. Start it before you go to sleep rather than
waiting on it.

---

## 5. Get the dataset onto D: (needs Git from step 1)

A full clone of PlantVillage is about 2 GB. A **sparse** clone of just the four
tomato classes is **116 MB** — this is the exact command I used, verified:

```
D:
mkdir D:\agrishield_data
cd D:\agrishield_data
git init
git remote add origin https://github.com/spMohanty/PlantVillage-Dataset.git
git sparse-checkout init --cone
git sparse-checkout set raw/color/Tomato___Early_blight raw/color/Tomato___Late_blight raw/color/Tomato___healthy raw/color/Tomato___Septoria_leaf_spot
git fetch --depth 1 --filter=blob:none origin master
git checkout FETCH_HEAD
```

Expected: 6,271 images — 1,000 Early blight, 1,909 Late blight, 1,771 Septoria,
1,591 healthy.

Then build the splits:

```
cd %USERPROFILE%\Documents\AGRI_SHIELD_AI
env-vision\Scripts\python disease_detection\training\prepare_splits.py ^
  --root D:\agrishield_data\raw\color ^
  --out datasets\metadata ^
  --hamming 5
```

Expected: ~6,235 groups, 0 group-straddle violations.

## 6. Train for real

```
env-vision\Scripts\python disease_detection\training\train.py ^
  --manifest datasets\metadata\splits.csv ^
  --out D:\agrishield_data\runs\run1 ^
  --epochs 12 --img-size 176 --batch 16 --workers 4
```

Checkpoints go to D: to keep C: free. On an i3-1215U with no GPU this runs for
a few hours — start it before bed.

**Check `metrics.json` afterwards.** If `"pretrained_backbone": false`, the
ImageNet download failed and the numbers are a pipeline test, not a result.
On your laptop the download should work, so expect `true`.
