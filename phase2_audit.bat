@echo off
REM ============================================================
REM AGRI-SHIELD AI - Phase 2 environment audit
REM Place in the AGRI_SHIELD_AI project root and double-click.
REM Writes phase2\phase2_audit_raw.txt . Reads only; changes nothing.
REM ============================================================
cd /d "%~dp0"
if not exist phase2 mkdir phase2
set OUT=phase2\phase2_audit_raw.txt

echo AGRI-SHIELD AI - PHASE 2 ENVIRONMENT AUDIT > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo Project root: %CD% >> %OUT%
echo. >> %OUT%

echo ===================================================== >> %OUT%
echo SECTION 1 - LAPTOP TOOLCHAIN >> %OUT%
echo ===================================================== >> %OUT%

echo [git] >> %OUT%
where git >> %OUT% 2>&1
git --version >> %OUT% 2>&1
echo. >> %OUT%

echo [adb] >> %OUT%
where adb >> %OUT% 2>&1
adb version >> %OUT% 2>&1
echo. >> %OUT%

echo [python] >> %OUT%
where python >> %OUT% 2>&1
python --version >> %OUT% 2>&1
py -0p >> %OUT% 2>&1
echo. >> %OUT%

echo [java/jdk] >> %OUT%
where java >> %OUT% 2>&1
java -version >> %OUT% 2>&1
echo JAVA_HOME=%JAVA_HOME% >> %OUT%
echo. >> %OUT%

echo [android sdk/ndk] >> %OUT%
echo ANDROID_HOME=%ANDROID_HOME% >> %OUT%
echo ANDROID_SDK_ROOT=%ANDROID_SDK_ROOT% >> %OUT%
echo ANDROID_NDK_HOME=%ANDROID_NDK_HOME% >> %OUT%
if exist "%LOCALAPPDATA%\Android\Sdk" (
  echo SDK dir present, contents: >> %OUT%
  dir /b "%LOCALAPPDATA%\Android\Sdk" >> %OUT% 2>&1
) else (
  echo no SDK at %LOCALAPPDATA%\Android\Sdk >> %OUT%
)
echo. >> %OUT%

echo [cmake] >> %OUT%
where cmake >> %OUT% 2>&1
cmake --version >> %OUT% 2>&1
echo. >> %OUT%

echo ===================================================== >> %OUT%
echo SECTION 2 - PROJECT PYTHON ENVIRONMENTS >> %OUT%
echo ===================================================== >> %OUT%
if exist "env-executorch\Scripts\python.exe" (
  echo env-executorch present >> %OUT%
  env-executorch\Scripts\python.exe -c "import sys;print('python',sys.version)" >> %OUT% 2>&1
  env-executorch\Scripts\python.exe -c "from importlib.metadata import version;print('executorch',version('executorch'))" >> %OUT% 2>&1
  env-executorch\Scripts\python.exe -c "import torch;print('torch',torch.__version__)" >> %OUT% 2>&1
) else (
  echo env-executorch NOT PRESENT >> %OUT%
)
echo. >> %OUT%
if exist "env-vision\Scripts\python.exe" (
  echo env-vision present >> %OUT%
  env-vision\Scripts\python.exe -c "import torch,torchvision;print('torch',torch.__version__,'tv',torchvision.__version__)" >> %OUT% 2>&1
) else (
  echo env-vision NOT PRESENT >> %OUT%
)
echo. >> %OUT%

echo ===================================================== >> %OUT%
echo SECTION 3 - TRAINED MODEL ARTIFACTS >> %OUT%
echo ===================================================== >> %OUT%
if exist "models" (dir /b models >> %OUT% 2>&1) else (echo no models dir >> %OUT%)
echo. >> %OUT%
if exist "models\agrishield_tomato4.pte" (
  dir "models\agrishield_tomato4.pte" >> %OUT% 2>&1
  certutil -hashfile "models\agrishield_tomato4.pte" SHA256 >> %OUT% 2>&1
) else (
  echo TRAINED .pte NOT FOUND at models\agrishield_tomato4.pte >> %OUT%
)
echo. >> %OUT%

echo ===================================================== >> %OUT%
echo SECTION 4 - PHONE VIA ADB >> %OUT%
echo ===================================================== >> %OUT%
where adb >nul 2>&1
if errorlevel 1 (
  echo ADB NOT ON PATH - no phone inspection performed >> %OUT%
  echo Sections 4 contains NO measured phone data. >> %OUT%
  goto :finish
)

echo [adb devices] >> %OUT%
adb devices -l >> %OUT% 2>&1
echo. >> %OUT%

echo [device properties] >> %OUT%
adb shell "for p in ro.product.model ro.product.manufacturer ro.product.device ro.build.version.release ro.build.version.sdk ro.product.cpu.abi ro.product.cpu.abilist ro.soc.manufacturer ro.soc.model ro.board.platform ro.hardware; do echo $p = $(getprop $p); done" >> %OUT% 2>&1
echo. >> %OUT%

echo [cpu - features line decides the kernel path] >> %OUT%
adb shell "grep -m1 Features /proc/cpuinfo; echo cores = $(grep -c ^processor /proc/cpuinfo); grep -m1 'CPU architecture' /proc/cpuinfo" >> %OUT% 2>&1
echo. >> %OUT%

echo [per-core midr / max freq] >> %OUT%
adb shell "for c in /sys/devices/system/cpu/cpu[0-9]*; do echo $c midr=$(cat $c/regs/identification/midr_el1 2>/dev/null) maxfreq=$(cat $c/cpufreq/cpuinfo_max_freq 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo [memory] >> %OUT%
adb shell "head -3 /proc/meminfo" >> %OUT% 2>&1
echo. >> %OUT%

echo [thermal zones] >> %OUT%
adb shell "for z in /sys/class/thermal/thermal_zone*; do echo $z $(cat $z/type 2>/dev/null) $(cat $z/temp 2>/dev/null); done" >> %OUT% 2>&1
echo. >> %OUT%

echo [storage] >> %OUT%
adb shell "df -h /data /data/local/tmp" >> %OUT% 2>&1
echo. >> %OUT%

echo [can we write and execute under /data/local/tmp] >> %OUT%
adb shell "mkdir -p /data/local/tmp/agrishield && echo write_ok > /data/local/tmp/agrishield/probe.txt && cat /data/local/tmp/agrishield/probe.txt && printf '#!/system/bin/sh\necho exec_ok\n' > /data/local/tmp/agrishield/probe.sh && chmod 755 /data/local/tmp/agrishield/probe.sh && /data/local/tmp/agrishield/probe.sh" >> %OUT% 2>&1
echo. >> %OUT%

:finish
echo ===================================================== >> %OUT%
echo AUDIT COMPLETE >> %OUT%
echo ===================================================== >> %OUT%
echo.
echo Audit complete. Output written to %OUT%
echo.
pause
