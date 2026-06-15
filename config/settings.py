# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: config/settings.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-24
Description: Cau hinh trung tam (Core Settings).
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
from typing import cast
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


def _find_first_existing_path(candidates):
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def configure_windows_gis_runtime():
    """
    Resolve native GDAL/PROJ paths on Windows before GeoDjango imports run.

    The project contract keeps GeoDjango enabled because attendance/location
    integrity depends on PointField. When the runtime is missing, fail fast with
    an actionable error instead of letting the web process die later and surface
    as an empty HTTP response.
    """
    if os.name != "nt":
        return

    explicit_root = config("OSGEO4W_ROOT", default="")
    root_candidates = [
        explicit_root,
        r"C:\OSGeo4W",
        r"C:\OSGeo4W64",
        r"C:\Program Files\QGIS 3.40.0",
        r"C:\Program Files\QGIS 3.38.0",
        r"C:\Program Files\QGIS 3.36.0",
        r"C:\Program Files\QGIS 3.34.0",
    ]

    base_root = _find_first_existing_path(root_candidates)
    if not base_root:
        raise ImproperlyConfigured(
            "Khong tim thay runtime GDAL/PROJ tren Windows. "
            "Can cai OSGeo4W/QGIS hoac dat bien OSGEO4W_ROOT truoc khi khoi dong SCMD Pro."
        )

    bin_candidates = [
        os.path.join(base_root, "bin"),
        os.path.join(base_root, "apps", "gdal", "bin"),
    ]
    osgeo_bin = _find_first_existing_path(bin_candidates)
    if not osgeo_bin:
        raise ImproperlyConfigured(
            f"Khong tim thay thu muc bin cua GDAL trong '{base_root}'. "
            "Hay kiem tra lai OSGEO4W_ROOT hoac ban cai QGIS/OSGeo4W."
        )

    gdal_candidates = sorted(
        [
            os.path.join(osgeo_bin, filename)
            for filename in os.listdir(osgeo_bin)
            if filename.lower().startswith("gdal") and filename.lower().endswith(".dll")
        ],
        reverse=True,
    )
    gdal_library_path = _find_first_existing_path(gdal_candidates)
    if not gdal_library_path:
        raise ImproperlyConfigured(
            f"Khong tim thay file gdal*.dll trong '{osgeo_bin}'. "
            "SCMD Pro khong the khoi dong GeoDjango neu thieu native GDAL runtime."
        )

    proj_candidates = [
        os.path.join(base_root, "share", "proj"),
        os.path.join(base_root, "apps", "proj", "share", "proj"),
    ]
    proj_lib = _find_first_existing_path(proj_candidates)
    if not proj_lib:
        raise ImproperlyConfigured(
            f"Khong tim thay du lieu PROJ trong '{base_root}'. "
            "Hay cai day du runtime GDAL/PROJ cho GeoDjango."
        )

    os.environ["PATH"] = osgeo_bin + os.pathsep + os.environ.get("PATH", "")
    os.environ["PROJ_LIB"] = proj_lib
    try:
        os.add_dll_directory(osgeo_bin)
    except (AttributeError, FileNotFoundError, OSError):
        pass

    return gdal_library_path


COMMON_INSECURE_CREDENTIAL_VALUES = {
    "",
    "admin",
    "password",
    "123456",
    "changeme",
    "change-me",
    "please_change",
    "change-this-admin-password",
    "change-this-seed-password",
    "local/dev only",
    "scmd_pass",
}


def _normalize_secret(value):
    if value is None:
        return None
    return str(value).strip()


def is_insecure_default(value, insecure_defaults=()):
    normalized = _normalize_secret(value)
    if normalized is None:
        return False

    lowered = normalized.lower()
    explicit_defaults = {str(item).strip().lower() for item in insecure_defaults}
    if lowered in explicit_defaults:
        return True
    if lowered in COMMON_INSECURE_CREDENTIAL_VALUES:
        return True
    if lowered.startswith("django-insecure-"):
        return True
    if "change-this" in lowered or "please-change" in lowered:
        return True
    return False


def require_production_safe_value(name, value, *, insecure_defaults=()):
    if DEBUG:
        return value
    if value is None:
        logger.critical("BAO MAT: %s chua duoc thiet lap trong moi truong Production.", name)
        raise ImproperlyConfigured(f"BAO MAT: {name} phai duoc thiet lap trong moi truong Production.")
    if is_insecure_default(value, insecure_defaults):
        logger.critical("BAO MAT: %s dang dung gia tri mac dinh/placeholder trong Production.", name)
        raise ImproperlyConfigured(f"BAO MAT: {name} khong duoc dung gia tri mac dinh trong moi truong Production.")
    return value


def get_required_secret(name, *, aliases=(), insecure_defaults=()):
    value = config(name, default=None)
    if value is None:
        for alias in aliases:
            value = config(alias, default=None)
            if value is not None:
                break
    if DEBUG:
        if value is None and insecure_defaults:
            return insecure_defaults[0]
        return value

    return require_production_safe_value(name, value, insecure_defaults=insecure_defaults)

# ==============================================================================
# 1. CẤU HÌNH CƠ BẢN & BẢO MẬT
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ID tổ chức mặc định (SSOT cho Single-Organization ERP)
# SCMD PRO sẽ nạp biến này động từ request, bản ERP hiện tại dùng cấu hình cứng.
SCMD_ORGANIZATION_ID = config("SCMD_ORGANIZATION_ID", default="d8f89835-f716-419b-9800-47b74403387c", cast=uuid.UUID)

ENVIRONMENT = config("ENVIRONMENT", default="development")
SCMD_DOCKER_COMPOSE = config("SCMD_DOCKER_COMPOSE", default="")
SCMD_DOCKER_PROD_MODE = str(SCMD_DOCKER_COMPOSE).strip().lower() in {"prod", "production", "demo"}

DEBUG = config("DEBUG", default="False", cast=bool)

# Quản lý SECRET_KEY an toàn. Production fail-fast nếu thiếu hoặc dùng key mẫu/dev.
try:
    SECRET_KEY = config("SECRET_KEY")
except UndefinedValueError:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
        logger.warning("BẢO MẬT: Sử dụng SECRET_KEY ngẫu nhiên trong chế độ DEBUG.")
    else:
        logger.critical("BẢO MẬT: SECRET_KEY chưa được thiết lập trong môi trường Production.")
        raise ImproperlyConfigured("BẢO MẬT: SECRET_KEY phải được thiết lập trong môi trường Production.")
else:
    SECRET_KEY = require_production_safe_value(
        "SECRET_KEY",
        SECRET_KEY,
        insecure_defaults=(
            "django-insecure-local-dev-key",
            "your-very-secret-key-here-change-this-in-production!",
            "change-me",
        ),
    )

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
        current_origins = list(CSRF_TRUSTED_ORIGINS)  # type: ignore
        for origin in debug_origins:
            if origin not in current_origins:
                current_origins.append(origin)
        CSRF_TRUSTED_ORIGINS = current_origins
    except Exception as e:
        logger.warning(f"Không thể thiết lập debug_origins: {e}")

# Cấu hình bảo mật HTTPS/SSL
# Admin related-object editing uses same-origin modal iframes in Jazzmin.
# Keep cross-origin framing blocked while allowing those in-admin flows.
X_FRAME_OPTIONS = config("X_FRAME_OPTIONS", default="SAMEORIGIN")

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False
else:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default="True", cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True  
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- CẤU HÌNH EXPORT ---
# Mật khẩu bảo vệ file Excel xuất ra (Security by Design)
EXCEL_EXPORT_PASSWORD = get_required_secret(
    "EXCEL_EXPORT_PASSWORD",
    insecure_defaults=(
        "SCMD@Audit2026",
        "strong-export-password-required-in-production",
    ),
)

# --- CẤU HÌNH MÃ HÓA DỮ LIỆU (AES-256) ---
# Khóa mã hóa phải là 32 bytes (base64 encoded). Không được làm mất khóa này.
FIELD_ENCRYPTION_KEY = get_required_secret(
    "FIELD_ENCRYPTION_KEY",
    aliases=("ENCRYPTION_KEY",),
    insecure_defaults=(
        "YmFzZTY0LWVuY29kZWQtMzItYnl0ZS1rZXktZ2VuZXJhdGVk",
        "base64-encoded-32-byte-key-required-in-production",
    ),
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
    "rest_framework_simplejwt.token_blacklist",
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
    "main.middleware.DashboardPerformanceInstrumentationMiddleware",
    "main.middleware.AccessDeniedExperienceMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SCMD_PERF_INSTRUMENTATION = config("SCMD_PERF_INSTRUMENTATION", default=DEBUG, cast=bool)
SCMD_PERF_INSTRUMENTATION_PATH_PREFIXES = (
    "/admin/",
    "/dashboard/",
    "/operations/",
    "/accounting/",
    "/inventory/",
    "/users/",
    "/clients/",
    "/inspection/",
    "/workflow/",
    "/mobile/",
)
SCMD_PRO_CACHE_VERSION = config(
    "SCMD_PRO_CACHE_VERSION",
    default=config("RELEASE_VERSION", default="2026-06-14-demo-hardening"),
)

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
                "main.context_processors.notification_context",
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
def _database_host_from_url(database_url):
    try:
        parsed = urllib.parse.urlparse(database_url)
    except Exception:
        return None
    return parsed.hostname


def _database_scheme_from_url(database_url):
    try:
        parsed = urllib.parse.urlparse(database_url)
    except Exception:
        return None
    return parsed.scheme


def _validate_compose_database_contract(database_url):
    if not SCMD_DOCKER_PROD_MODE:
        return
    if not database_url:
        raise ImproperlyConfigured(
            "DATABASE_URL must be set when running docker-compose.prod.yml. "
            "Use postgis://<SQL_USER>:<SQL_PASSWORD>@db:5432/<SQL_DATABASE>."
        )

    scheme = (_database_scheme_from_url(database_url) or "").lower()
    if scheme.startswith("sqlite"):
        raise ImproperlyConfigured(
            "SQLite is not allowed when running docker-compose.prod.yml. "
            "Set DATABASE_URL to a PostGIS URL using host 'db'."
        )

    hostname = (_database_host_from_url(database_url) or "").lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ImproperlyConfigured(
            "DATABASE_URL must use Docker service host 'db' in docker-compose.prod.yml, "
            "not localhost/127.0.0.1."
        )


def _validate_compose_database_engine(database_config):
    if not SCMD_DOCKER_PROD_MODE:
        return
    engine = database_config.get("ENGINE", "")
    if engine == "django.db.backends.sqlite3" or "sqlite" in engine:
        raise ImproperlyConfigured(
            "SQLite backend is forbidden in docker-compose.prod.yml. "
            "Django must run with django.contrib.gis.db.backends.postgis."
        )
    if engine != "django.contrib.gis.db.backends.postgis":
        raise ImproperlyConfigured(
            "docker-compose.prod.yml must run Django with "
            "django.contrib.gis.db.backends.postgis."
        )


DATABASE_URL: str | None = cast(str | None, config("DATABASE_URL", default=None))
_validate_compose_database_contract(DATABASE_URL)
if DATABASE_URL:
    try:
        DATABASES = {
            "default": dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                ssl_require=config("DB_SSL_REQUIRE", default="False", cast=bool),  # type: ignore
                engine="django.contrib.gis.db.backends.postgis",
            )
        }
        _validate_compose_database_engine(DATABASES["default"])
    except ImproperlyConfigured:
        raise
    except Exception as e:
        if not DEBUG or SCMD_DOCKER_PROD_MODE:
            logger.critical("DATABASE CONFIGURATION ERROR: %s", e)
            raise ImproperlyConfigured("Database configuration failed. Check DATABASE_URL.") from e
        logger.error("Lỗi cấu hình DB: %s. Chuyển sang SQLite dev theo DEBUG=True.", e)
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}}
else:
    if not DEBUG or SCMD_DOCKER_PROD_MODE:
        raise ImproperlyConfigured("DATABASE_URL must be set in production/demo Docker environment.")
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

# --- ATTENDANCE POLICY DEFAULTS (Operations integrity contract) ---
# Check-in is allowed from `shift_start - ATTENDANCE_CHECKIN_EARLY_MINUTES`
# until `shift_end + ATTENDANCE_CHECKIN_LATE_MINUTES`.
# With the default late value `0`, staff may still check in until the scheduled
# shift end time. This is intentional for long-running operational shifts and
# must be covered by regression tests.
ATTENDANCE_CHECKIN_EARLY_MINUTES = config(
    "ATTENDANCE_CHECKIN_EARLY_MINUTES",
    default="60",
    cast=int,
)
ATTENDANCE_CHECKIN_LATE_MINUTES = config(
    "ATTENDANCE_CHECKIN_LATE_MINUTES",
    default="0",
    cast=int,
)
ATTENDANCE_CHECKOUT_EARLY_MINUTES = config(
    "ATTENDANCE_CHECKOUT_EARLY_MINUTES",
    default="0",
    cast=int,
)
ATTENDANCE_CHECKOUT_LATE_MINUTES = config(
    "ATTENDANCE_CHECKOUT_LATE_MINUTES",
    default="240",
    cast=int,
)
ATTENDANCE_REQUIRE_IMAGE_CHECKIN = config(
    "ATTENDANCE_REQUIRE_IMAGE_CHECKIN",
    default="False",
    cast=bool,
)
ATTENDANCE_REQUIRE_IMAGE_CHECKOUT = config(
    "ATTENDANCE_REQUIRE_IMAGE_CHECKOUT",
    default="False",
    cast=bool,
)
ALIVE_CHECK_REQUIRE_SELFIE = config(
    "ALIVE_CHECK_REQUIRE_SELFIE",
    default="False",
    cast=bool,
)

from datetime import timedelta

SIMPLE_JWT_ACCESS_TOKEN_HOURS = config(
    "SIMPLE_JWT_ACCESS_TOKEN_HOURS",
    default="8",
    cast=int,
)
SIMPLE_JWT_REFRESH_TOKEN_DAYS = config(
    "SIMPLE_JWT_REFRESH_TOKEN_DAYS",
    default="7",
    cast=int,
)
SIMPLE_JWT_SIGNING_KEY = config("SIMPLE_JWT_SIGNING_KEY", default=SECRET_KEY)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=SIMPLE_JWT_ACCESS_TOKEN_HOURS),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=SIMPLE_JWT_REFRESH_TOKEN_DAYS),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SIMPLE_JWT_SIGNING_KEY,
}

# Explicit CORS Origins (Rule 12.4)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv())

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Map tile provider is configurable so operations dashboard can use OSM by
# default, or an internal/proxy tile service in production without JS changes.
SCMD_MAP_TILE_URL = config("SCMD_MAP_TILE_URL", default="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
SCMD_MAP_ATTRIBUTION = config("SCMD_MAP_ATTRIBUTION", default="&copy; OpenStreetMap contributors")

# ==============================================================================
# 5. REDIS & CELERY & CHANNELS (Real-time Core)
# ==============================================================================
REDIS_URL = config("REDIS_URL", default=None if SCMD_DOCKER_PROD_MODE else "redis://redis:6379/0")
if SCMD_DOCKER_PROD_MODE:
    parsed_redis_url = urllib.parse.urlparse(REDIS_URL)
    if not REDIS_URL:
        raise ImproperlyConfigured("REDIS_URL must be set when running docker-compose.prod.yml.")
    if (parsed_redis_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ImproperlyConfigured(
            "REDIS_URL must use Docker service host 'redis' in docker-compose.prod.yml, "
            "not localhost/127.0.0.1."
        )

# Django shared cache. Django's native RedisCache avoids adding django-redis
# while keeping dashboard/API caches shared across web processes.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
        "KEY_PREFIX": "scmd_pro",
    }
}

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

# --- CELERY RELIABILITY & MONITORING ---
CELERY_TASK_ACKS_LATE = True  # Chỉ xác nhận đã xong sau khi xử lý thành công (chống mất task khi worker crash)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Tránh việc worker ôm quá nhiều task gây nghẽn
CELERY_TASK_REJECT_ON_WORKER_LOST = True # Đẩy lại task vào queue nếu worker bị kill đột ngột
CELERY_TASK_SEND_SENT_EVENT = True # Cho phép các công cụ monitoring (như Flower) theo dõi event gửi task
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_SEND_TASK_EVENTS = True

# Cấu hình lịch trình tác vụ định kỳ (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    'accounting_calculate_monthly_payroll': { # Corrected task name
        'task': 'accounting.tasks.accounting_calculate_monthly_payroll',
        'schedule': crontab(hour=1, minute=0, day_of_month='1'),
        'description': 'Tự động tính lương cho tháng trước vào 1 giờ sáng ngày đầu tháng.',
    },
    'auto_lock_resigned_employees_daily': {
        'task': 'users.tasks.auto_lock_resigned_employees_task',
        'schedule': crontab(hour=2, minute=0),
        'description': 'Tự động khóa hồ sơ nhân sự nghỉ việc sau 30 ngày (chạy 2h sáng hàng ngày).',
    },
    'monitor_target_stability_daily': {
        'task': 'operations.tasks.check_target_stability_daily_task',
        'schedule': crontab(hour=4, minute=0),
        'description': 'Kiểm tra tỷ lệ đổi ca bất thường tại các mục tiêu (chạy 4h sáng hàng ngày).',
    },
    'celery_worker_heartbeat_ping': {
        'task': 'operations.tasks.update_worker_heartbeat_task',
        'schedule': timedelta(minutes=1),
        'description': 'Workers tự báo cáo trạng thái mỗi phút.',
    },
    'celery_health_monitor_broadcast': {
        'task': 'operations.tasks.monitor_worker_health_and_broadcast_task',
        'schedule': timedelta(minutes=2),
        'description': 'Quét trạng thái rủi ro của workers và cập nhật bảng điều hành vận hành.',
    },
    'operations_mark_expired_alive_checks': {
        'task': 'operations.tasks.operations_mark_expired_alive_checks',
        'schedule': timedelta(minutes=5), # Run every 5 minutes
        'description': 'Tự động đánh dấu quá hạn cho các yêu cầu Alive Check không phản hồi.',
    },
    'operations_check_late_checkout_daily': {
        'task': 'operations.tasks.check_late_checkout_task',
        'schedule': crontab(hour=5, minute=0), # Run daily at 5 AM
        'description': 'Quét và đánh dấu các ca trực chưa check-out quá 2 giờ sau giờ kết thúc.',
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

# Date/time display contract for SCMD Pro UI/admin/export surfaces.
# Database/API protocol values may still use ISO-8601 where required by HTML5 inputs, URLs,
# JSON clients or backup filenames; user-facing display must use Vietnamese format.
FORMAT_MODULE_PATH = ["config.formats"]

DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
TIME_FORMAT = "H:i"
YEAR_MONTH_FORMAT = "m/Y"
MONTH_DAY_FORMAT = "d/m"
FIRST_DAY_OF_WEEK = 1

DATE_INPUT_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",  # HTML5 date input / API compatibility; not the display format.
]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%Y-%m-%dT%H:%M",  # HTML5 datetime-local compatibility.
    "%Y-%m-%d %H:%M:%S",
]

# ==============================================================================
# 7. STATIC & MEDIA
# ==============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
TAILWIND_APP_NAME = "theme"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# 8. CẤU HÌNH EMAIL (SMTP)
# ==============================================================================
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default="587", cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default="True", cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="SCMD <no-reply@scmd.vn>")
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
if os.name == "nt":
    GDAL_LIBRARY_PATH = configure_windows_gis_runtime()
else:
    # Django PostGIS engine tự động nhận diện GDAL trên Linux
    pass

# Cấu hình đăng xuất & điều hướng
LOGOUT_ON_GET = True 
LOGOUT_REDIRECT_URL = 'main:login'
