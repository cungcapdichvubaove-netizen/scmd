# -*- coding: utf-8 -*-
"""Central dashboard routing for SCMD Pro.

This module is the single source of truth for post-login routing. It resolves
business workspaces from explicit rolepermissions roles, then from the linked
NhanVien profile (department/title), then from Django groups.

Important: Vietnamese labels are normalized accent-insensitively, including
``đ/Đ`` -> ``d/D``. The resolver supports both exact aliases and conservative
keyword matching for real-world department names such as "Phòng Kế toán - Tài
chính" or "Phòng Nghiệp vụ & Vận hành".
"""

from dataclasses import dataclass
from functools import wraps
import unicodedata

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from rolepermissions.checkers import has_permission, has_role




@dataclass(frozen=True)
class DashboardAccessRule:
    """Central dashboard access rule resolved by role, profile or group aliases."""

    route_name: str
    role_names: tuple[str, ...] = ()
    alias_keys: tuple[str, ...] = ()
    allow_any_authenticated: bool = False

@dataclass(frozen=True)
class DashboardRouteDecision:
    route_name: str
    matched: bool
    source: str


class DashboardRouter:
    ADMIN_ROUTE = "admin:index"
    DEFAULT_ROUTE = "main:access_pending"
    ROUTE_PRIORITY = (
        "dashboard:main",
        "operations:mobile_dashboard",
        "accounting:dashboard",
        "inventory:dashboard",
        "users:dashboard",
        "clients:dashboard_crm",
        "inspection:dashboard",
        "operations:dashboard_vanhanh",
        "reports:report_dashboard",
    )

    # Exact aliases. Keys MUST be normalized by _normalize_key().
    WORKSPACE_ROUTE_ALIASES = {
        # Executive / system overview
        "bangiamdoc": "dashboard:main",
        "banlanhdao": "dashboard:main",
        "tonggiamdoc": "dashboard:main",
        "giamdoc": "dashboard:main",
        "bod": "dashboard:main",
        # Operations
        "nghiepvu": "operations:dashboard_vanhanh",
        "phongnghiepvu": "operations:dashboard_vanhanh",
        "vanhanh": "operations:dashboard_vanhanh",
        "dieuhanh": "operations:dashboard_vanhanh",
        "quanlyvung": "operations:dashboard_vanhanh",
        "chihuytruong": "operations:dashboard_vanhanh",
        "doitruong": "operations:dashboard_vanhanh",
        # Accounting
        "ketoan": "accounting:dashboard",
        "taichinhketoan": "accounting:dashboard",
        "ketoantaichinh": "accounting:dashboard",
        "phongketoan": "accounting:dashboard",
        "phongtaichinhketoan": "accounting:dashboard",
        "phongketoantaichinh": "accounting:dashboard",
        # Inventory
        "kho": "inventory:dashboard",
        "khovattu": "inventory:dashboard",
        "vattu": "inventory:dashboard",
        "phongkho": "inventory:dashboard",
        "phongkhovattu": "inventory:dashboard",
        # Inspection / training
        "thanhtra": "inspection:dashboard",
        "thanhtradaotao": "inspection:dashboard",
        "phongthanhtradaotao": "inspection:dashboard",
        "daotao": "inspection:dashboard",
        # Sales / CRM
        "kinhdoanh": "clients:dashboard_crm",
        "phongkinhdoanh": "clients:dashboard_crm",
        "phongkinhdoanhcskh": "clients:dashboard_crm",
        "sales": "clients:dashboard_crm",
        "crm": "clients:dashboard_crm",
        "cskh": "clients:dashboard_crm",
        # HR
        "nhansu": "users:dashboard",
        "hanhchinhnhansu": "users:dashboard",
        "phonghanhchinhnhansu": "users:dashboard",
        "hcns": "users:dashboard",
        "hcnsdaotao": "users:dashboard",
        "phongnhansu": "users:dashboard",
        # Guard/mobile
        "baove": "operations:mobile_dashboard",
        "nhanvienbaove": "operations:mobile_dashboard",
        "guard": "operations:mobile_dashboard",
        "securityguard": "operations:mobile_dashboard",
    }

    # Conservative keyword aliases for real-world labels with prefixes/suffixes.
    # Order matters: more specific office departments are evaluated before generic
    # words such as "dao tao" or "bao ve".
    KEYWORD_ROUTE_ALIASES = (
        (("bangiamdoc", "banlanhdao", "tonggiamdoc", "bod"), "dashboard:main"),
        (("ketoan", "taichinh"), "accounting:dashboard"),
        (("hanhchinhnhansu", "nhansu", "hcns"), "users:dashboard"),
        (("kinhdoanh", "cskh", "crm", "sales"), "clients:dashboard_crm"),
        (("khovattu", "vattu", "thukho", "kho"), "inventory:dashboard"),
        (("thanhtra", "kiemtra", "daotao"), "inspection:dashboard"),
        (("nghiepvu", "vanhanh", "dieuhanh", "quanlyvung", "doitruong", "chihuytruong"), "operations:dashboard_vanhanh"),
        (("nhanvienbaove", "baove", "securityguard", "guard"), "operations:mobile_dashboard"),
    )

    ROLE_ROUTE_NAMES = (
        ("ban_giam_doc", "dashboard:main"),
        ("ke_toan", "accounting:dashboard"),
        ("thu_kho", "inventory:dashboard"),
        ("nhan_su", "users:dashboard"),
        ("nghiep_vu", "operations:dashboard_vanhanh"),
        ("quan_ly_vung", "operations:dashboard_vanhanh"),
        ("doi_truong", "operations:dashboard_vanhanh"),
        ("nhan_vien_kinh_doanh", "clients:dashboard_crm"),
        ("nhan_vien_bao_ve", "operations:mobile_dashboard"),
    )

    ROUTE_CANONICAL_ALIASES = {
        "operations:dashboard_trinh_chieu": "operations:dashboard_vanhanh",
        "operations:dashboard_xep_lich": "operations:dashboard_vanhanh",
        "operations:mobile_dashboard_redirect": "operations:mobile_dashboard",
    }

    DASHBOARD_ACCESS_RULES = {
        "dashboard:main": DashboardAccessRule(
            route_name="dashboard:main",
            role_names=("ban_giam_doc",),
            alias_keys=("bangiamdoc", "banlanhdao", "tonggiamdoc", "giamdoc", "bod"),
        ),
        "operations:dashboard_vanhanh": DashboardAccessRule(
            route_name="operations:dashboard_vanhanh",
            role_names=("ban_giam_doc", "nghiep_vu", "quan_ly_vung", "doi_truong"),
            alias_keys=("nghiepvu", "phongnghiepvu", "vanhanh", "dieuhanh", "quanlyvung", "chihuytruong", "doitruong"),
        ),
        "accounting:dashboard": DashboardAccessRule(
            route_name="accounting:dashboard",
            role_names=("ban_giam_doc", "ke_toan"),
            alias_keys=("ketoan", "taichinhketoan", "ketoantaichinh", "phongketoan", "phongtaichinhketoan", "phongketoantaichinh"),
        ),
        "inventory:dashboard": DashboardAccessRule(
            route_name="inventory:dashboard",
            role_names=("ban_giam_doc", "thu_kho"),
            alias_keys=("kho", "khovattu", "vattu", "phongkho", "phongkhovattu"),
        ),
        "inspection:dashboard": DashboardAccessRule(
            route_name="inspection:dashboard",
            role_names=("ban_giam_doc", "quan_ly_vung", "doi_truong", "thanh_tra"),
            alias_keys=("thanhtra", "thanhtradaotao", "phongthanhtradaotao", "daotao"),
        ),
        "clients:dashboard_crm": DashboardAccessRule(
            route_name="clients:dashboard_crm",
            role_names=("ban_giam_doc", "nhan_vien_kinh_doanh"),
            alias_keys=("kinhdoanh", "phongkinhdoanh", "phongkinhdoanhcskh", "sales", "crm", "cskh"),
        ),
        "users:dashboard": DashboardAccessRule(
            route_name="users:dashboard",
            role_names=("ban_giam_doc", "nhan_su"),
            alias_keys=("nhansu", "hanhchinhnhansu", "phonghanhchinhnhansu", "hcns", "hcnsdaotao", "phongnhansu"),
        ),
        "reports:report_dashboard": DashboardAccessRule(
            route_name="reports:report_dashboard",
            role_names=("ban_giam_doc", "ke_toan", "quan_ly_vung", "doi_truong", "nhan_su", "thanh_tra"),
            alias_keys=("bangiamdoc", "ketoan", "nghiepvu", "vanhanh", "nhansu", "thanhtra"),
        ),
        "operations:mobile_dashboard": DashboardAccessRule(
            route_name="operations:mobile_dashboard",
            role_names=("nhan_vien_bao_ve",),
            alias_keys=("baove", "nhanvienbaove"),
        ),
    }

    @classmethod
    def resolve(cls, user):
        return cls.resolve_decision(user).route_name

    @classmethod
    def resolve_decision(cls, user):
        if user.is_superuser:
            return DashboardRouteDecision(cls.ADMIN_ROUTE, True, "superuser")

        role_route = cls._resolve_from_roles(user)
        if role_route:
            return DashboardRouteDecision(role_route, True, "rolepermissions")

        profile_route = cls._resolve_from_employee_profile(user)
        if profile_route:
            return DashboardRouteDecision(profile_route, True, "employee-profile")

        group_route = cls._resolve_from_groups(user)
        if group_route:
            return DashboardRouteDecision(group_route, True, "django-group")

        return DashboardRouteDecision(cls.DEFAULT_ROUTE, False, "fallback")

    @classmethod
    def canonical_route(cls, route_name):
        return cls.ROUTE_CANONICAL_ALIASES.get(route_name, route_name)

    @classmethod
    def user_can_access(cls, user, route_name):
        if not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser:
            return True

        route_name = cls.canonical_route(route_name)
        rule = cls.DASHBOARD_ACCESS_RULES.get(route_name)
        if not rule:
            return False
        if rule.allow_any_authenticated:
            return True

        decision = cls.resolve_decision(user)
        if decision.matched and cls.canonical_route(decision.route_name) == route_name:
            return True

        if cls._has_any_role(user, rule.role_names):
            return True

        profile_routes = cls._routes_from_employee_profile(user)
        group_routes = cls._routes_from_groups(user)
        if route_name in profile_routes or route_name in group_routes:
            return True

        return False

    @classmethod
    def user_can_access_admin_console(cls, user):
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
            return False
        if user.is_superuser:
            return True
        if not getattr(user, "is_staff", False):
            return False

        # Technical console is reserved for technical-admin style accounts.
        # Any user that already resolves to a business workspace must use that
        # workspace instead of staying inside /admin/.
        decision = cls.resolve_decision(user)
        return not decision.matched

    @classmethod
    def user_can_access_shell_route(cls, user, route_name):
        """Return whether a user should see a shell navigation route as active.

        This keeps the sidebar aligned with the same permission SSOT used by
        post-login routing, while still allowing a few non-dashboard shell
        surfaces to express access explicitly.
        """
        if not getattr(user, "is_authenticated", False):
            return False

        route_name = cls.canonical_route(route_name)
        if route_name in cls.DASHBOARD_ACCESS_RULES:
            return cls.user_can_access(user, route_name)

        if route_name == "operations:mobile_tuan_tra_list":
            return bool(
                getattr(user, "is_superuser", False)
                or has_permission(user, "thuc_hien_tuan_tra_bao_ve")
            )

        if route_name == "workflow:dashboard":
            if getattr(user, "is_superuser", False):
                return True
            try:
                return getattr(user, "nhan_vien", None) is not None
            except Exception:
                return False

        return False

    @staticmethod
    def shell_access_denied_message(route_name):
        return "Bạn không có quyền truy cập khu vực này. Vui lòng liên hệ với Admin."

    @classmethod
    def enforce_access(cls, user, route_name):
        if cls.user_can_access(user, route_name):
            return
        raise PermissionDenied("Bạn không có quyền truy cập dashboard này.")

    @classmethod
    def _has_any_role(cls, user, role_names):
        return any(has_role(user, role_name) for role_name in role_names)

    @classmethod
    def _routes_from_employee_profile(cls, user):
        nhan_vien = getattr(user, "nhan_vien", None)
        if not nhan_vien:
            return set()

        routes = set()
        for attr_name in ("phong_ban", "chuc_danh"):
            obj = getattr(nhan_vien, attr_name, None)
            if not obj:
                continue
            label = getattr(obj, "ten_phong_ban", "") or getattr(obj, "ten_chuc_danh", "")
            route = cls._resolve_alias(label)
            if route:
                routes.add(cls.canonical_route(route))
        return routes

    @classmethod
    def _routes_from_groups(cls, user):
        routes = set()
        for name in user.groups.values_list("name", flat=True):
            route = cls._resolve_alias(name)
            if route:
                routes.add(cls.canonical_route(route))
        return routes

    @classmethod
    def _pick_preferred_route(cls, routes):
        canonical_routes = {cls.canonical_route(route_name) for route_name in routes if route_name}
        if not canonical_routes:
            return None
        for route_name in cls.ROUTE_PRIORITY:
            if route_name in canonical_routes:
                return route_name
        return sorted(canonical_routes)[0]

    @classmethod
    def _resolve_from_roles(cls, user):
        for role_name, route_name in cls.ROLE_ROUTE_NAMES:
            if has_role(user, role_name):
                return route_name
        return None

    @classmethod
    def _resolve_from_employee_profile(cls, user):
        nhan_vien = getattr(user, "nhan_vien", None)
        if not nhan_vien:
            return None

        chuc_danh = getattr(nhan_vien, "chuc_danh", None)
        phong_ban = getattr(nhan_vien, "phong_ban", None)
        return cls._pick_preferred_route(
            (
                cls._resolve_alias(getattr(chuc_danh, "ten_chuc_danh", "")),
                cls._resolve_alias(getattr(phong_ban, "ten_phong_ban", "")),
            )
        )

    @classmethod
    def _resolve_from_groups(cls, user):
        return cls._pick_preferred_route(
            cls._resolve_alias(name)
            for name in user.groups.values_list("name", flat=True)
        )

    @classmethod
    def _resolve_alias(cls, value):
        key = cls._normalize_key(value)
        if not key:
            return None

        route = cls.WORKSPACE_ROUTE_ALIASES.get(key)
        if route:
            return route

        for keywords, route_name in cls.KEYWORD_ROUTE_ALIASES:
            if any(keyword in key for keyword in keywords):
                return route_name
        return None

    @staticmethod
    def _normalize_key(value):
        # NFKD removes combining accents but does not convert Vietnamese đ/Đ.
        value = (value or "").replace("Đ", "D").replace("đ", "d")
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return "".join(ch for ch in value.lower() if ch.isalnum())


def dashboard_access_required(route_name):
    """Decorator for dashboard views; DashboardRouter is the permission SSOT."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            DashboardRouter.enforce_access(request.user, route_name)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
