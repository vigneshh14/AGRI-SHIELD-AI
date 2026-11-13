@echo off
REM ============================================================
REM AGRI-SHIELD AI - verify Termux install and pre-grant storage
REM Uses --user 0 because this phone has a secondary user profile.
REM ============================================================
cd /d "%~dp0"
set ADB=%~dp0phase2\platform-tools\adb.exe
set OUT=phase2\termux_verify_raw.txt

echo AGRI-SHIELD AI - TERMUX VERIFY > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

"%ADB%" devices >> %OUT% 2>&1
echo. >> %OUT%

echo ===== IS TERMUX ACTUALLY INSTALLED ===== >> %OUT%
echo Checking...
"%ADB%" shell "pm list packages --user 0 com.termux" > "%TEMP%\agt.txt" 2>&1
type "%TEMP%\agt.txt" >> %OUT%
type "%TEMP%\agt.txt" | find "com.termux" >nul 2>&1
if errorlevel 1 (
  echo. >> %OUT%
  echo RESULT: TERMUX NOT FOUND for user 0 >> %OUT%
  echo Trying all users... >> %OUT%
  "%ADB%" shell "pm list packages --user 10 com.termux" >> %OUT% 2>&1
  "%ADB%" shell "cmd package list packages com.termux" >> %OUT% 2>&1
  echo.
  echo TERMUX NOT DETECTED - see %OUT%
  pause
  goto :eof
)
echo. >> %OUT%
echo RESULT: TERMUX IS INSTALLED >> %OUT%
echo. >> %OUT%

echo ===== VERSION ===== >> %OUT%
"%ADB%" shell "dumpsys package com.termux | grep -E 'versionName|versionCode|firstInstallTime' | head -4" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== PRE-GRANT STORAGE ACCESS ===== >> %OUT%
echo Granting storage permission so Termux can read the payload...
"%ADB%" shell "pm grant --user 0 com.termux android.permission.READ_EXTERNAL_STORAGE" >> %OUT% 2>&1
"%ADB%" shell "pm grant --user 0 com.termux android.permission.WRITE_EXTERNAL_STORAGE" >> %OUT% 2>&1
"%ADB%" shell "appops set --user 0 com.termux MANAGE_EXTERNAL_STORAGE allow" >> %OUT% 2>&1
"%ADB%" shell "appops set --user 0 com.termux LEGACY_STORAGE allow" >> %OUT% 2>&1
echo Grants attempted. Current state: >> %OUT%
"%ADB%" shell "dumpsys package com.termux | grep -A2 -E 'READ_EXTERNAL|MANAGE_EXTERNAL' | head -10" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== PAYLOAD STILL ON THE PHONE ===== >> %OUT%
"%ADB%" shell "ls -l /sdcard/Download/agrishield_phase2" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STORAGE HEADROOM ===== >> %OUT%
"%ADB%" shell "df -h /data /sdcard" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== BATTERY AND THERMAL SANITY ===== >> %OUT%
"%ADB%" shell "dumpsys battery | grep -E 'level|temperature|status'" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== COMPLETE ===== >> %OUT%
echo.
echo Done. Results in %OUT%
echo.
pause
