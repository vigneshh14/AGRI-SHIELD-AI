@echo off
REM ============================================================
REM AGRI-SHIELD AI - platform-tools download, attempt 2
REM Windows curl failed TLS (schannel SEC_E_DECRYPT_FAILURE).
REM PowerShell uses the .NET TLS stack instead, and BITS a third.
REM ============================================================
cd /d "%~dp0"
if not exist phase2 mkdir phase2
set OUT=phase2\adb_setup2_raw.txt
set URL=https://dl.google.com/android/repository/platform-tools-latest-windows.zip
set ZIP=%TEMP%\agrishield-pt.zip
set ADB=%~dp0phase2\platform-tools\adb.exe

echo AGRI-SHIELD AI - platform-tools download attempt 2 > %OUT%
echo Generated: %DATE% %TIME% >> %OUT%
echo. >> %OUT%

if exist "%ADB%" goto :extracted

echo [A] PowerShell Invoke-WebRequest, TLS 1.2 forced >> %OUT%
echo Trying PowerShell download...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13; try { Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' -UseBasicParsing -TimeoutSec 180; Write-Output ('OK bytes=' + (Get-Item '%ZIP%').Length) } catch { Write-Output ('FAILED: ' + $_.Exception.Message) }" >> %OUT% 2>&1

if exist "%ZIP%" goto :extract

echo. >> %OUT%
echo [B] BITS transfer >> %OUT%
echo Trying BITS...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Start-BitsTransfer -Source '%URL%' -Destination '%ZIP%' -ErrorAction Stop; Write-Output ('OK bytes=' + (Get-Item '%ZIP%').Length) } catch { Write-Output ('FAILED: ' + $_.Exception.Message) }" >> %OUT% 2>&1

if exist "%ZIP%" goto :extract

echo. >> %OUT%
echo [C] curl with explicit TLS 1.2 >> %OUT%
echo Trying curl with forced TLS 1.2...
curl -L --fail --tlsv1.2 --tls-max 1.2 --silent --show-error -o "%ZIP%" "%URL%" >> %OUT% 2>&1

if exist "%ZIP%" goto :extract

echo. >> %OUT%
echo ALL THREE DOWNLOAD METHODS FAILED >> %OUT%
echo This is a TLS/network problem on this machine, not a missing file. >> %OUT%
echo Download manually from: >> %OUT%
echo   %URL% >> %OUT%
echo and extract so that this path exists: >> %OUT%
echo   %~dp0phase2\platform-tools\adb.exe >> %OUT%
echo.
echo ALL DOWNLOAD METHODS FAILED - see %OUT%
echo.
pause
goto :eof

:extract
for %%A in ("%ZIP%") do echo Downloaded %%~zA bytes >> %OUT%
echo. >> %OUT%
echo Extracting... >> %OUT%
tar -xf "%ZIP%" -C phase2 >> %OUT% 2>&1
if not exist "%ADB%" powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath 'phase2' -Force" >> %OUT% 2>&1

:extracted
if exist "%ADB%" (
  echo adb.exe present: %ADB% >> %OUT%
  del "%ZIP%" >nul 2>&1
) else (
  echo EXTRACTION FAILED >> %OUT%
  dir /b phase2 >> %OUT% 2>&1
  echo.
  echo EXTRACTION FAILED - see %OUT%
  pause
  goto :eof
)

echo. >> %OUT%
echo Download OK. Handing over to the device probe... >> %OUT%
echo.
echo platform-tools installed. Now probing the phone...
echo.
call "%~dp0setup_adb.bat"
