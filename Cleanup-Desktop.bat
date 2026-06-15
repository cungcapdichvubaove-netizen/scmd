@echo off
chcp 65001 >nul
setlocal
<<<<<<< HEAD
title SCMD Pro - Cleanup Docker State

set "PROJECT_ROOT=%SCMDPRO_ROOT%"
if "%PROJECT_ROOT%"=="" set "PROJECT_ROOT=%~dp0"
=======
title SCMDERP - Cleanup Docker State

set "PROJECT_ROOT=%SCMDERP_ROOT%"
if "%PROJECT_ROOT%"=="" set "PROJECT_ROOT=D:\SCMDERP"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
set "COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"

echo.
echo =============================================================
<<<<<<< HEAD
echo   SCMD Pro - Cleanup Docker state
=======
echo   SCMDERP - CLEANUP DOCKER STATE
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
echo =============================================================
echo   Project root: %PROJECT_ROOT%
echo   Compose file: %COMPOSE_FILE%
echo.
<<<<<<< HEAD
echo   Canh bao: lenh nay se dung stack va xoa volumes Docker cua SCMD Pro.
=======
echo   Canh bao: lenh nay se dung stack va xoa volumes Docker cua SCMDERP.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
echo.
pause

if not exist "%COMPOSE_FILE%" (
    echo   [ERR] Khong tim thay %COMPOSE_FILE%
    pause
    exit /b 1
)

docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERR] Docker Desktop chua san sang.
    pause
    exit /b 1
)

docker compose --project-directory "%PROJECT_ROOT%" -f "%COMPOSE_FILE%" config >nul
if %errorlevel% neq 0 (
    echo   [ERR] Compose config khong hop le.
    pause
    exit /b 1
)

docker compose --project-directory "%PROJECT_ROOT%" -f "%COMPOSE_FILE%" down -v --remove-orphans
if %errorlevel% neq 0 (
    echo   [ERR] Cleanup that bai.
    pause
    exit /b 1
)

echo.
<<<<<<< HEAD
echo   [OK] Da don sach stack Docker cua SCMD Pro.
=======
echo   [OK] Da don sach stack Docker cua SCMDERP.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
echo   Tiep theo co the chay Reset-Desktop.bat hoac Deploy-Desktop.bat.
pause
endlocal
