@echo off
REM ============================================================
REM AGRI-SHIELD AI - Phase 2: verify payload, probe phone, push
REM Run AFTER enabling USB debugging on the phone.
REM ============================================================
cd /d "%~dp0"
set ADB=%~dp0phase2\platform-tools\adb.exe
set PAY=%~dp0phase2\agrishield_phase2
set OUT=phase2\deploy_raw.txt
set EXPECT=f57f5ec391f44b8add7fee57cd47e439e0ad17aaec5ce5d3e8aeaf1601037f4b

echo AGRI-SHIELD AI - PHASE 2 DEPLOY > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

if not exist "%ADB%" (
  echo adb.exe NOT FOUND at %ADB% >> %OUT%
  echo adb.exe not found - run setup_adb2.bat first
  pause
  goto :eof
)

echo ===== STEP 1: complete the payload ===== >> %OUT%
if not exist "%PAY%\agrishield_tomato4.pte" (
  echo Copying the trained model into the payload... >> %OUT%
  copy /Y "models\agrishield_tomato4.pte" "%PAY%\agrishield_tomato4.pte" >> %OUT% 2>&1
)
echo. >> %OUT%
echo Verifying model SHA256... >> %OUT%
certutil -hashfile "%PAY%\agrishield_tomato4.pte" SHA256 >> %OUT% 2>&1
echo Expected: %EXPECT% >> %OUT%
echo. >> %OUT%
echo Payload contents: >> %OUT%
dir /b /s "%PAY%" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 2: is the phone visible to adb ===== >> %OUT%
echo Looking for the phone...
"%ADB%" devices -l >> %OUT% 2>&1
"%ADB%" devices > "%TEMP%\agd2.txt" 2>&1
type "%TEMP%\agd2.txt" | find "unauthorized" >nul 2>&1
if not errorlevel 1 (
  echo. >> %OUT%
  echo STATE: UNAUTHORIZED >> %OUT%
  echo The phone is connected but has not trusted this computer. >> %OUT%
  echo Look at the phone screen and tap ALLOW on the USB debugging dialog. >> %OUT%
  echo.
  echo PHONE SHOWS "unauthorized" - tap ALLOW on the phone, then run this again.
  pause
  goto :eof
)
type "%TEMP%\agd2.txt" | find /c "	device" >nul 2>&1
if errorlevel 1 (
  echo. >> %OUT%
  echo STATE: NO DEVICE >> %OUT%
  echo USB debugging is probably still off, or the cable is charge-only. >> %OUT%
  echo.
  echo NO DEVICE FOUND - see %OUT%
  pause
  goto :eof
)
echo STATE: DEVICE ONLINE >> %OUT%
echo. >> %OUT%

echo ===== STEP 3: device identity ===== >> %OUT%
echo Phone detected. Collecting device information...
"%ADB%" shell "for p in ro.product.model ro.product.manufacturer ro.product.device ro.product.name ro.build.version.release ro.build.version.sdk ro.build.version.security_patch ro.product.cpu.abi ro.product.cpu.abilist ro.soc.manufacturer ro.soc.model ro.board.platform ro.hardware; do echo $p = $(getprop $p); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 4: /proc/cpuinfo - THE I8MM ANSWER ===== >> %OUT%
"%ADB%" shell "cat /proc/cpuinfo" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 5: per-core midr / frequency ===== >> %OUT%
"%ADB%" shell "for c in /sys/devices/system/cpu/cpu[0-9]*; do echo $(basename $c) midr=$(cat $c/regs/identification/midr_el1 2>/dev/null) maxfreq=$(cat $c/cpufreq/cpuinfo_max_freq 2>/dev/null) minfreq=$(cat $c/cpufreq/cpuinfo_min_freq 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 6: memory ===== >> %OUT%
"%ADB%" shell "head -6 /proc/meminfo" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 7: thermal zones ===== >> %OUT%
"%ADB%" shell "for z in /sys/class/thermal/thermal_zone*; do echo $(basename $z) $(cat $z/type 2>/dev/null) $(cat $z/temp 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 8: storage ===== >> %OUT%
"%ADB%" shell "df -h /data /sdcard" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 9: push the payload to the phone ===== >> %OUT%
echo Pushing the payload to the phone...
"%ADB%" shell "mkdir -p /sdcard/Download/agrishield_phase2" >> %OUT% 2>&1
"%ADB%" push "%PAY%\." /sdcard/Download/agrishield_phase2/ >> %OUT% 2>&1
echo. >> %OUT%
echo Listing what landed on the phone: >> %OUT%
"%ADB%" shell "ls -lR /sdcard/Download/agrishield_phase2" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 10: verify model hash ON THE PHONE ===== >> %OUT%
"%ADB%" shell "sha256sum /sdcard/Download/agrishield_phase2/agrishield_tomato4.pte 2>/dev/null || toybox sha256sum /sdcard/Download/agrishield_phase2/agrishield_tomato4.pte" >> %OUT% 2>&1
echo Expected: %EXPECT% >> %OUT%
echo. >> %OUT%

echo ===== COMPLETE ===== >> %OUT%
echo.
echo Done. Results in %OUT%
echo.
pause
