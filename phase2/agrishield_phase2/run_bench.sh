#!/bin/sh
# AGRI-SHIELD AI — Phase 2 on-device benchmark
#
# Run this inside the Debian aarch64 rootfs on the Infinix NOTE 30 5G.
#   sh run_bench.sh
#
# Collects: real /proc/cpuinfo (settles the I8MM question), thermal zones
# before/after, peak RSS, and >=30 timed inferences of the trained model.
# Writes results next to this script. Needs no network.

set -u
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"

ITERS=${ITERS:-50}
WARMUP=${WARMUP:-10}
OUT="$HERE/android_inference_results.json"
SYS="$HERE/device_sysinfo.txt"

echo "AGRI-SHIELD AI — Phase 2 on-device benchmark"
echo "working dir: $HERE"
echo

# ---------------------------------------------------------------- sanity
missing=0
for f in agrishield_bench agrishield_tomato4.pte validation_inputs.bin \
         lib/libexecutorch.so lib/libexecutorch_backend_xnnpack.so \
         lib/libexecutorch_threadpool.so; do
  if [ ! -f "$f" ]; then echo "MISSING: $f"; missing=1; fi
done
[ "$missing" -eq 1 ] && { echo "payload incomplete — aborting"; exit 1; }
chmod +x agrishield_bench 2>/dev/null

# Verify the model is the authentic Phase 1 artifact before trusting any number.
EXPECT=f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b
if command -v sha256sum >/dev/null 2>&1; then
  GOT=$(sha256sum agrishield_tomato4.pte | cut -d' ' -f1)
  if [ "$GOT" = "$EXPECT" ]; then
    echo "model SHA256 OK  ($GOT)"
  else
    echo "!! MODEL HASH MISMATCH"
    echo "   expected $EXPECT"
    echo "   got      $GOT"
    echo "   Refusing to benchmark a model that is not the Phase 1 artifact."
    exit 1
  fi
else
  echo "WARNING: sha256sum unavailable — model authenticity NOT verified"
fi
echo

# ------------------------------------------------------- device sysinfo
{
  echo "=== collected $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC ==="
  echo
  echo "=== uname ==="; uname -a
  echo
  echo "=== /proc/cpuinfo ==="; cat /proc/cpuinfo 2>/dev/null
  echo
  echo "=== per-core max frequency ==="
  for c in /sys/devices/system/cpu/cpu[0-9]*; do
    [ -d "$c" ] || continue
    printf '%s maxfreq=%s midr=%s\n' "$(basename "$c")" \
      "$(cat "$c/cpufreq/cpuinfo_max_freq" 2>/dev/null || echo NA)" \
      "$(cat "$c/regs/identification/midr_el1" 2>/dev/null || echo NA)"
  done
  echo
  echo "=== /proc/meminfo (head) ==="; head -5 /proc/meminfo 2>/dev/null
  echo
  echo "=== thermal zones ==="
  for z in /sys/class/thermal/thermal_zone*; do
    [ -d "$z" ] || continue
    printf '%s type=%s temp=%s\n' "$(basename "$z")" \
      "$(cat "$z/type" 2>/dev/null || echo NA)" \
      "$(cat "$z/temp" 2>/dev/null || echo NA)"
  done
  echo
  echo "=== android properties (via /system/bin/getprop if reachable) ==="
  if [ -x /system/bin/getprop ]; then
    for p in ro.product.model ro.product.manufacturer ro.build.version.release \
             ro.build.version.sdk ro.product.cpu.abi ro.soc.manufacturer \
             ro.soc.model ro.board.platform; do
      printf '%s = %s\n' "$p" "$(/system/bin/getprop $p 2>/dev/null)"
    done
  else
    echo "getprop not reachable from inside this rootfs (expected under proot)"
  fi
} > "$SYS" 2>&1

echo "device sysinfo -> $SYS"
echo
echo "--- CPU feature line (this settles the I8MM question) ---"
grep -m1 -i "^Features" /proc/cpuinfo 2>/dev/null || echo "(no Features line found)"
echo

# ------------------------------------------------------------- benchmark
export LD_LIBRARY_PATH="$HERE/lib:${LD_LIBRARY_PATH:-}"
echo "running $ITERS timed iterations after $WARMUP warm-up..."
echo
./agrishield_bench agrishield_tomato4.pte validation_inputs.bin "$OUT" \
    --iters "$ITERS" --warmup "$WARMUP"
rc=$?
echo
if [ $rc -eq 0 ]; then
  echo "SUCCESS — results written to:"
  echo "  $OUT"
  echo "  $SYS"
  echo
  echo "Copy BOTH files back to the laptop."
else
  echo "FAILED with exit code $rc — nothing may be reported as a measurement."
fi
exit $rc
