@echo off
REM ============================================================
REM AGRI-SHIELD AI - install Termux from the OFFICIAL F-Droid repo
REM and push it to the phone with adb. No third-party APK sources.
REM ============================================================
cd /d "%~dp0"
set ADB=%~dp0phase2\platform-tools\adb.exe
set OUT=phase2\termux_install_raw.txt
set APK=%TEMP%\termux-fdroid.apk

echo AGRI-SHIELD AI - TERMUX INSTALL > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

if not exist "%ADB%" (
  echo adb.exe NOT FOUND >> %OUT%
  echo adb.exe not found - run setup_adb2.bat first
  pause
  goto :eof
)

echo ===== STEP 1: is the phone online ===== >> %OUT%
"%ADB%" devices >> %OUT% 2>&1
"%ADB%" get-state > "%TEMP%\agstate.txt" 2>&1
type "%TEMP%\agstate.txt" | find "device" >nul 2>&1
if errorlevel 1 (
  echo PHONE NOT ONLINE >> %OUT%
  echo Phone not detected. Check the cable and USB debugging.
  pause
  goto :eof
)
echo Phone online. >> %OUT%
echo. >> %OUT%

echo ===== STEP 2: is Termux already installed ===== >> %OUT%
"%ADB%" shell pm list packages com.termux > "%TEMP%\agpkg.txt" 2>&1
type "%TEMP%\agpkg.txt" >> %OUT%
type "%TEMP%\agpkg.txt" | find "com.termux" >nul 2>&1
if not errorlevel 1 (
  echo Termux already installed - skipping download. >> %OUT%
  echo Termux is already installed.
  goto :launch
)
echo Not installed. >> %OUT%
echo. >> %OUT%

echo ===== STEP 3: ask F-Droid for the current version ===== >> %OUT%
echo Querying the official F-Droid index...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13; try { $j = Invoke-RestMethod -Uri 'https://f-droid.org/api/v1/packages/com.termux' -TimeoutSec 120; $c = $j.suggestedVersionCode; Write-Output ('VERSIONCODE=' + $c); Set-Content -Path $env:TEMP'\agvc.txt' -Value $c -NoNewline } catch { Write-Output ('FAILED: ' + $_.Exception.Message) }" >> %OUT% 2>&1

if not exist "%TEMP%\agvc.txt" (
  echo COULD NOT REACH F-DROID API >> %OUT%
  echo Install Termux manually on the phone from: >> %OUT%
  echo   https://f-droid.org/packages/com.termux/ >> %OUT%
  echo.
  echo Could not reach F-Droid. Install Termux manually from
  echo   https://f-droid.org/packages/com.termux/
  pause
  goto :eof
)
set /p VC=<"%TEMP%\agvc.txt"
echo Version code: %VC% >> %OUT%
echo. >> %OUT%

echo ===== STEP 4: download the APK ===== >> %OUT%
echo Downloading Termux %VC% from f-droid.org ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13; try { Invoke-WebRequest -Uri ('https://f-droid.org/repo/com.termux_%VC%.apk') -OutFile '%APK%' -UseBasicParsing -TimeoutSec 600; Write-Output ('OK bytes=' + (Get-Item '%APK%').Length) } catch { Write-Output ('FAILED: ' + $_.Exception.Message) }" >> %OUT% 2>&1

if not exist "%APK%" (
  echo DOWNLOAD FAILED >> %OUT%
  echo Download failed - see %OUT%
  pause
  goto :eof
)
for %%A in ("%APK%") do echo Downloaded %%~zA bytes >> %OUT%
echo. >> %OUT%

echo ===== STEP 5: install on the phone ===== >> %OUT%
echo Installing on the phone...
"%ADB%" install -r "%APK%" >> %OUT% 2>&1
echo. >> %OUT%
"%ADB%" shell pm list packages com.termux >> %OUT% 2>&1
"%ADB%" shell pm list packages com.termux > "%TEMP%\agpkg2.txt" 2>&1
type "%TEMP%\agpkg2.txt" | find "com.termux" >nul 2>&1
if errorlevel 1 (
  echo INSTALL DID NOT REGISTER >> %OUT%
  echo Install failed - see %OUT%
  pause
  goto :eof
)
echo Termux installed. >> %OUT%
del "%APK%" >nul 2>&1

:launch
echo. >> %OUT%
echo ===== STEP 6: storage headroom ===== >> %OUT%
"%ADB%" shell "df -h /data" >> %OUT% 2>&1
echo. >> %OUT%

echo ===== STEP 7: launch Termux ===== >> %OUT%
"%ADB%" shell monkey -p com.termux -c android.intent.category.LAUNCHER 1 >> %OUT% 2>&1
echo. >> %OUT%
echo ===== COMPLETE ===== >> %OUT%
echo.
echo Termux is installed and launching on the phone.
echo Look at the phone screen now.
echo.
pause
