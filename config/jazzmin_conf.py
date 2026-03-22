# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: config/jazzmin_conf.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-22
Description: Tách biệt cấu hình giao diện Admin (Jazzmin) khỏi core settings.
             UPGRADE PHASE 12.3: 
             - Chuẩn hóa PEP8 & Tối ưu hóa hiệu suất load UI.
             - Fix lỗi không hiển thị Icon cho App Labels bằng cách map chính xác App Name.
             - UI REFINEMENT: Sửa lỗi hiển thị tên danh mục bị rớt dòng và màu nền Sidebar.
"""

import logging
from decouple import config, UndefinedValueError

# Khởi tạo logger để ghi lại các vấn đề về cấu hình
logger = logging.getLogger(__name__)

# --- FEATURE FLAG ---
try:
    ADMIN_UI_FEATURE_FLAG = config("ADMIN_UI_FEATURE_FLAG", default=True, cast=bool)
except (UndefinedValueError, Exception):
    ADMIN_UI_FEATURE_FLAG = True

# --- THEME CONFIGURATION ---
# Sử dụng khối try-except bao quát để đảm bảo hệ thống luôn có giá trị fallback an toàn
try:
    _JAZZMIN_SITE_TITLE = config("JAZZMIN_SITE_TITLE", default="SCMD Commander")
    _JAZZMIN_SITE_HEADER = config("JAZZMIN_SITE_HEADER", default="SCMD System")
    _JAZZMIN_SITE_BRAND = config("JAZZMIN_SITE_BRAND", default="SCMD PRO")
    _JAZZMIN_WELCOME_SIGN = config("JAZZMIN_WELCOME_SIGN", default="Hệ thống Điều hành & Chỉ huy An ninh SCMD")
    _JAZZMIN_COPYRIGHT = config("JAZZMIN_COPYRIGHT", default="SCMD Security Co., Ltd © 2026")
    _JAZZMIN_THEME = config("JAZZMIN_THEME", default="litera")
    _JAZZMIN_DARK_THEME = config("JAZZMIN_DARK_THEME", default="darkly")
    _SITE_LOGO = config("JAZZMIN_SITE_LOGO", default="img/logo_moi.png")
    _LOGIN_LOGO = config("JAZZMIN_LOGIN_LOGO", default="img/logo_moi.png")
    _SITE_ICON = config("JAZZMIN_SITE_ICON", default="img/logo_moi.png")
    _CUSTOM_CSS = config("JAZZMIN_CUSTOM_CSS", default="common/css/custom_admin.css")
    _CUSTOM_JS = config("JAZZMIN_CUSTOM_JS", default="admin/js/scmd_jazzmin_scroll.js")
except (UndefinedValueError, Exception) as e:
    logger.warning(f"Jazzmin Config: Lỗi đọc biến môi trường. Sử dụng giá trị mặc định. Chi tiết: {e}")
    _JAZZMIN_SITE_TITLE = "SCMD Commander"
    _JAZZMIN_SITE_HEADER = "SCMD System"
    _JAZZMIN_SITE_BRAND = "SCMD PRO"
    _JAZZMIN_WELCOME_SIGN = "Hệ thống Điều hành & Chỉ huy An ninh SCMD"
    _JAZZMIN_COPYRIGHT = "SCMD Security Co., Ltd © 2026"
    _JAZZMIN_THEME = "litera"
    _JAZZMIN_DARK_THEME = "darkly"
    _SITE_LOGO = "img/logo_moi.png"
    _LOGIN_LOGO = "img/logo_moi.png"
    _SITE_ICON = "img/logo_moi.png"
    _CUSTOM_CSS = "common/css/custom_admin.css"
    _CUSTOM_JS = "admin/js/scmd_jazzmin_scroll.js"

# --- MAIN SETTINGS ---
JAZZMIN_SETTINGS = {
    "site_title": _JAZZMIN_SITE_TITLE,
    "site_header": _JAZZMIN_SITE_HEADER,
    "site_brand": _JAZZMIN_SITE_BRAND,
    "site_logo": _SITE_LOGO,
    "login_logo": _LOGIN_LOGO,
    "login_logo_dark": config("JAZZMIN_LOGIN_LOGO_DARK", default=_LOGIN_LOGO),
    "site_logo_classes": "img-circle elevation-3",
    "site_icon": _SITE_ICON,
    "welcome_sign": _JAZZMIN_WELCOME_SIGN,
    "copyright": _JAZZMIN_COPYRIGHT,
    "search_model": ["users.NhanVien", "clients.MucTieu"],
    "user_avatar": "nhan_vien.anh_the", 
    
    "topmenu_links": [
        {"name": "🎯 Trang chủ", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "🛡️ CEO Dashboard", "url": "dashboard:main", "icon": "fas fa-chart-line", "permissions": ["auth.view_user"]},
        {"name": "🚀 Vận hành", "url": "operations:dashboard_vanhanh", "icon": "fas fa-shield-alt", "new_window": False},
        {"name": "📋 Việc cần làm", "model": "workflow.Task", "icon": "fas fa-tasks"},
        {"name": "🎧 Hỗ trợ", "url": "https://scmdpro.com/support", "icon": "fas fa-headset", "new_window": True},
        {"model": "auth.User"},
    ],

    "show_sidebar": True,
    "navigation_expanded": False, 
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "dashboard", "operations", "inspection", "clients", "users", 
        "workflow", "accounting", "inventory", "reports", "auth", 
        "notifications", "backup_restore", "django_celery_beat"
    ],

    "icons": {
        "auth": "fas fa-user-shield",
        "auth.user": "fas fa-user-lock",
        "auth.Group": "fas fa-users-cog",
        "dashboard": "fas fa-th-large",
        "clients": "fas fa-handshake",
        "operations": "fas fa-project-diagram",
        "inspection": "fas fa-search-location",
        "users": "fas fa-users-cog",
        "workflow": "fas fa-route",
        "accounting": "fas fa-calculator",
        "inventory": "fas fa-boxes",
        "reports": "fas fa-chart-pie",
        "notifications": "fas fa-bell",
        "backup_restore": "fas fa-database",
        "django_celery_beat": "fas fa-calendar-alt",
        
        "users.NhanVien": "fas fa-id-card-alt",
        "users.PhongBan": "fas fa-sitemap",
        "users.ChucDanh": "fas fa-user-tag",
        "clients.MucTieu": "fas fa-fort-awesome",
        "operations.BaoCaoSuCo": "fas fa-exclamation-triangle",
        "workflow.Task": "fas fa-clipboard-check",
    },
    
    "default_icon_parents": "fas fa-folder", 
    "default_icon_children": "far fa-dot-circle",
    
    "related_modal_active": True,
    "use_google_fonts_cdn": True, 
    "custom_css": _CUSTOM_CSS,
    "custom_js": _CUSTOM_JS,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
}

# --- UI TWEAKS ---
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-navy",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-navy",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-navy", 
    "sidebar_nav_small_text": True, 
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True, 
    "sidebar_nav_compact_style": True, 
    "sidebar_nav_legacy_style": True,  
    "sidebar_nav_flat_style": False,
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

# Fallback cho trường hợp tắt UI Feature
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