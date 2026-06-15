# -*- coding: utf-8 -*-
"""Operations-first UX helpers for SCMD Pro Django Admin.

This module builds computed UI context only. It intentionally does not create
models, migrations, permissions or business workflows. Every queryset is scoped
through the existing policies/managers where available, then exposed as compact
work-queue items for server-rendered admin templates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import md5
import logging
from datetime import timedelta
from typing import Any, Iterable
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q, QuerySet
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from main.dashboard_router import DashboardRouter

logger = logging.getLogger(__name__)
ADMIN_OPERATIONS_UX_CACHE_TTL = 30


@dataclass(frozen=True)
class OperationsSummaryCard:
    """Small KPI card displayed above admin list/dashboard content."""

    key: str
    label: str
    value: int | str
    note: str
    tone: str = "neutral"
    url: str = "#"

    def as_template_context(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkQueueItem:
    """One actionable operations queue entry.

    ``count`` remains numeric for sorting and tests. ``display_count`` lets the
    UI be honest for bounded counts such as ``999+`` or source warnings without
    forcing heavy exact counts on large tables.
    """

    key: str
    label: str
    count: int
    note: str
    url: str
    tone: str = "neutral"
    priority: int = 100
    cta: str = "Mở danh sách"
    display_count: str = ""
    source_warning: bool = False
    next_actions: list[dict[str, str]] = field(default_factory=list)

    def as_template_context(self) -> dict[str, Any]:
        data = asdict(self)
        data["display_count"] = self.display_count or ("999+" if self.count > 999 else str(self.count))
        # V9 governance: never auto-generate a generic ``generic export flag`` action.
        # Next actions must be explicitly supplied by the provider only when a
        # real admin endpoint exists, for example ``export/`` or ``export-csv/``.
        data["next_actions"] = list(self.next_actions or [])
        return data


class AdminOperationsUXProvider:
    """Build role-aware admin UX context without changing authorization.

    Dashboard role/category detection is derived from ``DashboardRouter`` so the
    admin homepage follows the same workspace routing SSOT used after login. The
    provider only chooses which already-visible queues/cards to show first; it
    does not grant permissions, widen querysets, or change business rules.
    """

    # Category keys used internally by this provider. They are derived from
    # DashboardRouter route decisions and role aliases, not used for auth.
    EXECUTIVE_KEYS = {"scope:executive", "scope:technical", "route:dashboard:main", "superuser"}
    HR_KEYS = {"scope:hr", "route:users:dashboard", "nhan_su"}
    OPERATIONS_KEYS = {
        "scope:operations",
        "scope:inspection",
        "route:operations:dashboard_vanhanh",
        "route:inspection:dashboard",
        "route:operations:mobile_dashboard",
        "quan_ly_vung",
        "doi_truong",
        "thanh_tra",
        "nhan_vien_bao_ve",
    }
    ACCOUNTING_KEYS = {"scope:accounting", "route:accounting:dashboard", "ke_toan"}
    INVENTORY_KEYS = {"scope:inventory", "route:inventory:dashboard"}
    CLIENT_KEYS = {"scope:clients", "route:clients:dashboard_crm", "nhan_vien_kinh_doanh"}

    ROUTE_CATEGORY_KEYS = {
        "dashboard:main": {"scope:executive"},
        "users:dashboard": {"scope:hr"},
        "operations:dashboard_vanhanh": {"scope:operations"},
        "operations:mobile_dashboard": {"scope:operations"},
        "inspection:dashboard": {"scope:inspection"},
        "accounting:dashboard": {"scope:accounting"},
        "inventory:dashboard": {"scope:inventory"},
        "clients:dashboard_crm": {"scope:clients"},
        "reports:report_dashboard": {"scope:reports"},
        "admin:index": {"scope:technical", "scope:executive"},
    }

    @classmethod
    def build(cls, user: Any) -> dict[str, Any]:
        role_keys = cls.role_keys_for_user(user)
        cache_key = cls._cache_key_for_user(user, role_keys)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        work_queue_items = cls.work_queue_for_user(user, role_keys)
        dashboard_cards = cls.dashboard_cards_for_user(user, role_keys, work_queue_items)
        payload = {
            "role_keys": sorted(role_keys),
            "role_summary": cls.role_summary(role_keys),
            "home_header": cls.home_header_for_user(role_keys),
            "dashboard_cards": [card.as_template_context() for card in dashboard_cards],
            "work_queue_items": [item.as_template_context() for item in work_queue_items],
            "has_work_queue": bool(work_queue_items),
        }
        cache.set(cache_key, payload, ADMIN_OPERATIONS_UX_CACHE_TTL)
        return payload

    @classmethod
    def _cache_key_for_user(cls, user: Any, role_keys: set[str]) -> str:
        role_fingerprint = md5("|".join(sorted(role_keys)).encode("utf-8")).hexdigest()[:16]
        org_id = getattr(settings, "SCMD_ORGANIZATION_ID", "org")
        return f"main:admin_operations_ux:org:{org_id}:user:{getattr(user, 'pk', 'anon')}:{role_fingerprint}"

    @classmethod
    def role_keys_for_user(cls, user: Any) -> set[str]:
        keys: set[str] = set()
        if not getattr(user, "is_authenticated", False):
            return keys
        if getattr(user, "is_superuser", False):
            keys.update({"superuser", "scope:technical", "scope:executive"})

        cls._add_dashboard_routes(keys, cls._routes_for_user(user))
        keys.update(cls._rolepermission_keys(user))
        keys.update(cls._profile_and_group_alias_keys(user))
        return {key for key in keys if key}

    @classmethod
    def role_summary(cls, role_keys: set[str]) -> str:
        if role_keys & cls.HR_KEYS:
            return "Ưu tiên hồ sơ nhân sự, tài khoản đăng nhập và dữ liệu liên hệ cần hoàn thiện."
        if role_keys & cls.OPERATIONS_KEYS:
            return "Ưu tiên ca trực, check-in, sự cố và quân số tại mục tiêu."
        if role_keys & cls.ACCOUNTING_KEYS:
            return "Ưu tiên dữ liệu đối soát, lương và chứng từ cần xử lý."
        if role_keys & cls.INVENTORY_KEYS:
            return "Ưu tiên tồn kho, cấp phát và vật tư dưới ngưỡng cảnh báo."
        if role_keys & cls.CLIENT_KEYS:
            return "Ưu tiên khách hàng, hợp đồng và điểm cần theo dõi trong phạm vi phụ trách."
        if role_keys & cls.EXECUTIVE_KEYS:
            return "Ưu tiên tổng quan việc tồn đọng, sự cố, nhân sự và điểm nghẽn vận hành."
        return "Ưu tiên các việc có thể xử lý theo phạm vi quyền hiện tại."

    @classmethod
    def home_header_for_user(cls, role_keys: set[str]) -> dict[str, Any]:
        title = "Bàn làm việc vận hành"
        if role_keys & cls.HR_KEYS:
            title = "Bàn làm việc nhân sự"
        elif role_keys & cls.OPERATIONS_KEYS:
            title = "Bàn làm việc điều hành"
        elif role_keys & cls.ACCOUNTING_KEYS:
            title = "Bàn làm việc đối soát"
        elif role_keys & cls.INVENTORY_KEYS:
            title = "Bàn làm việc kho"
        elif role_keys & cls.EXECUTIVE_KEYS:
            title = "Bàn làm việc quản trị"

        actions = [
            {
                "label": "Nhân sự",
                "url": cls._safe_reverse("admin:users_nhanvien_changelist"),
                "icon": "fas fa-id-card",
                "primary": bool(role_keys & cls.HR_KEYS),
            },
            {
                "label": "Ca trực",
                "url": cls._safe_reverse("admin:operations_phancongcatruc_changelist"),
                "icon": "fas fa-calendar-check",
                "primary": bool(role_keys & cls.OPERATIONS_KEYS),
            },
            {
                "label": "Sự cố",
                "url": cls._safe_reverse("admin:operations_baocaosuco_changelist"),
                "icon": "fas fa-triangle-exclamation",
                "primary": False,
            },
        ]
        if not any(action["primary"] for action in actions):
            actions[0]["primary"] = True

        return {
            "kicker": "SCMD Pro · Bàn làm việc vận hành",
            "title": title,
            "subtitle": cls.role_summary(role_keys),
            "actions": [action for action in actions if action["url"] != "#"],
        }

    @classmethod
    def dashboard_cards_for_user(
        cls,
        user: Any,
        role_keys: set[str],
        work_queue_items: Iterable[WorkQueueItem],
    ) -> list[OperationsSummaryCard]:
        items = list(work_queue_items)
        urgent_count = sum(item.count for item in items if item.tone in {"danger", "warning"})
        cards = [
            OperationsSummaryCard(
                key="pending_work",
                label="Việc cần xử lý",
                value=urgent_count,
                note="Tổng các nhóm việc đang cần rà soát theo quyền hiện tại.",
                tone="warning" if urgent_count else "success",
            )
        ]

        if role_keys & (cls.EXECUTIVE_KEYS | cls.HR_KEYS):
            cards.extend(cls._staff_health_cards(user))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.OPERATIONS_KEYS):
            cards.extend(cls._operations_health_cards(user))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.INVENTORY_KEYS):
            cards.extend(cls._inventory_health_cards())

        return cards[:5]

    @classmethod
    def work_queue_for_user(cls, user: Any, role_keys: set[str]) -> list[WorkQueueItem]:
        items: list[WorkQueueItem] = []
        if role_keys & (cls.EXECUTIVE_KEYS | cls.HR_KEYS):
            items.extend(cls._safe_queue_source(role_keys, "staff", "dữ liệu nhân sự", lambda: cls._staff_work_items(user)))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.OPERATIONS_KEYS):
            items.extend(cls._safe_queue_source(role_keys, "operations", "dữ liệu ca trực/chấm công", lambda: cls._operations_work_items(user)))
            items.extend(cls._safe_queue_source(role_keys, "patrol", "dữ liệu tuần tra", lambda: cls._patrol_work_items(user)))
            items.extend(cls._safe_queue_source(role_keys, "contracts", "dữ liệu hợp đồng", lambda: cls._contract_work_items(user)))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.OPERATIONS_KEYS | cls.HR_KEYS | cls.ACCOUNTING_KEYS):
            items.extend(cls._safe_queue_source(role_keys, "workflow", "dữ liệu trình duyệt/công việc", lambda: cls._workflow_work_items(user)))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.ACCOUNTING_KEYS):
            items.extend(cls._safe_queue_source(role_keys, "payroll", "dữ liệu lương/đối soát", cls._payroll_work_items))
        if role_keys & (cls.EXECUTIVE_KEYS | cls.INVENTORY_KEYS):
            items.extend(cls._safe_queue_source(role_keys, "inventory", "dữ liệu kho/cấp phát", cls._inventory_work_items))

        actionable = [item for item in items if item.count > 0 or item.source_warning]
        if not actionable:
            actionable.append(
                WorkQueueItem(
                    key="no_pending_work",
                    label="Chưa có việc nổi bật",
                    count=0,
                    note="Không ghi nhận nhóm việc cần xử lý ngay theo phạm vi hiện tại.",
                    url=cls._safe_reverse("admin:index"),
                    tone="success",
                    priority=999,
                    cta="Xem danh mục",
                )
            )
        return sorted(actionable, key=lambda item: (item.priority, -item.count))[:6]

    @classmethod
    def _safe_queue_source(cls, role_keys: set[str], source_key: str, source_label: str, loader):
        try:
            return loader()
        except Exception as exc:
            logger.warning("Operations UX work queue source unavailable: %s", source_key, exc_info=True)
            if cls._should_show_source_warnings(role_keys):
                return [
                    WorkQueueItem(
                        key=f"source_unavailable:{source_key}",
                        label=f"Không tải được {source_label}",
                        count=0,
                        display_count="!",
                        note="Nguồn dữ liệu này chưa sẵn sàng hoặc query lỗi. Không coi là không có việc; cần kiểm tra log/runtime.",
                        url=cls._safe_reverse("admin:index"),
                        tone="warning",
                        priority=7,
                        cta="Kiểm tra",
                        source_warning=True,
                    )
                ]
            return [
                WorkQueueItem(
                    key=f"source_updating:{source_key}",
                    label=f"{source_label.capitalize()} đang cập nhật",
                    count=0,
                    display_count="…",
                    note="Một số dữ liệu vận hành chưa tải xong. Vui lòng tải lại sau nếu số liệu không khớp thực tế.",
                    url=cls._safe_reverse("admin:index"),
                    tone="neutral",
                    priority=90,
                    cta="Tải lại",
                    source_warning=True,
                )
            ]

    @classmethod
    def _should_show_source_warnings(cls, role_keys: set[str]) -> bool:
        return bool(role_keys & {"superuser", "scope:technical"})

    @classmethod
    def _routes_for_user(cls, user: Any) -> set[str]:
        routes: set[str] = set()
        try:
            decision = DashboardRouter.resolve_decision(user)
            if decision and decision.route_name:
                routes.add(DashboardRouter.canonical_route(decision.route_name))
        except Exception:
            pass

        try:
            routes.update(DashboardRouter._routes_from_employee_profile(user))
        except Exception:
            pass
        try:
            routes.update(DashboardRouter._routes_from_groups(user))
        except Exception:
            pass
        try:
            for role_name, route_name in DashboardRouter.ROLE_ROUTE_NAMES:
                if DashboardRouter._has_any_role(user, (role_name,)):
                    routes.add(DashboardRouter.canonical_route(route_name))
        except Exception:
            pass
        return routes

    @classmethod
    def _add_dashboard_routes(cls, keys: set[str], routes: Iterable[str]) -> None:
        for route_name in routes:
            canonical = DashboardRouter.canonical_route(route_name)
            keys.add(f"route:{canonical}")
            keys.update(cls.ROUTE_CATEGORY_KEYS.get(canonical, set()))

    @classmethod
    def _rolepermission_keys(cls, user: Any) -> set[str]:
        """Resolve rolepermission aliases from DashboardRouter rules.

        V2 only looked at ``ROLE_ROUTE_NAMES``. That missed roles that are
        allowed by ``DASHBOARD_ACCESS_RULES`` but are not first-choice login
        routes, for example ``nhan_su`` and ``thanh_tra``. V3 treats the
        router rules as the alias SSOT, then adds category keys for matching
        routes. This is UI prioritization only; authorization remains in the
        existing policies/router.
        """
        keys: set[str] = set()
        try:
            for route_name, rule in DashboardRouter.DASHBOARD_ACCESS_RULES.items():
                for role_name in getattr(rule, "role_names", ()):
                    if DashboardRouter._has_any_role(user, (role_name,)):
                        keys.add(role_name)
                        cls._add_dashboard_routes(keys, [route_name])
        except Exception:
            pass
        return keys

    @classmethod
    def _profile_and_group_alias_keys(cls, user: Any) -> set[str]:
        keys: set[str] = set()
        try:
            for name in user.groups.values_list("name", flat=True):
                key = DashboardRouter._normalize_key(name)
                if key:
                    keys.add(f"alias:{key}")
        except Exception:
            pass
        try:
            profile = user.nhan_vien
            for attr_name in ("phong_ban", "chuc_danh"):
                obj = getattr(profile, attr_name, None)
                label = getattr(obj, "ten_phong_ban", "") or getattr(obj, "ten_chuc_danh", "")
                key = DashboardRouter._normalize_key(label)
                if key:
                    keys.add(f"alias:{key}")
        except Exception:
            pass
        return keys

    @classmethod
    def _staff_queryset(cls, user: Any):
        from users.access_policies import StaffVisibilityPolicy

        return StaffVisibilityPolicy.visible_staff(user)

    @classmethod
    def _staff_current_assignment_ids(cls, staff_qs: QuerySet):
        from users.models import LichSuCongTac

        return (
            LichSuCongTac.objects.filter(
                nhan_vien__in=staff_qs,
                muc_tieu__isnull=False,
                ngay_ket_thuc__isnull=True,
            )
            .values_list("nhan_vien_id", flat=True)
            .distinct()
        )

    @classmethod
    def _staff_counts(cls, user: Any) -> dict[str, int]:
        staff_qs = cls._staff_queryset(user)
        assigned_ids = cls._staff_current_assignment_ids(staff_qs)
        return {
            "total": cls._bounded_count(staff_qs),
            "missing_user": cls._bounded_count(staff_qs.filter(user__isnull=True)),
            "missing_phone": cls._bounded_count(staff_qs.filter(Q(sdt_chinh__isnull=True) | Q(sdt_chinh=""))),
            "missing_email": cls._bounded_count(staff_qs.filter(Q(email__isnull=True) | Q(email=""))),
            "missing_site": cls._bounded_count(staff_qs.exclude(pk__in=assigned_ids)),
            "with_device_token": cls._bounded_count(staff_qs.exclude(fcm_token__isnull=True).exclude(fcm_token="")),
        }

    @classmethod
    def _staff_health_cards(cls, user: Any) -> list[OperationsSummaryCard]:
        try:
            counts = cls._staff_counts(user)
        except Exception:
            return []
        base_url = cls._safe_reverse("admin:users_nhanvien_changelist")
        return [
            OperationsSummaryCard(
                key="staff_total",
                label="Nhân viên trong phạm vi",
                value=counts["total"],
                note="Theo StaffVisibilityPolicy hiện tại.",
                tone="neutral",
                url=base_url,
            ),
            OperationsSummaryCard(
                key="staff_missing_site",
                label="Chưa phân mục tiêu",
                value=counts["missing_site"],
                note="Cần rà soát phân bổ mục tiêu hiện hành.",
                tone="warning" if counts["missing_site"] else "success",
                url=cls._with_query(base_url, {"staff_ops": "missing_site"}),
            ),
        ]

    @classmethod
    def _staff_work_items(cls, user: Any) -> list[WorkQueueItem]:
        counts = cls._staff_counts(user)
        base_url = cls._safe_reverse("admin:users_nhanvien_changelist")
        return [
            WorkQueueItem(
                key="staff_missing_site",
                label="Nhân viên chưa phân mục tiêu",
                count=counts["missing_site"],
                note="Cần bổ sung mục tiêu hiện hành để tránh thiếu dữ liệu điều phối và đối soát.",
                url=cls._with_query(base_url, {"staff_ops": "missing_site"}),
                next_actions=cls._export_next_action(cls._with_query(base_url, {"staff_ops": "missing_site"}), child_path="export"),
                tone="warning",
                priority=20,
            ),
            WorkQueueItem(
                key="staff_missing_phone",
                label="Nhân viên thiếu số điện thoại",
                count=counts["missing_phone"],
                note="Ảnh hưởng liên lạc khẩn cấp và xác thực vận hành.",
                url=cls._with_query(base_url, {"staff_ops": "missing_phone"}),
                next_actions=cls._export_next_action(cls._with_query(base_url, {"staff_ops": "missing_phone"}), child_path="export"),
                tone="warning",
                priority=30,
            ),
            WorkQueueItem(
                key="staff_missing_user",
                label="Nhân viên chưa có tài khoản",
                count=counts["missing_user"],
                note="Cần liên kết khi nhân viên dùng app hoặc nhận thông báo.",
                url=cls._with_query(base_url, {"staff_ops": "missing_user"}),
                next_actions=cls._export_next_action(cls._with_query(base_url, {"staff_ops": "missing_user"}), child_path="export"),
                tone="neutral",
                priority=45,
            ),
            WorkQueueItem(
                key="staff_missing_email",
                label="Nhân viên thiếu email",
                count=counts["missing_email"],
                note="Cần hoàn thiện hồ sơ liên hệ khi có quy trình gửi thông tin nội bộ.",
                url=cls._with_query(base_url, {"staff_ops": "missing_email"}),
                next_actions=cls._export_next_action(cls._with_query(base_url, {"staff_ops": "missing_email"}), child_path="export"),
                tone="neutral",
                priority=55,
            ),
        ]

    @classmethod
    def _operations_health_cards(cls, user: Any) -> list[OperationsSummaryCard]:
        try:
            counts = cls._operations_counts(user)
        except Exception:
            return []
        return [
            OperationsSummaryCard(
                key="today_shifts_without_checkin",
                label="Ca chưa check-in",
                value=counts["shifts_without_checkin"],
                note="Ca trực hôm nay chưa có check-in.",
                tone="warning" if counts["shifts_without_checkin"] else "success",
                url=cls._safe_reverse("admin:operations_phancongcatruc_changelist"),
            ),
            OperationsSummaryCard(
                key="open_incidents",
                label="Sự cố đang mở",
                value=counts["open_incidents"],
                note="Sự cố chờ xử lý hoặc đang xử lý.",
                tone="danger" if counts["critical_incidents"] else "warning" if counts["open_incidents"] else "success",
                url=cls._safe_reverse("admin:operations_baocaosuco_changelist"),
            ),
        ]

    @classmethod
    def _operations_counts(cls, user: Any) -> dict[str, int]:
        from operations.access_policies import ShiftVisibilityPolicy
        from operations.models import BaoCaoSuCo, KiemTraQuanSo

        org_id = settings.SCMD_ORGANIZATION_ID
        today = timezone.localdate()
        staff_qs = cls._staff_queryset(user)
        shift_qs = ShiftVisibilityPolicy.visible_shifts(user, date_range=(today, today))
        incident_qs = BaoCaoSuCo.objects.for_tenant(org_id).filter(trang_thai__in=["CHO_XU_LY", "DANG_XU_LY"])

        if not getattr(user, "is_superuser", False):
            incident_qs = incident_qs.filter(
                Q(nhan_vien_bao_cao__in=staff_qs)
                | Q(nhan_vien_co_loi__in=staff_qs)
                | Q(nguoi_xu_ly__in=staff_qs)
                | Q(ca_truc__nhan_vien__in=staff_qs)
            ).distinct()

        alive_qs = KiemTraQuanSo.objects.for_tenant(org_id).filter(ca_truc__in=shift_qs)
        return {
            "today_shifts": cls._bounded_count(shift_qs),
            "shifts_without_checkin": cls._bounded_count(shift_qs.filter(chamcong__thoi_gian_check_in__isnull=True)),
            "attendance_missing_checkout": cls._bounded_count(shift_qs.filter(
                chamcong__thoi_gian_check_in__isnull=False,
                chamcong__thoi_gian_check_out__isnull=True,
            )),
            "alive_pending": cls._bounded_count(alive_qs.filter(trang_thai="PENDING")),
            "alive_missed": cls._bounded_count(alive_qs.filter(trang_thai__in=["MISSED", "LATE"])),
            "open_incidents": cls._bounded_count(incident_qs),
            "critical_incidents": cls._bounded_count(incident_qs.filter(muc_do__in=["CAO", "NGUY_HIEM"])),
        }

    @classmethod
    def _patrol_counts(cls, user: Any) -> dict[str, int]:
        from clients.access_policies import SiteVisibilityPolicy
        from inspection.models import GhiNhanTuanTra, LuotTuanTra

        org_id = settings.SCMD_ORGANIZATION_ID
        today_start = timezone.now() - timedelta(days=1)
        evidence_start = timezone.now() - timedelta(days=7)
        staff_qs = cls._staff_queryset(user)
        patrol_qs = LuotTuanTra.objects.for_tenant(org_id).all()
        evidence_qs = GhiNhanTuanTra.objects.for_tenant(org_id).all()

        if not getattr(user, "is_superuser", False):
            managed_sites = SiteVisibilityPolicy.managed_sites(user)
            patrol_qs = patrol_qs.filter(
                Q(nhan_vien__in=staff_qs) | Q(loai_tuan_tra__muc_tieu__in=managed_sites)
            ).distinct()
            evidence_qs = evidence_qs.filter(
                Q(luot_tuan_tra__nhan_vien__in=staff_qs)
                | Q(luot_tuan_tra__loai_tuan_tra__muc_tieu__in=managed_sites)
            ).distinct()

        return {
            "open_patrols": cls._bounded_count(patrol_qs.filter(trang_thai="DANG_DI")),
            "abandoned_patrols": cls._bounded_count(patrol_qs.filter(trang_thai="BO_DO", thoi_gian_bat_dau__gte=today_start)),
            "patrol_evidence_warnings": cls._bounded_count(evidence_qs.filter(
                ket_qua__in=["CANH_BAO_XA", "MAT_GPS", "GIAN_LAN"],
                thoi_gian_quet__gte=evidence_start,
            )),
        }

    @classmethod
    def _contract_counts(cls, user: Any) -> dict[str, int]:
        from clients.access_policies import SiteVisibilityPolicy
        from clients.models import HopDong

        org_id = settings.SCMD_ORGANIZATION_ID
        today = timezone.localdate()
        soon = today + timedelta(days=30)
        contract_qs = HopDong.objects.for_tenant(org_id).all()
        if not getattr(user, "is_superuser", False):
            managed_sites = SiteVisibilityPolicy.managed_sites(user)
            contract_qs = contract_qs.filter(cac_muc_tieu__in=managed_sites).distinct()

        active_states = ["HIEU_LUC", "SAP_HET_HAN"]
        return {
            "contracts_expiring": cls._bounded_count(contract_qs.filter(
                trang_thai__in=active_states,
                ngay_het_han__gte=today,
                ngay_het_han__lte=soon,
            )),
            "contracts_expired_open": cls._bounded_count(contract_qs.filter(
                trang_thai__in=active_states,
                ngay_het_han__lt=today,
            )),
        }

    @classmethod
    def _payroll_counts(cls) -> dict[str, int]:
        from accounting.models import BangLuongThang

        org_id = settings.SCMD_ORGANIZATION_ID
        payroll_qs = BangLuongThang.objects.for_tenant(org_id)
        return {
            "payroll_open": cls._bounded_count(payroll_qs.exclude(
                trang_thai__in=[BangLuongThang.TrangThai.LOCKED, BangLuongThang.TrangThai.PAID]
            ))
        }

    @classmethod
    def _operations_work_items(cls, user: Any) -> list[WorkQueueItem]:
        counts = cls._operations_counts(user)
        return [
            WorkQueueItem(
                key="critical_incidents",
                label="Sự cố nghiêm trọng đang mở",
                count=counts["critical_incidents"],
                note="Ưu tiên cập nhật trạng thái, người xử lý và bằng chứng liên quan.",
                url=cls._with_query(cls._safe_reverse("admin:operations_baocaosuco_changelist"), {"incident_ops": "high_risk"}),
                tone="danger",
                priority=5,
            ),
            WorkQueueItem(
                key="alive_pending",
                label="Alive check đang chờ phản hồi",
                count=counts["alive_pending"],
                note="Cần theo dõi phản hồi quân số trong ca để phát hiện bỏ vị trí hoặc mất liên lạc.",
                url=cls._with_query(cls._safe_reverse("admin:operations_kiemtraquanso_changelist"), {"alive_status": "pending"}),
                tone="warning",
                priority=8,
            ),
            WorkQueueItem(
                key="alive_missed",
                label="Alive check trễ hoặc bỏ lỡ",
                count=counts["alive_missed"],
                note="Cần rà soát ca trực, thiết bị và biên bản xác minh nếu có.",
                url=cls._with_query(cls._safe_reverse("admin:operations_kiemtraquanso_changelist"), {"alive_status": "missed"}),
                tone="danger",
                priority=9,
            ),
            WorkQueueItem(
                key="shifts_without_checkin",
                label="Ca hôm nay chưa check-in",
                count=counts["shifts_without_checkin"],
                note="Rà soát điều phối, thiết bị hoặc xác nhận có mặt tại chốt.",
                url=cls._with_query(cls._safe_reverse("admin:operations_phancongcatruc_changelist"), {"assignment_quality": "missing_checkin_today"}),
                tone="warning",
                priority=10,
            ),
            WorkQueueItem(
                key="attendance_missing_checkout",
                label="Ca đã check-in chưa check-out",
                count=counts["attendance_missing_checkout"],
                note="Cần hoàn tất dữ liệu chấm công để tránh nghẽn đối soát và tính lương.",
                url=cls._with_query(cls._safe_reverse("admin:operations_chamcong_changelist"), {"attendance_ops": "missing_checkout"}),
                tone="warning",
                priority=12,
            ),
            WorkQueueItem(
                key="open_incidents",
                label="Sự cố chờ xử lý",
                count=counts["open_incidents"],
                note="Bao gồm hồ sơ chờ xử lý hoặc đang xử lý.",
                url=cls._with_query(cls._safe_reverse("admin:operations_baocaosuco_changelist"), {"incident_ops": "open"}),
                tone="warning",
                priority=15,
            ),
        ]

    @classmethod
    def _patrol_work_items(cls, user: Any) -> list[WorkQueueItem]:
        counts = cls._patrol_counts(user)
        return [
            WorkQueueItem(
                key="open_patrols",
                label="Lượt tuần tra đang thực hiện",
                count=counts["open_patrols"],
                note="Theo dõi các phiên tuần tra chưa kết thúc để kịp xử lý khi quá thời gian.",
                url=cls._with_query(cls._safe_reverse("admin:inspection_luottuantra_changelist"), {"ops": "active"}),
                tone="neutral",
                priority=18,
            ),
            WorkQueueItem(
                key="abandoned_patrols",
                label="Lượt tuần tra bỏ dở gần đây",
                count=counts["abandoned_patrols"],
                note="Cần rà soát nguyên nhân bỏ dở và bằng chứng tại các checkpoint.",
                url=cls._with_query(cls._safe_reverse("admin:inspection_luottuantra_changelist"), {"ops": "abandoned"}),
                tone="warning",
                priority=19,
            ),
            WorkQueueItem(
                key="patrol_evidence_warnings",
                label="Bằng chứng tuần tra cần kiểm tra",
                count=counts["patrol_evidence_warnings"],
                note="GPS xa, mất GPS hoặc nghi vấn gian lận trong 7 ngày gần đây.",
                url=cls._with_query(cls._safe_reverse("admin:inspection_ghinhantuantra_changelist"), {"scan_ops": "warning"}),
                tone="warning",
                priority=22,
            ),
        ]

    @classmethod
    def _contract_work_items(cls, user: Any) -> list[WorkQueueItem]:
        counts = cls._contract_counts(user)
        return [
            WorkQueueItem(
                key="contracts_expiring",
                label="Hợp đồng sắp hết hạn",
                count=counts["contracts_expiring"],
                note="Cần chuẩn bị gia hạn, nghiệm thu hoặc kế hoạch bàn giao trước hạn 30 ngày.",
                url=cls._with_query(cls._safe_reverse("admin:clients_hopdong_changelist"), {"contract_quality": "expiring_30"}),
                tone="warning",
                priority=25,
            ),
            WorkQueueItem(
                key="contracts_expired_open",
                label="Hợp đồng quá hạn chưa đóng",
                count=counts["contracts_expired_open"],
                note="Cần cập nhật trạng thái thanh lý hoặc xử lý đối soát còn tồn.",
                url=cls._with_query(cls._safe_reverse("admin:clients_hopdong_changelist"), {"contract_quality": "expired"}),
                tone="danger",
                priority=26,
            ),
        ]

    @classmethod
    def _workflow_work_items(cls, user: Any) -> list[WorkQueueItem]:
        from workflow.models import Proposal, Task

        staff = cls._staff_profile_or_none(user)
        task_qs = Task.objects.exclude(trang_thai__in=[Task.Status.HOAN_THANH, Task.Status.DA_HUY])
        proposal_qs = Proposal.objects.filter(trang_thai=Proposal.Status.CHO_DUYET)
        if not getattr(user, "is_superuser", False) and staff is not None:
            task_qs = task_qs.filter(Q(nguoi_giao=staff) | Q(nguoi_nhan=staff) | Q(nguoi_phoi_hop=staff)).distinct()
            proposal_qs = proposal_qs.filter(Q(nguoi_de_xuat=staff) | Q(nguoi_duyet_hien_tai=staff)).distinct()
        elif not getattr(user, "is_superuser", False):
            task_qs = task_qs.none()
            proposal_qs = proposal_qs.none()

        return [
            WorkQueueItem(
                key="pending_proposals",
                label="Hồ sơ đang trình duyệt",
                count=cls._bounded_count(proposal_qs),
                note="Cần rà soát để không nghẽn phê duyệt vận hành.",
                url=cls._safe_reverse("admin:workflow_proposal_changelist"),
                tone="warning",
                priority=35,
            ),
            WorkQueueItem(
                key="open_tasks",
                label="Công việc chưa hoàn tất",
                count=cls._bounded_count(task_qs),
                note="Theo người giao, người nhận hoặc phối hợp trong hồ sơ công việc.",
                url=cls._safe_reverse("admin:workflow_task_changelist"),
                tone="neutral",
                priority=60,
            ),
        ]

    @classmethod
    def _payroll_work_items(cls) -> list[WorkQueueItem]:
        counts = cls._payroll_counts()
        return [
            WorkQueueItem(
                key="payroll_open",
                label="Kỳ lương chưa khóa/chưa thanh toán",
                count=counts["payroll_open"],
                note="Cần hoàn tất đối soát trước khi khóa kỳ hoặc thanh toán.",
                url=cls._safe_reverse("admin:accounting_bangluongthang_changelist"),
                tone="warning",
                priority=42,
            )
        ]

    @classmethod
    def _inventory_health_cards(cls) -> list[OperationsSummaryCard]:
        try:
            count = cls._low_stock_count()
        except Exception:
            return []
        return [
            OperationsSummaryCard(
                key="low_stock",
                label="Vật tư dưới ngưỡng",
                value=count,
                note="Theo mức cảnh báo tồn tối thiểu.",
                tone="warning" if count else "success",
                url=cls._safe_reverse("admin:inventory_vattu_changelist"),
            )
        ]

    @classmethod
    def _inventory_work_items(cls) -> list[WorkQueueItem]:
        low_stock_count = cls._low_stock_count()
        draft_docs = cls._draft_inventory_document_count()
        return [
            WorkQueueItem(
                key="low_stock",
                label="Vật tư dưới ngưỡng tồn",
                count=low_stock_count,
                note="Cần rà soát cấp phát, thu hồi hoặc nhập bổ sung.",
                url=cls._with_query(cls._safe_reverse("admin:inventory_vattu_changelist"), {"material_issue": "low_stock"}),
                next_actions=cls._export_next_action(cls._with_query(cls._safe_reverse("admin:inventory_vattu_changelist"), {"material_issue": "low_stock"}), child_path="export-csv"),
                tone="warning",
                priority=40,
            ),
            WorkQueueItem(
                key="inventory_draft_documents",
                label="Phiếu kho còn nháp",
                count=draft_docs,
                note="Cần ghi sổ, hủy hoặc hoàn thiện chứng từ để tồn kho phản ánh đúng thực tế.",
                url=cls._with_query(cls._safe_reverse("admin:inventory_phieunhap_changelist"), {"receipt_issue": "draft"}),
                next_actions=cls._export_next_action(cls._with_query(cls._safe_reverse("admin:inventory_phieunhap_changelist"), {"receipt_issue": "draft"}), child_path="export-csv"),
                tone="neutral",
                priority=50,
            ),
        ]

    @classmethod
    def _low_stock_count(cls) -> int:
        from inventory.models import VatTu

        return AdminOperationsUXProvider._bounded_count(VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(so_luong_ton__lte=F("muc_canh_bao")))

    @classmethod
    def _draft_inventory_document_count(cls) -> int:
        from inventory.models import PhieuNhap, PhieuXuat

        org_id = settings.SCMD_ORGANIZATION_ID
        return (
            AdminOperationsUXProvider._bounded_count(PhieuNhap.objects.for_tenant(org_id).filter(trang_thai=PhieuNhap.TrangThai.DRAFT))
            + AdminOperationsUXProvider._bounded_count(PhieuXuat.objects.for_tenant(org_id).filter(trang_thai=PhieuXuat.TrangThai.DRAFT))
        )

    @staticmethod
    def _bounded_count(queryset: QuerySet, limit: int = 999) -> int:
        """Count enough for work queues without forcing heavy exact counts.

        Work queues answer "is there work and roughly how much?". For very large
        tables, bounded counting prevents the admin home from doing full-table
        counts across every module on each request. Values above the limit are
        displayed as ``999+`` by ``_queue_item`` when used there.
        """
        rows = list(queryset.values_list("pk", flat=True)[: limit + 1])
        return limit + 1 if len(rows) > limit else len(rows)

    @staticmethod
    def _count_label(count: int, limit: int = 999) -> str:
        return f"{limit}+" if count > limit else str(count)

    @staticmethod
    def _staff_profile_or_none(user: Any):
        try:
            return user.nhan_vien
        except Exception:
            return None

    @staticmethod
    def _safe_reverse(name: str, fallback: str = "#") -> str:
        try:
            return reverse(name)
        except NoReverseMatch:
            return fallback

    @staticmethod
    def _with_query(url: str, params: dict[str, str]) -> str:
        if not url or url == "#":
            return "#"
        query = urlencode(params)
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{query}"

    @staticmethod
    def _admin_child_url(changelist_url: str, child_path: str) -> str:
        """Build a known child admin endpoint while preserving filters.

        This is intentionally strict: callers pass the exact child endpoint that
        exists on that ModelAdmin. It prevents fake CTAs such as ``generic export flag``
        on changelists that do not implement generic export handling.
        """
        if not changelist_url or changelist_url == "#":
            return "#"
        path, _separator, query = changelist_url.partition("?")
        if not path.endswith("/"):
            path = f"{path}/"
        child = child_path.strip("/")
        url = f"{path}{child}/"
        return f"{url}?{query}" if query else url

    @classmethod
    def _export_next_action(
        cls,
        changelist_url: str,
        *,
        child_path: str,
        label: str = "Xuất danh sách lọc",
    ) -> list[dict[str, str]]:
        export_url = cls._admin_child_url(changelist_url, child_path)
        return [{"label": label, "url": export_url}] if export_url != "#" else []


__all__ = ["AdminOperationsUXProvider", "OperationsSummaryCard", "WorkQueueItem"]
