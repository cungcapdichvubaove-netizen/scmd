@echo off
setlocal

REM ==========================================
REM Cau hinh 2 duong dan ben duoi cho de su dung
REM SOURCE_DIR: thu muc du lieu can backup
REM BACKUP_DIR: thu muc luu repository backup
REM ==========================================
set "SOURCE_DIR=D:\SCMD_Tech\1.SCMDPRO\scmd_pro"
set "BACKUP_DIR="D:\SCMD_Tech\1.SCMDPRO\BackupRepo"

REM Neu may co lenh py thi giu mac dinh.
REM Neu khong, doi PYTHON_CMD thanh python hoac duong dan python.exe day du.
set "PYTHON_CMD=py"

set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%scripts\incremental_backup.py"

if not exist "%PY_SCRIPT%" (
    echo Khong tim thay file Python: "%PY_SCRIPT%"
    exit /b 1
)

echo Dang chay backup...
"%PYTHON_CMD%" "%PY_SCRIPT%" --source "%SOURCE_DIR%" --backup "%BACKUP_DIR%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo Backup that bai. Ma loi: %EXIT_CODE%
    exit /b %EXIT_CODE%
)

echo Backup thanh cong.
pause
