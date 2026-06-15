# -*- coding: utf-8 -*-
from django.core.cache import cache
from django.conf import settings

ACCOUNTING_CACHE_NAMESPACE = "accounting:dashboard"
ACCOUNTING_VERSION_KEY = f"{ACCOUNTING_CACHE_NAMESPACE}:version"
ACCOUNTING_DASHBOARD_UI_VERSION = "44.1"

def get_accounting_cache_version():
    """Lấy phiên bản hiện tại của namespace cache kế toán."""
    version = cache.get(ACCOUNTING_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(ACCOUNTING_VERSION_KEY, version, None)
    return version

def build_accounting_dashboard_cache_key(user_id, period, ui_version=None):
    """Xây dựng cache key có scope rõ ràng theo Org, User, UI version và tham số lọc."""
    version = get_accounting_cache_version()
    org_id = getattr(settings, 'SCMD_ORGANIZATION_ID', 'default')
    ui_version = ui_version or ACCOUNTING_DASHBOARD_UI_VERSION
    return f"{ACCOUNTING_CACHE_NAMESPACE}:v{version}:ui{ui_version}:org{org_id}:u{user_id}:p{period}"

def invalidate_accounting_cache():
    """Vô hiệu hóa toàn bộ cache kế toán bằng cách xoay version."""
    try:
        # Tăng version để các key cũ không bao giờ bị truy cập lại (Atomic)
        cache.incr(ACCOUNTING_VERSION_KEY)
    except ValueError:
        # Nếu key chưa tồn tại, khởi tạo lại
        cache.set(ACCOUNTING_VERSION_KEY, 1, None)
