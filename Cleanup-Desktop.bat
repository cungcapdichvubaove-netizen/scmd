@echo off
chcp 65001 >nul
setlocal
title SCMD Pro - Cleanup Docker State

set "PROJECT_ROOT=%SCMDPRO_ROOT%"
if "%PROJECT_ROOT%"=="" set "PROJECT_ROOT=%~dp0"
set "COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"

echo.
echo =============================================================
echo   SCMD Pro - Cleanup Docker state
echo =============================================================
echo   Project root: %PROJECT_ROOT%
echo   Compose file: %COMPOSE_FILE%
echo.
echo   Canh bao: lenh nay se dung stack va xoa volumes Docker cua SCMD Pro.
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
echo   [OK] Da don sach stack Docker cua SCMD Pro.
echo   Tiep theo co the chay Reset-Desktop.bat hoac Deploy-Desktop.bat.
pause
endlocal
