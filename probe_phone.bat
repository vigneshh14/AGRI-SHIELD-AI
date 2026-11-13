@echo off
REM AGRI-SHIELD AI - Android device profile via adb
REM Run AFTER adb is on PATH and USB debugging is enabled and authorised.
cd /d "%~dp0"
set OUT=phone_profile.txt
echo AGRI-SHIELD AI Android device profile > %OUT%
echo Generated %DATE% %TIME% >> %OUT%
echo. >> %OUT%
echo ===== ADB ===== >> %OUT%
adb version >> %OUT% 2>&1
adb devices -l >> %OUT% 2>&1
echo. >> %OUT%
echo ===== IDENTITY ===== >> %OUT%
for %%P in (ro.product.manufacturer ro.product.model ro.product.name ro.soc.manufacturer ro.soc.model ro.board.platform ro.build.version.release ro.build.version.sdk ro.product.cpu.abi ro.product.cpu.abilist) do (
  echo|set /p="%%P = " >> %OUT%
  adb shell getprop %%P >> %OUT% 2>&1
)
echo. >> %OUT%
echo ===== CPU ===== >> %OUT%
adb shell cat /proc/cpuinfo >> %OUT% 2>&1
echo. >> %OUT%
echo ===== CPU FEATURE FLAGS (the line that matters) ===== >> %OUT%
adb shell "grep -m1 Features /proc/cpuinfo" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== MIDR (Arm CPU identification register) ===== >> %OUT%
adb shell "cat /sys/devices/system/cpu/cpu0/regs/identification/midr_el1 2>/dev/null || echo midr_not_readable" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== CORE TOPOLOGY ===== >> %OUT%
adb shell "cat /sys/devices/system/cpu/possible" >> %OUT% 2>&1
adb shell "for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/cpuinfo_max_freq; do echo $c $(cat $c); done" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== MEMORY ===== >> %OUT%
adb shell "head -3 /proc/meminfo" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== STORAGE ===== >> %OUT%
adb shell "df -h /data /data/local/tmp" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== WRITE TEST (can we push and execute?) ===== >> %OUT%
adb shell "mkdir -p /data/local/tmp/agrishield && echo ok > /data/local/tmp/agrishield/probe.txt && cat /data/local/tmp/agrishield/probe.txt" >> %OUT% 2>&1
echo. >> %OUT%
echo PROFILE COMPLETE >> %OUT%
echo Done. Output written to %OUT%
pause
