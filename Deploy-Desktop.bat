@echo off
chcp 65001 >nul
<<<<<<< HEAD
title SCMD Pro - Deploy
=======
title SCMDERP - Deploy
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

where powershell.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [ERR] Khong tim thay PowerShell.
    pause
    exit /b 1
)

if not exist "%~dp0Deploy-Desktop.ps1" (
    echo.
    echo   [ERR] Khong tim thay Deploy-Desktop.ps1 cung thu muc.
    pause
    exit /b 1
)

echo.
echo =============================================================
<<<<<<< HEAD
echo   SCMD Pro - Deploy
=======
echo   SCMDERP - DEPLOY
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
echo =============================================================
echo.
echo   [1] Fast restart ^(bo qua build image, van migrate/check^)
echo   [2] Full rebuild ^(build image + restart + migrate/check^)
echo.
set /p MODE="Nhap 1 hoac 2: "

if "%MODE%"=="1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Deploy-Desktop.ps1" -SkipBuild
) else if "%MODE%"=="2" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Deploy-Desktop.ps1"
) else (
    echo   [ERR] Lua chon khong hop le.
    pause
    exit /b 1
)

if %errorlevel% neq 0 (
    echo.
    echo   [ERR] Deploy that bai. Xem thong bao o tren.
    pause
    exit /b 1
)
