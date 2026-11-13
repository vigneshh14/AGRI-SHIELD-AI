@echo off
REM ============================================================
REM AGRI-SHIELD AI - pull on-device results back from the phone
REM ============================================================
cd /d "%~dp0"
set ADB=%~dp0phase2\platform-tools\adb.exe
set DEST=%~dp0benchmarks
set OUT=phase2\pull_raw.txt
set SRC=/sdcard/Download/agrishield_phase2

if not exist "%DEST%" mkdir "%DEST%"

echo AGRI-SHIELD AI - PULL RESULTS > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

"%ADB%" devices >> %OUT% 2>&1
echo. >> %OUT%

echo ===== RADIO STATE AT PULL TIME ===== >> %OUT%
echo airplane_mode_on: >> %OUT%
"%ADB%" shell "settings get global airplane_mode_on" >> %OUT% 2>&1
echo wifi_on: >> %OUT%
"%ADB%" shell "settings get global wifi_on" >> %OUT% 2>&1
echo mobile_data: >> %OUT%
"%ADB%" shell "settings get global mobile_data" >> %OUT% 2>&1
echo connectivity summary: >> %OUT%
"%ADB%" shell "dumpsys connectivity | grep -m4 -E 'Active default network|NetworkAgentInfo|No active'" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== WHAT IS ON THE PHONE ===== >> %OUT%
"%ADB%" shell "ls -l %SRC%" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== PULLING ===== >> %OUT%
echo Pulling result files...
"%ADB%" pull %SRC%/android_inference_results.json "%DEST%\android_inference_results.json" >> %OUT% 2>&1
"%ADB%" pull %SRC%/device_sysinfo.txt "%DEST%\device_sysinfo_onphone.txt" >> %OUT% 2>&1
"%ADB%" pull %SRC%/offline_results.json "%DEST%\offline_results.json" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== BATTERY / THERMAL AT PULL TIME ===== >> %OUT%
"%ADB%" shell "dumpsys battery | grep -E 'level|temperature'" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== WHAT LANDED LOCALLY ===== >> %OUT%
dir "%DEST%" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== COMPLETE ===== >> %OUT%
echo.
echo Done. Results in %OUT% and benchmarks\
echo.
pause
