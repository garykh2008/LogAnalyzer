@echo off
setlocal EnableDelayedExpansion
title LogAnalyzer - Remote Capture Target Setup

echo ========================================================
echo   LogAnalyzer Remote Capture - Target Setup
echo ========================================================
echo   Prepares THIS machine to be captured remotely over SSH
echo   (OpenSSH Server + local-admin network elevation).
echo.
echo   Run this ON THE TARGET machine, as Administrator.
echo ========================================================
echo.

REM --- Require Administrator ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator.
    pause
    exit /b 1
)
echo [OK] Running as Administrator.

echo.
echo [Step 1] Setting network profile to Private (so firewall rules apply)...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object NetworkCategory -eq Public | Set-NetConnectionProfile -NetworkCategory Private" >nul 2>&1
echo    - Done.

echo.
echo [Step 2] Allowing local admin accounts full elevation over the network...
REM Needed so a scheduled task can run with "Highest" privileges for kernel capture.
reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f >nul
echo    - LocalAccountTokenFilterPolicy = 1

echo.
echo [Step 3] Installing / starting OpenSSH Server...
sc query sshd >nul 2>&1
if %errorLevel% neq 0 (
    echo    - OpenSSH Server not found. Installing...
    powershell -NoProfile -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0" >nul 2>&1
    if !errorlevel! equ 0 (
        echo    - [OK] OpenSSH Server installed.
    ) else (
        echo    - [ERROR] Install failed. Check Internet / Windows Update access.
    )
) else (
    echo    - OpenSSH Server already installed.
)

sc config sshd start= auto >nul
net start sshd >nul 2>&1
netsh advfirewall firewall add rule name="OpenSSH Server (sshd)" dir=in action=allow protocol=TCP localport=22 >nul 2>&1
echo    - sshd set to auto-start, firewall port 22 opened.

echo.
echo ========================================================
echo   Target setup complete.
echo ========================================================
echo.
echo   Next: in LogAnalyzer, use  File ^> Capture DbgView (Remote)...
echo   with this machine's IP, an ADMIN username/password, and the
echo   full path to Dbgview.exe on this machine.
echo.
echo   Notes:
echo    - The SSH account must be a local Administrator (needed to load
echo      the kernel capture driver via a Highest-privilege task).
echo    - DebugView (Dbgview.exe) must already exist on this machine.
echo    - Loading unsigned drivers is a separate concern (bcdedit
echo      /set testsigning on) and is NOT configured by this script.
echo.
pause
