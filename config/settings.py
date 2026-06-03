# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: config/settings.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-24
Description: Cấu hình trung tâm (Core Settings).
             UPGRADE PHASE 12.2: 
             - Fix lỗi 'NoneType' Channel Layer (Real-time).
             - Tích hợp cấu hình Celery & Redis đồng bộ Docker.
             - Gia cố CSRF & Security Headers cho môi trường Hybrid.
             - Tối ưu hóa hiệu suất nạp Template.
             - HARDENING: Enforce Database Fail-Closed and API Security (JWT/Throttling).
"""

import logging
import os
import shutil
import sys
import urllib.parse
import uuid
from pathlib import Path
from datetime import timedelta

# --- Third-party imports ---
import dj_database_url
import sentry_sdk
from celery.schedules import crontab
from decouple import Csv, config, UndefinedValueError
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from sentry_sdk.integrations.django import DjangoIntegration

# --- LOGGER CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_required_secret(name, *, insecure_defaults=()):
    value = config(name, default=None)
    if DEBUG:
        if value is None and insecure_defaults:
            return insecure_defaults[0]
        return value

    if value is None:
        logger.critical("BAO MAT: %s chua duoc thiet lap trong moi truong Production.", name)
        raise ImproperlyConfigured(f"BAO MAT: {name} phai duoc thiet lap trong moi truong Production.")

    if value in insecure_defaults:
        logger.critical("BAO MAT: %s dang dung gia tri mac dinh khong an toan trong Production.", name)
        raise ImproperlyConfigured(f"BAO MAT: {name} khong duoc dung gia tri mac dinh trong moi truong Production.")

    return value

# ==============================================================================
# 1. CẤU HÌNH CƠ BẢN & BẢO MẬT
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ID tổ chức mặc định (SSOT cho Single-Organization ERP)
# SCMD PRO sẽ nạp biến này động từ request, bản ERP hiện tại dùng cấu hình cứng.
SCMD_ORGANIZATION_ID = config("SCMD_ORGANIZATION_ID", default="d8f89835-f716-419b-9800-47b74403387c", cast=uuid.UUID)

DEBUG = config("DEBUG", default=False, cast=bool)

# Quản lý SECRET_KEY an toàn
try:
    SECRET_KEY = config("SECRET_KEY")
except UndefinedValueError:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
        logger.warning("BẢO MẬT: Sử dụng SECRET_KEY ngẫu nhiên trong chế độ DEBUG.")
    else:
        logger.critical("BẢO MẬT: SECRET_KEY chưa được thiết lập trong môi trường Production.")
        raise ValueError("BẢO MẬT: SECRET_KEY phải được thiết lập trong môi trường Production.")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
if DEBUG:
    ALLOWED_HOSTS = ["*"]

# Quản lý CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
    cast=Csv(),
)

if DEBUG:
    try:
        my_lan_ip = config('MY_LAN_IP', default='192.168.1.1')
        debug_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://0.0.0.0:8000",
            f"http://{my_lan_ip}:8000",
        ]
        # Chuyển thành list để thao tác nếu cần
        current_origins = list(CSRF_TRUSTED_ORIGINS)
        for origin in debug_origins:
            if origin not in current_origins:
                current_origins.append(origin)
        CSRF_TRUSTED_ORIGINS = current_origins
    except Exception as e:
        logger.warning(f"Không thể thiết lập debug_origins: {e}")

# Cấu hình bảo mật HTTPS/SSL
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False
else:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True  
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# --- CẤU HÌNH EXPORT ---
# Mật khẩu bảo vệ file Excel xuất ra (Security by Design)
EXCEL_EXPORT_PASSWORD = get_required_secret(
    "EXCEL_EXPORT_PASSWORD",
    insecure_defaults=("SCMD@Audit2026",),
)

# --- CẤU HÌNH MÃ HÓA DỮ LIỆU (AES-256) ---
# Khóa mã hóa phải là 32 bytes (base64 encoded). Không được làm mất khóa này.
FIELD_ENCRYPTION_KEY = get_required_secret(
    "FIELD_ENCRYPTION_KEY",
    insecure_defaults=("YmFzZTY0LWVuY29kZWQtMzItYnl0ZS1rZXktZ2VuZXJhdGVk",),
)

# ==============================================================================
# 2. INSTALLED APPS (Thứ tự ưu tiên: Daphne > Jazzmin > Apps)
# ==============================================================================
INSTALLED_APPS = [
    "daphne",                # ASGI Server (Phải đứng đầu để xử lý WebSockets)
    "jazzmin",               # Admin UI
    "django.contrib.admin",
    "config.apps_overrides.CustomAuthConfig",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",    # Hỗ trợ bản đồ PostGIS
    "django.contrib.humanize",
    "cloudinary_storage", 
    "cloudinary",          
    "rest_framework",
    "corsheaders",
    "import_export",
    "rolepermissions",       
    "tailwind",
    "theme",
    "django_bootstrap5",
    "phonenumber_field",
    "channels",              # Real-time Framework
    "config.apps_overrides.CustomBeatConfig",
    "config.apps_overrides.CustomResultsConfig",
    "drf_spectacular", 
    
    # SCMD Business Apps
    "main.apps.MainConfig",
    "users.apps.UsersConfig",
    "clients.apps.ClientsConfig",
    "operations.apps.OperationsConfig",
    "inventory.apps.InventoryConfig",
    "inspection.apps.InspectionConfig",
    "accounting.apps.AccountingConfig",
    "workflow.apps.WorkflowConfig",
    "notifications.apps.NotificationsConfig",
    "backup_restore.apps.BackupRestoreConfig",
    "reports.apps.ReportsConfig",
    "dashboard.apps.DashboardConfig",
    "mobile.apps.MobileConfig",
]

ROLEPERMISSIONS_MODULE = 'config.roles'

# ==============================================================================
# 3. MIDDLEWARE & URLS
# ==============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ==============================================================================
# 4. TEMPLATES & DATABASE
# ==============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": False, 
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "main.context_processors.company_info",
            ],
            "loaders": [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if not DEBUG else [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

# Cấu hình Database (Mặc định PostGIS)
DATABASE_URL = config("DATABASE_URL", default=None)
if DATABASE_URL:
    try:
        DATABASES = {
            "default": dj_database_url.config(
                default=DATABASE_URL, 
                conn_max_age=600, 
                ssl_require=config("DB_SSL_REQUIRE", default=False, cast=bool),
                engine='django.contrib.gis.db.backends.postgis'
            )
        }
    except Exception as e:
        if not DEBUG:
            logger.critical(f"PRODUCTION DATABASE ERROR: {e}")
            raise ImproperlyConfigured("Database connection failed in production.")
        else:
            logger.error(f"Lỗi kết nối DB: {e}. Chuyển hướng sang SQLite dự phòng.")
            DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}}
else:
    if not DEBUG:
        raise ImproperlyConfigured("DATABASE_URL must be set in production environment.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}}

# --- API SECURITY (Rule 10 SSOT) ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '2000/day',
        'attendance': '20/minute',  # Giới hạn spam check-in/out
    }
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# Explicit CORS Origins (Rule 12.4)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv())

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# 5. REDIS & CELERY & CHANNELS (Real-time Core)
# ==============================================================================
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/0")

# Cấu hình Channels (Sửa lỗi NoneType cho simulation)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Cấu hình Celery Broker
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = "Asia/Ho_Chi_Minh"

# Cấu hình lịch trình tác vụ định kỳ (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    'accounting_calculate_monthly_payroll': { # Corrected task name
        'task': 'accounting.tasks.accounting_calculate_monthly_payroll',
        'schedule': crontab(hour=1, minute=0, day_of_month='1'),
        'desc': 'Tự động tính lương cho tháng trước vào 1 giờ sáng ngày đầu tháng.',
    },
    'auto_lock_resigned_employees_daily': {
        'task': 'users.tasks.auto_lock_resigned_employees_task',
        'schedule': crontab(hour=2, minute=0),
        'desc': 'Tự động khóa hồ sơ nhân sự nghỉ việc sau 30 ngày (chạy 2h sáng hàng ngày).',
    },
    'monitor_target_stability_daily': {
        'task': 'operations.tasks.check_target_stability_daily_task',
        'schedule': crontab(hour=4, minute=0),
        'desc': 'Kiểm tra tỷ lệ đổi ca bất thường tại các mục tiêu (chạy 4h sáng hàng ngày).',
    },
    'celery_worker_heartbeat_ping': {
        'task': 'operations.tasks.update_worker_heartbeat_task',
        'schedule': timedelta(minutes=1),
        'desc': 'Workers tự báo cáo trạng thái mỗi phút.',
    },
    'celery_health_monitor_broadcast': {
        'task': 'operations.tasks.monitor_worker_health_and_broadcast_task',
        'schedule': timedelta(minutes=2),
        'desc': 'Quét trạng thái rủi ro của Workers và cập nhật War Room.',
    },
    'operations_mark_expired_alive_checks': {
        'task': 'operations.tasks.operations_mark_expired_alive_checks',
        'schedule': timedelta(minutes=5), # Run every 5 minutes
        'desc': 'Tự động đánh dấu quá hạn cho các yêu cầu Alive Check không phản hồi.',
    },
    'operations_check_late_checkout_daily': {
        'task': 'operations.tasks.check_late_checkout_task',
        'schedule': crontab(hour=5, minute=0), # Run daily at 5 AM
        'desc': 'Quét và đánh dấu các ca trực chưa check-out quá 2 giờ sau giờ kết thúc.',
    },
}

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ==============================================================================
# 6. QUỐC TẾ HÓA (Chuẩn Việt Nam - ISO 8601 Compliance)
# ==============================================================================
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
USE_L10N = False 

DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
TIME_FORMAT = "H:i"

# ==============================================================================
# 7. STATIC & MEDIA
# ==============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# 8. CẤU HÌNH EMAIL (SMTP)
# ==============================================================================
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="SCMD ERP <noreply@scmd.vn>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
FCM_SERVER_KEY = config("FCM_SERVER_KEY", default="")

# ==============================================================================
# 9. ADMIN UI (JAZZMIN)
# ==============================================================================
try:
    from .jazzmin_conf import JAZZMIN_SETTINGS, JAZZMIN_UI_TWEAKS
except ImportError:
    logger.error("CẢNH BÁO: Không tìm thấy jazzmin_conf.py. Sử dụng cấu hình trống.")
    JAZZMIN_SETTINGS = {}
    JAZZMIN_UI_TWEAKS = {}

# ==============================================================================
# 10. GIS CONFIGURATION (DOCKER/WINDOWS ADAPTIVE)
# ==============================================================================
if os.name == 'nt':
    # --- WINDOWS DEVELOPMENT ---
    BASE_OSGEO4W = config("OSGEO4W_ROOT", default=r"C:\OSGeo4W") 
    OSGEO4W_BIN = os.path.join(BASE_OSGEO4W, "bin")
    
    if os.path.exists(OSGEO4W_BIN):
        os.environ['PATH'] = OSGEO4W_BIN + os.pathsep + os.environ['PATH']
        try:
            os.add_dll_directory(OSGEO4W_BIN)
        except (AttributeError, Exception):
            pass
        
        try:
            available_dlls = [f for f in os.listdir(OSGEO4W_BIN) if f.startswith('gdal') and f.endswith('.dll')]
            if available_dlls:
                target_dll = 'gdal308.dll' if 'gdal308.dll' in available_dlls else available_dlls[0]
                GDAL_LIBRARY_PATH = os.path.join(OSGEO4W_BIN, target_dll)
        except Exception as e:
            logger.warning(f"Lỗi quét thư mục GDAL trên Windows: {e}")
            
        PROJ_LIB = os.path.join(BASE_OSGEO4W, 'share', 'proj')
        if os.path.exists(PROJ_LIB):
            os.environ['PROJ_LIB'] = PROJ_LIB
else:
    # --- DOCKER/LINUX ---
    # Django PostGIS engine tự động nhận diện GDAL trên Linux
    pass

# Cấu hình đăng xuất & điều hướng
LOGOUT_ON_GET = True 
LOGOUT_REDIRECT_URL = 'main:login'
