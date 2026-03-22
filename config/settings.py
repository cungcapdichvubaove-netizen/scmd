# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: config/settings.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-22
Description: Cấu hình trung tâm (Core Settings).
             UPGRADE PHASE 12.1: 
             - Tích hợp Hybrid GIS Loader (Docker/Windows).
             - Tối ưu hóa hiệu suất Query & Caching Template.
             - Chuẩn hóa định dạng hiển thị Tiếng Việt (PEP8 Compliance).
             - Gia cố Error Handling cho Database & Static Files.
"""

import logging
import os
import shutil
import sys
import urllib.parse
from pathlib import Path

# Third-party imports
import dj_database_url
import sentry_sdk
from decouple import Csv, config, UndefinedValueError
from django.core.management.utils import get_random_secret_key
from sentry_sdk.integrations.django import DjangoIntegration

# --- LOGGER CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CẤU HÌNH CƠ BẢN & BẢO MẬT
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

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
        for origin in debug_origins:
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)
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

# ==============================================================================
# 2. INSTALLED APPS (Thứ tự ưu tiên: Jazzmin > Admin > Apps)
# ==============================================================================
INSTALLED_APPS = [
    "daphne",                # ASGI Server
    "jazzmin",               # Admin UI (Phải đứng trước admin)
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
    "channels",
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
    "whitenoise.middleware.WhiteNoiseMiddleware", # Xử lý static files nhanh
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
            # Tối ưu hóa nạp Template bằng bộ nhớ đệm (Cached Loader) khi không ở DEBUG
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

# Cấu hình Database (Mặc định PostGIS cho SCMD)
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
        logger.error(f"Lỗi kết nối DB: {e}. Chuyển hướng sang SQLite dự phòng.")
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3", 
                "NAME": str(BASE_DIR / "db.sqlite3")
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3", 
            "NAME": str(BASE_DIR / "db.sqlite3")
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# 6. QUỐC TẾ HÓA (Chuẩn Việt Nam - ISO 8601 Compliance)
# ==============================================================================
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
USE_L10N = False 

# Định dạng hiển thị ngày tháng chuẩn ngành an ninh
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

# Sử dụng WhiteNoise để nén và đặt mã băm (hash) cho file tĩnh
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# 9. ADMIN UI (JAZZMIN) - Tích hợp từ file cấu hình riêng
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
    # --- MÔI TRƯỜNG WINDOWS (Local Development) ---
    BASE_OSGEO4W = config("OSGEO4W_ROOT", default=r"C:\OSGeo4W") 
    OSGEO4W_BIN = os.path.join(BASE_OSGEO4W, "bin")
    
    if os.path.exists(OSGEO4W_BIN):
        os.environ['PATH'] = OSGEO4W_BIN + os.pathsep + os.environ['PATH']
        try:
            os.add_dll_directory(OSGEO4W_BIN)
        except (AttributeError, Exception):
            pass
        
        # Tự động quét DLL GDAL phù hợp (Ưu tiên v308)
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
    # --- MÔI TRƯỜNG DOCKER/LINUX (Production) ---
    # Django sẽ tự động tìm kiếm GDAL trong /usr/lib/ hoặc /usr/local/lib/
    pass

# Cấu hình đăng xuất & điều hướng
LOGOUT_ON_GET = True 
LOGOUT_REDIRECT_URL = 'main:login'