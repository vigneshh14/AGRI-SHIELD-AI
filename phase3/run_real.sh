#!/bin/sh
# AGRI-SHIELD AI — Phase 3: real tomato leaf photographs on the phone's Arm CPU.
#
# Run inside the Debian aarch64 rootfs, same place Phase 2 ran:
#   proot-distro login debian
#   cd /root/agrishield_phase2 && sh run_real.sh
#
# Expects real_image_inputs.bin (produced by preprocess_images.py) beside it.
# Writes real_image_results.json. Needs no network.

set -u
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"

IN=${IN:-real_image_inputs.bin}
OUT="$HERE/real_image_results.json"
ITERS=${ITERS:-30}
WARMUP=${WARMUP:-10}

echo "AGRI-SHIELD AI — Phase 3 real-image inference"
echo

missing=0
for f in agrishield_bench agrishield_tomato4.pte "$IN" \
         lib/libexecutorch.so lib/libexecutorch_backend_xnnpack.so \
         lib/libexecutorch_threadpool.so; do
  [ -f "$f" ] || { echo "MISSING: $f"; missing=1; }
done
if [ "$missing" -eq 1 ]; then
  echo
  echo "If real_image_inputs.bin is missing, the photographs have not been"
  echo "preprocessed and copied across yet. Nothing to run."
  exit 1
fi
chmod +x agrishield_bench 2>/dev/null

# The model must be the authentic Phase 1 artifact, or no number here means
# anything. Same check as Phase 2.
EXPECT=f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b
if command -v sha256sum >/dev/null 2>&1; then
  GOT=$(sha256sum agrishield_tomato4.pte | cut -d' ' -f1)
  if [ "$GOT" = "$EXPECT" ]; then
    echo "model SHA256 OK  ($GOT)"
  else
    echo "!! MODEL HASH MISMATCH — refusing to run"
    echo "   expected $EXPECT"
    echo "   got      $GOT"
    exit 1
  fi
else
  echo "WARNING: sha256sum unavailable — model authenticity NOT verified"
fi

echo "input: $IN"
echo
grep -m1 -i "^Features" /proc/cpuinfo 2>/dev/null || echo "(no Features line)"
echo

export LD_LIBRARY_PATH="$HERE/lib:${LD_LIBRARY_PATH:-}"
./agrishield_bench agrishield_tomato4.pte "$IN" "$OUT" \
    --iters "$ITERS" --warmup "$WARMUP"
rc=$?
echo
if [ $rc -eq 0 ]; then
  echo "SUCCESS — $OUT"
  echo
  echo "Copy it back:"
  echo "  cp real_image_results.json /sdcard/Download/agrishield_phase2/"
else
  echo "FAILED with exit code $rc — no result may be reported as a measurement."
fi
exit $rc
