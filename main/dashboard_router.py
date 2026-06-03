from dataclasses import dataclass

from rolepermissions.checkers import has_role


@dataclass(frozen=True)
class DashboardRouteDecision:
    route_name: str
    matched: bool
    source: str


class DashboardRouter:
    ADMIN_ROUTE = "admin:index"
    DEFAULT_ROUTE = "operations:mobile_dashboard"

    GROUP_ROUTE_NAMES = {
        "bangiamdoc": "dashboard:main",
        "nghiepvu": "operations:dashboard_vanhanh",
        "vanhanh": "operations:dashboard_vanhanh",
        "ketoan": "accounting:dashboard",
        "kho": "inventory:dashboard",
        "thanhtra": "inspection:dashboard",
        "baove": "operations:mobile_dashboard",
        "kinhdoanh": "clients:dashboard_crm",
        "nhansu": "users:dashboard",
        "quanlyvung": "operations:dashboard_vanhanh",
        "doitruong": "operations:dashboard_vanhanh",
    }

    ROLE_ROUTE_NAMES = (
        ("ban_giam_doc", "dashboard:main"),
        ("ke_toan", "accounting:dashboard"),
        ("quan_ly_vung", "operations:dashboard_vanhanh"),
        ("doi_truong", "operations:dashboard_vanhanh"),
        ("nhan_vien_kinh_doanh", "clients:dashboard_crm"),
        ("nhan_vien_bao_ve", "operations:mobile_dashboard"),
    )

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

        group_route = cls._resolve_from_groups(user)
        if group_route:
            return DashboardRouteDecision(group_route, True, "django-group")

        return DashboardRouteDecision(cls.DEFAULT_ROUTE, False, "fallback")

    @classmethod
    def _resolve_from_roles(cls, user):
        for role_name, route_name in cls.ROLE_ROUTE_NAMES:
            if has_role(user, role_name):
                return route_name
        return None

    @classmethod
    def _resolve_from_groups(cls, user):
        normalized_groups = {
            cls._normalize_group_name(name)
            for name in user.groups.values_list("name", flat=True)
        }
        for group_name, route_name in cls.GROUP_ROUTE_NAMES.items():
            if group_name in normalized_groups:
                return route_name
        return None

    @staticmethod
    def _normalize_group_name(value):
        return "".join(ch for ch in value.lower() if ch.isalnum())
