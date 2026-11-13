@echo off
REM ============================================================
REM AGRI-SHIELD AI - Phase 2: obtain Android platform-tools (ADB)
REM No administrator rights. Does NOT modify PATH. Downloads the
REM official Google zip, extracts it inside the project, then probes
REM the connected phone.
REM ============================================================
cd /d "%~dp0"
if not exist phase2 mkdir phase2
set OUT=phase2\adb_setup_raw.txt
set PT=%~dp0phase2\platform-tools
set ADB=%PT%\adb.exe

echo AGRI-SHIELD AI - ADB SETUP AND LIVE DEVICE PROBE > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

echo ===== STEP 1: look for an existing adb ===== >> %OUT%
where adb >> %OUT% 2>&1
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
  echo FOUND in Android SDK >> %OUT%
  set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
)
if exist "%ADB%" (
  echo Using existing: %ADB% >> %OUT%
  goto :probe
)
echo No existing adb found. >> %OUT%
echo. >> %OUT%

echo ===== STEP 2: download official platform-tools ===== >> %OUT%
echo Downloading platform-tools-latest-windows.zip ^(about 15 MB^)...
curl -L --fail --silent --show-error -o "%TEMP%\agrishield-pt.zip" ^
  https://dl.google.com/android/repository/platform-tools-latest-windows.zip >> %OUT% 2>&1
if errorlevel 1 (
  echo DOWNLOAD FAILED - check internet connection or corporate proxy >> %OUT%
  echo DOWNLOAD FAILED. See %OUT%
  goto :finish
)
for %%A in ("%TEMP%\agrishield-pt.zip") do echo Downloaded %%~zA bytes >> %OUT%

echo ===== STEP 3: extract ===== >> %OUT%
tar -xf "%TEMP%\agrishield-pt.zip" -C phase2 >> %OUT% 2>&1
if errorlevel 1 (
  echo TAR EXTRACT FAILED - trying PowerShell Expand-Archive >> %OUT%
  powershell -NoProfile -Command "Expand-Archive -LiteralPath '%TEMP%\agrishield-pt.zip' -DestinationPath 'phase2' -Force" >> %OUT% 2>&1
)
if exist "%ADB%" (
  echo Extracted OK: %ADB% >> %OUT%
  del "%TEMP%\agrishield-pt.zip" >nul 2>&1
) else (
  echo EXTRACTION DID NOT PRODUCE adb.exe >> %OUT%
  dir /b phase2 >> %OUT% 2>&1
  goto :finish
)
echo. >> %OUT%

:probe
echo ===== STEP 4: adb version ===== >> %OUT%
"%ADB%" version >> %OUT% 2>&1
echo. >> %OUT%

echo Starting adb server and looking for the phone...
echo ===== STEP 5: devices ===== >> %OUT%
"%ADB%" start-server >> %OUT% 2>&1
"%ADB%" devices -l >> %OUT% 2>&1
echo. >> %OUT%

REM Detect state: unauthorized / offline / no device
"%ADB%" devices > "%TEMP%\agd.txt" 2>&1
find /c "unauthorized" "%TEMP%\agd.txt" >nul 2>&1 && echo STATE: UNAUTHORIZED - approve the RSA dialog on the phone >> %OUT%
find /c "device" "%TEMP%\agd.txt" >nul 2>&1 || echo STATE: NO DEVICE LISTED >> %OUT%

echo ===== STEP 6: device properties ===== >> %OUT%
"%ADB%" shell "for p in ro.product.model ro.product.manufacturer ro.product.device ro.build.version.release ro.build.version.sdk ro.product.cpu.abi ro.product.cpu.abilist ro.soc.manufacturer ro.soc.model ro.board.platform ro.hardware; do echo $p = $(getprop $p); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 7: CPU - the Features line settles I8MM ===== >> %OUT%
"%ADB%" shell "cat /proc/cpuinfo" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 8: per-core midr and max frequency ===== >> %OUT%
"%ADB%" shell "for c in /sys/devices/system/cpu/cpu[0-9]*; do echo $(basename $c) midr=$(cat $c/regs/identification/midr_el1 2>/dev/null) maxfreq=$(cat $c/cpufreq/cpuinfo_max_freq 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 9: memory ===== >> %OUT%
"%ADB%" shell "head -5 /proc/meminfo" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 10: thermal zones ===== >> %OUT%
"%ADB%" shell "for z in /sys/class/thermal/thermal_zone*; do echo $(basename $z) $(cat $z/type 2>/dev/null) $(cat $z/temp 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 11: storage and exec test ===== >> %OUT%
"%ADB%" shell "df -h /data /data/local/tmp" >> %OUT% 2>&1
"%ADB%" shell "mkdir -p /data/local/tmp/agrishield && echo write_ok > /data/local/tmp/agrishield/p.txt && cat /data/local/tmp/agrishield/p.txt && printf '#!/system/bin/sh\necho exec_ok\n' > /data/local/tmp/agrishield/p.sh && chmod 755 /data/local/tmp/agrishield/p.sh && /data/local/tmp/agrishield/p.sh" >> %OUT% 2>&1
echo. >> %OUT%

:finish
echo ===== COMPLETE ===== >> %OUT%
echo.
echo Done. Results in %OUT%
echo.
pause
