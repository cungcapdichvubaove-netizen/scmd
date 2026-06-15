# -*- coding: utf-8 -*-
"""
Jazzmin configuration for the SCMD Pro operations admin shell.

The admin shell is a working console, not a marketing site and not a purely
technical menu. Keep the topbar quiet; navigation belongs in the sidebar and in
role-aware workspaces rendered by the admin index.
"""

import logging

from decouple import UndefinedValueError, config

logger = logging.getLogger(__name__)

try:
    ADMIN_UI_FEATURE_FLAG = config("ADMIN_UI_FEATURE_FLAG", default=True, cast=bool)
except (UndefinedValueError, Exception):
    ADMIN_UI_FEATURE_FLAG = True

try:
    _JAZZMIN_SITE_TITLE = config("JAZZMIN_SITE_TITLE", default="Quản trị kỹ thuật SCMD")
    _JAZZMIN_SITE_HEADER = config("JAZZMIN_SITE_HEADER", default="Quản trị kỹ thuật SCMD")
    _JAZZMIN_SITE_BRAND = config("JAZZMIN_SITE_BRAND", default="Quản trị kỹ thuật SCMD")
    _JAZZMIN_WELCOME_SIGN = config(
        "JAZZMIN_WELCOME_SIGN",
        default="Bàn làm việc vận hành SCMD Pro",
    )
    _JAZZMIN_COPYRIGHT = config("JAZZMIN_COPYRIGHT", default="SCMD © 2026")
    _JAZZMIN_THEME = config("JAZZMIN_THEME", default="flatly")
    _JAZZMIN_DARK_THEME = config("JAZZMIN_DARK_THEME", default="darkly")
    _SITE_LOGO = config("JAZZMIN_SITE_LOGO", default="img/brand/logo-symbol.png")
    _LOGIN_LOGO = config("JAZZMIN_LOGIN_LOGO", default="img/brand/logo-symbol.png")
    _SITE_ICON = config("JAZZMIN_SITE_ICON", default="img/brand/favicon.ico")
    _CUSTOM_CSS = config("JAZZMIN_CUSTOM_CSS", default="common/css/custom_admin.css")
    _CUSTOM_JS = config("JAZZMIN_CUSTOM_JS", default="js/scmd_jazzmin_scroll.js")
except (UndefinedValueError, Exception) as exc:
    logger.warning("Jazzmin config fallback applied: %s", exc)
    _JAZZMIN_SITE_TITLE = "Quản trị kỹ thuật SCMD"
    _JAZZMIN_SITE_HEADER = "Quản trị kỹ thuật SCMD"
    _JAZZMIN_SITE_BRAND = "Quản trị kỹ thuật SCMD"
    _JAZZMIN_WELCOME_SIGN = "Bàn làm việc vận hành SCMD Pro"
    _JAZZMIN_COPYRIGHT = "SCMD © 2026"
    _JAZZMIN_THEME = "flatly"
    _JAZZMIN_DARK_THEME = "darkly"
    _SITE_LOGO = "img/brand/logo-symbol.png"
    _LOGIN_LOGO = "img/brand/logo-symbol.png"
    _SITE_ICON = "img/brand/favicon.ico"
    _CUSTOM_CSS = "common/css/custom_admin.css"
    _CUSTOM_JS = "js/scmd_jazzmin_scroll.js"

JAZZMIN_SETTINGS = {
    "site_title": _JAZZMIN_SITE_TITLE,
    "site_header": _JAZZMIN_SITE_HEADER,
    "site_brand": _JAZZMIN_SITE_BRAND,
    "site_logo": _SITE_LOGO,
    "login_logo": _LOGIN_LOGO,
    "login_logo_dark": config("JAZZMIN_LOGIN_LOGO_DARK", default=_LOGIN_LOGO),
    "site_logo_classes": "scmd-admin-brand-symbol",
    "site_icon": _SITE_ICON,
    "welcome_sign": _JAZZMIN_WELCOME_SIGN,
    "copyright": _JAZZMIN_COPYRIGHT,
    # V10: disable Jazzmin model search in the topbar. Jazzmin renders one
    # compact search widget per configured model, which caused the repeated
    # search/icon regression reported in browser QA. A true unified command
    # search should be implemented as one dedicated endpoint, not by adding
    # multiple models here.
    "search_model": [],
    # The topbar must not become a second module navigation. Business navigation
    # belongs in the sidebar and operations workspace.
    "topmenu_links": [],
    "show_sidebar": True,
    "navigation_expanded": False,
    "hide_apps": [],
    "hide_models": [],
    # Sidebar should list stable admin destinations only. The work queue is
    # already rendered inside the admin index dashboard and must not be
    # duplicated here as a pseudo-navigation entry.
    "custom_links": {},
    "order_with_respect_to": [
        "main",
        "operations",
        "users",
        "clients",
        "inspection",
        "inventory",
        "accounting",
        "workflow",
        "reports",
        "notifications",
        "backup_restore",
        "auth",
        "django_celery_beat",
        "django_celery_results",
        "sessions",
        "dashboard",
    ],
    "icons": {
        "auth": "fas fa-user-shield",
        "auth.user": "fas fa-user-lock",
        "auth.Group": "fas fa-users-cog",
        "main": "fas fa-shield-alt",
        "main.AuditLog": "fas fa-clipboard-check",
        "main.WorkerHeartbeat": "fas fa-heartbeat",
        "dashboard": "fas fa-th-large",
        "clients": "fas fa-handshake",
        "operations": "fas fa-clipboard-list",
        "inspection": "fas fa-search-location",
        "users": "fas fa-users-cog",
        "workflow": "fas fa-route",
        "accounting": "fas fa-calculator",
        "inventory": "fas fa-boxes",
        "reports": "fas fa-chart-pie",
        "notifications": "fas fa-bell",
        "backup_restore": "fas fa-database",
        "django_celery_beat": "fas fa-calendar-alt",
        "django_celery_results": "fas fa-history",
        "users.NhanVien": "fas fa-id-card-alt",
        "users.HopDongLaoDong": "fas fa-file-contract",
        "users.PhuLucHopDongLaoDong": "fas fa-file-signature",
        "users.DonNghiPhep": "fas fa-calendar-minus",
        "users.QuyetDinhNghiViec": "fas fa-person-walking-arrow-right",
        "users.OffboardingChecklist": "fas fa-list-check",
        "users.HoSoBaoHiem": "fas fa-shield-heart",
        "users.PhongBan": "fas fa-sitemap",
        "users.ChucDanh": "fas fa-user-tag",
        "clients.MucTieu": "fas fa-fort-awesome",
        "operations.BaoCaoSuCo": "fas fa-exclamation-triangle",
        "operations.ShiftChangeRequest": "fas fa-right-left",
        "accounting.TamUngLuong": "fas fa-hand-holding-dollar",
        "accounting.KhoanKhauTruNhanVien": "fas fa-receipt",
        "clients.PhuLucHopDongDichVu": "fas fa-file-signature",
        "clients.BienBanNghiemThu": "fas fa-clipboard-check",
        "clients.HoaDon": "fas fa-file-invoice-dollar",
        "clients.CongNo": "fas fa-scale-balanced",
        "clients.ThanhToanKhachHang": "fas fa-money-bill-transfer",
        "clients.PhanBoThanhToanHoaDon": "fas fa-list-check",
        "workflow.Task": "fas fa-clipboard-check",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "far fa-dot-circle",
    "related_modal_active": True,
    "use_google_fonts_cdn": False,
    "custom_css": _CUSTOM_CSS,
    "custom_js": _CUSTOM_JS,
    "show_ui_builder": False,
    # Use a single continuous form by default. Horizontal tabs looked compact,
    # but they hid required fields when Bootstrap tab activation failed and
    # made data entry unclear on operational admin screens.
    "changeform_format": "single",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-white",
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": _JAZZMIN_THEME,
    "dark_mode_theme": _JAZZMIN_DARK_THEME,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

if not ADMIN_UI_FEATURE_FLAG:
    JAZZMIN_SETTINGS = {
        "show_ui_builder": False,
        "site_title": _JAZZMIN_SITE_TITLE,
        "site_header": _JAZZMIN_SITE_HEADER,
        "site_brand": _JAZZMIN_SITE_BRAND,
        "site_logo": _SITE_LOGO,
        "welcome_sign": _JAZZMIN_WELCOME_SIGN,
        "copyright": _JAZZMIN_COPYRIGHT,
    }
    JAZZMIN_UI_TWEAKS = {"theme": "default", "dark_mode_theme": None}
