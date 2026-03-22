@echo off
:: =======================================================
:: SCMD - KHOI DONG CAC SERVER PHU TRO (BACKGROUND ONLY)
:: Author: Mr. Anh (CTO)
:: Description: Chi chay Redis, Celery Worker, Celery Beat.
:: =======================================================

title SCMD BACKGROUND SERVICES
color 0B

echo.
echo [1/4] Kiem tra moi truong ao (VENV)...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo    -> OK: Da kich hoat VENV.
) else (
    color 0C
    echo    [!] LOI: Khong tim thay thu muc 'venv'.
    pause
    exit
)

echo.
echo [2/4] Kiem tra REDIS...
:: Thu bat Docker Redis (neu co)
docker start scmd-redis >nul 2>&1
echo    -> (Neu ban dung Memurai/Redis Service thi bo qua buoc nay)

echo.
echo [3/4] Khoi dong CELERY WORKER (Xu ly tac vu nen)...
:: Mo cua so rieng, giu lai neu loi (cmd /k)
start "SCMD - Celery Worker" cmd /k "call venv\Scripts\activate.bat && celery -A config worker -l info -P eventlet"
echo    -> OK: Da mo cua so Worker.

echo.
echo [4/4] Khoi dong CELERY BEAT (Lich trinh)...
start "SCMD - Celery Beat" cmd /k "call venv\Scripts\activate.bat && celery -A config beat -l info"
echo    -> OK: Da mo cua so Beat.

echo.
echo =======================================================
echo    CAC SERVER PHU TRO DANG CHAY!
echo    ---------------------------------------------
echo    Bay gio anh co the chay Web Server thu cong bang lenh:
echo    python manage.py runserver
echo =======================================================
pause