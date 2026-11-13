@echo off
REM AGRI-SHIELD AI - Windows environment audit
REM Writes everything to environment_audit_raw.txt next to this file.
cd /d "%~dp0"
set OUT=environment_audit_raw.txt
echo AGRI-SHIELD AI Windows audit > %OUT%
echo Generated %DATE% %TIME% >> %OUT%
echo. >> %OUT%
echo ===== ARCHITECTURE ===== >> %OUT%
echo PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE% >> %OUT%
echo NUMBER_OF_PROCESSORS=%NUMBER_OF_PROCESSORS% >> %OUT%
echo. >> %OUT%
echo ===== CPU / RAM / GPU / DISK ===== >> %OUT%
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | Format-List" >> %OUT% 2>&1
powershell -NoProfile -Command "$t=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory; Write-Output (\"TotalRAM_GB = \" + [math]::Round($t/1GB,2))" >> %OUT% 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | Format-List" >> %OUT% 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | Select-Object DeviceID,@{n=\"FreeGB\";e={[math]::Round($_.FreeSpace/1GB,1)}},@{n=\"SizeGB\";e={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize" >> %OUT% 2>&1
powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).Caption + \" build \" + (Get-CimInstance Win32_OperatingSystem).BuildNumber" >> %OUT% 2>&1
echo. >> %OUT%
echo ===== TOOLCHAIN ===== >> %OUT%
echo --- python --- >> %OUT%
where python >> %OUT% 2>&1
python --version >> %OUT% 2>&1
py -0p >> %OUT% 2>&1
echo --- git --- >> %OUT%
where git >> %OUT% 2>&1
git --version >> %OUT% 2>&1
echo --- adb --- >> %OUT%
where adb >> %OUT% 2>&1
adb version >> %OUT% 2>&1
echo --- android sdk --- >> %OUT%
if defined ANDROID_HOME echo ANDROID_HOME=%ANDROID_HOME% >> %OUT%
if exist "%LOCALAPPDATA%\Android\Sdk" dir /b "%LOCALAPPDATA%\Android\Sdk" >> %OUT% 2>&1
if exist "%USERPROFILE%\.android" dir /b "%USERPROFILE%\.android" >> %OUT% 2>&1
echo --- wsl --- >> %OUT%
wsl --status >> %OUT% 2>&1
wsl --list --verbose >> %OUT% 2>&1
echo. >> %OUT%
echo ===== ATTACHED ANDROID DEVICES ===== >> %OUT%
adb devices -l >> %OUT% 2>&1
echo. >> %OUT%
echo AUDIT COMPLETE >> %OUT%
echo Done. Output written to %OUT%
pause
