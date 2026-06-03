@echo off
chcp 65001 >nul
setlocal
title SCMDERP - Cleanup Docker State

set "PROJECT_ROOT=%SCMDERP_ROOT%"
if "%PROJECT_ROOT%"=="" set "PROJECT_ROOT=D:\SCMDERP"
set "COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"

echo.
echo =============================================================
echo   SCMDERP - CLEANUP DOCKER STATE
echo =============================================================
echo   Project root: %PROJECT_ROOT%
echo   Compose file: %COMPOSE_FILE%
echo.
echo   Canh bao: lenh nay se dung stack va xoa volumes Docker cua SCMDERP.
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
echo   [OK] Da don sach stack Docker cua SCMDERP.
echo   Tiep theo co the chay Reset-Desktop.bat hoac Deploy-Desktop.bat.
pause
endlocal
