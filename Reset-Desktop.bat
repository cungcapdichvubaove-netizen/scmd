@echo off
chcp 65001 >nul
<<<<<<< HEAD
title SCMD Pro - Factory Reset
=======
title SCMDERP - Factory Reset
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

where powershell.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [ERR] Khong tim thay PowerShell.
    pause
    exit /b 1
)

if not exist "%~dp0Reset-Desktop.ps1" (
    echo.
    echo   [ERR] Khong tim thay Reset-Desktop.ps1 cung thu muc.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Reset-Desktop.ps1" %*
if %errorlevel% neq 0 (
    echo.
    echo   [ERR] Reset that bai. Xem thong bao o tren.
    pause
    exit /b 1
)
