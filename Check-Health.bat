@echo off
chcp 65001 >nul
<<<<<<< HEAD
title SCMD Pro - Health Check
=======
title SCMDERP - Health Check
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

:: Kiem tra PowerShell ton tai
where powershell.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERR] Khong tim thay PowerShell. Vui long cai dat PowerShell 5.1+
    echo  https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell
    echo.
    pause
    exit /b 1
)

:: Kiem tra file PS1 ton tai cung thu muc
if not exist "%~dp0Check-Health.ps1" (
    echo.
    echo  [ERR] Khong tim thay Check-Health.ps1 cung thu muc nay.
    echo  Dam bao ca hai file nam cung mot folder.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-Health.ps1" %*
if %errorlevel% neq 0 (
    echo.
echo  [ERR] Health check ket thuc voi loi. Xem thong bao o tren.
    pause
    exit /b 1
)
