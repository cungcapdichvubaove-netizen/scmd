# -*- coding: utf-8 -*-
"""Direct site and region visibility policies for SCMD Pro."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from rolepermissions.checkers import has_role

from core.request_local import get_request_local_value
from clients.models import MucTieu
from users.models import LichSuCongTac, NhanVien
from users.models_assignment import NhanVienRegionAssignment, Region


ROLE_ALIAS_KEYS = {
    "ban_giam_doc": {"bangiamdoc", "banlanhdao", "tonggiamdoc", "giamdoc", "bod"},
    "quan_ly_vung": {"quanlyvung", "quanlyvung1", "qlv", "vung"},
    "doi_truong": {"doitruong", "chihuytruong"},
    "nhan_su": {"nhansu", "hanhchinhnhansu", "hcns"},
    "ke_toan": {"ketoan", "taichinhketoan", "ketoantaichinh"},
    "thanh_tra": {"thanhtra", "thanhtradaotao", "kiemtra"},
    "nghiep_vu": {"nghiepvu", "vanhanh", "dieuhanh"},
}


def _normalized_user_scope_labels(user: Any) -> set[str]:
    try:
        from main.dashboard_router import DashboardRouter
    except Exception:
        return set()

    labels: set[str] = set()
    if not (user is not None and getattr(user, "is_authenticated", False)):
        return labels

    for name in user.groups.values_list("name", flat=True):
        key = DashboardRouter._normalize_key(name)
        if key:
            labels.add(key)

    try:
        staff = user.nhan_vien
    except (AttributeError, NhanVien.DoesNotExist):
        staff = None

    if staff is not None:
        for attr_name in ("phong_ban", "chuc_danh"):
            obj = getattr(staff, attr_name, None)
            if obj is None:
                continue
            label = getattr(obj, "ten_phong_ban", "") or getattr(obj, "ten_chuc_danh", "")
            key = DashboardRouter._normalize_key(label)
            if key:
                labels.add(key)
    return labels




def _has_nationwide_operations_scope(user: Any) -> bool:
    """Return true for explicitly central operations demo roles.

    This is not a generic role widening: the user must have the nghiệp vụ role
    and a staff department/title that resolves to Phòng Vận hành Toàn quốc or
    Trung tâm Điều phối. Branch operations users remain region-bound through
    NhanVienRegionAssignment.
    """
    if not (user is not None and getattr(user, "is_authenticated", False)):
        return False
    if not has_role(user, "nghiep_vu"):
        return False

    labels = _normalized_user_scope_labels(user)
    central_scope_keys = {
        "phongvanhanhtoanquoc",
        "trungtamdieu phoi".replace(" ", ""),
        "trucbantrungtam",
    }
    return bool(labels & central_scope_keys)


def _has_business_role(user: Any, role_names: tuple[str, ...]) -> bool:
    if any(has_role(user, role_name) for role_name in role_names):
        return True
    labels = _normalized_user_scope_labels(user)
    if not labels:
        return False
    accepted: set[str] = set()
    try:
        from main.dashboard_router import DashboardRouter
        for role_name in role_names:
            accepted.add(DashboardRouter._normalize_key(role_name))
            accepted.update(ROLE_ALIAS_KEYS.get(role_name, set()))
    except Exception:
        for role_name in role_names:
            accepted.add(role_name.replace("_", ""))
            accepted.update(ROLE_ALIAS_KEYS.get(role_name, set()))
    return bool(labels & accepted)


class RegionVisibilityPolicy:
    """Direct region scope for area-manager style workflows."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_region_queryset(cls) -> QuerySet[Region]:
        return Region.objects.for_tenant(cls._organization_id())

    @classmethod
    def _base_site_queryset(cls) -> QuerySet[MucTieu]:
        return MucTieu.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _is_authenticated(user: Any) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False))

    @staticmethod
    def _is_superuser(user: Any) -> bool:
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_superuser", False)
        )

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not RegionVisibilityPolicy._is_authenticated(user):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @staticmethod
    def _effective_date(at_time=None) -> date:
        if at_time is None:
            return date.today()
        if isinstance(at_time, datetime):
            return at_time.date()
        if isinstance(at_time, date):
            return at_time
        return date.today()

    @classmethod
    def managed_regions(cls, user: Any, at_time=None) -> QuerySet[Region]:
        effective_date = cls._effective_date(at_time)

        def builder() -> QuerySet[Region]:
            base_qs = cls._base_region_queryset()
            if cls._is_superuser(user):
                return base_qs

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()
            if not _has_business_role(user, ("quan_ly_vung", "ban_giam_doc", "nghiep_vu")):
                return base_qs.none()
            if _has_nationwide_operations_scope(user):
                return base_qs.distinct()

            assignment_region_ids = (
                NhanVienRegionAssignment.objects.for_tenant(cls._organization_id())
                .filter(
                    nhan_vien=staff,
                    status=NhanVienRegionAssignment.Status.ACTIVE,
                    starts_at__lte=effective_date,
                )
                .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=effective_date))
                .values_list("region_id", flat=True)
                .distinct()
            )
            return base_qs.filter(pk__in=assignment_region_ids)

        return get_request_local_value(
            user,
            ("RegionVisibilityPolicy.managed_regions", effective_date),
            builder,
        )

    @classmethod
    def managed_sites(cls, user: Any, at_time=None) -> QuerySet[MucTieu]:
        """Return sites visible through authoritative region scope.

        Region-bound sites resolve region through ``HopDong.co_hoi.region`` as
        the SSOT. Legacy ``MucTieu.quan_ly_vung`` is kept only as a fallback
        for sites whose converted opportunity has not been backfilled yet.
        """

        effective_date = cls._effective_date(at_time)

        def builder() -> QuerySet[MucTieu]:
            base_qs = cls._base_site_queryset()
            if cls._is_superuser(user):
                return base_qs.select_related(
                    "hop_dong__co_hoi__region",
                    "quan_ly_muc_tieu",
                    "quan_ly_vung",
                ).distinct()

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()
            if not _has_business_role(user, ("quan_ly_vung", "ban_giam_doc", "nghiep_vu")):
                return base_qs.none()
            if _has_nationwide_operations_scope(user):
                return base_qs.select_related(
                    "hop_dong__co_hoi__region",
                    "quan_ly_muc_tieu",
                    "quan_ly_vung",
                ).distinct()

            managed_region_ids = cls.managed_regions(user, at_time=effective_date).values_list("pk", flat=True)
            return (
                base_qs.filter(
                    Q(hop_dong__co_hoi__region_id__in=managed_region_ids)
                    | Q(quan_ly_vung=staff)
                )
                .select_related("hop_dong__co_hoi__region", "quan_ly_muc_tieu", "quan_ly_vung")
                .distinct()
            )

        return get_request_local_value(
            user,
            ("RegionVisibilityPolicy.managed_sites", effective_date),
            builder,
        )


class SiteVisibilityPolicy:
    """Query-level visibility for protected sites/targets."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[MucTieu]:
        return MucTieu.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _is_authenticated(user: Any) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False))

    @staticmethod
    def _is_superuser(user: Any) -> bool:
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_superuser", False)
        )

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not SiteVisibilityPolicy._is_authenticated(user):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @classmethod
    def _current_assignment_site_ids(cls, staff: NhanVien) -> QuerySet:
        org_id = cls._organization_id()
        return (
            LichSuCongTac.objects.filter(
                nhan_vien=staff,
                nhan_vien__tenant_id=org_id,
                muc_tieu__isnull=False,
                muc_tieu__hop_dong__tenant_id=org_id,
                ngay_ket_thuc__isnull=True,
            )
            .values_list("muc_tieu_id", flat=True)
            .distinct()
        )

    @classmethod
    def managed_sites(cls, user: Any, at_time=None) -> QuerySet[MucTieu]:
        effective_date = RegionVisibilityPolicy._effective_date(at_time)

        def builder() -> QuerySet[MucTieu]:
            base_qs = cls._base_queryset()
            if cls._is_superuser(user):
                return base_qs.select_related(
                    "hop_dong__co_hoi__region",
                    "quan_ly_muc_tieu",
                    "quan_ly_vung",
                ).distinct()

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()

            region_site_ids = RegionVisibilityPolicy.managed_sites(user, at_time=effective_date).values_list("pk", flat=True)
            return (
                base_qs.filter(
                    Q(quan_ly_muc_tieu=staff)
                    | Q(quan_ly_vung=staff)
                    | Q(pk__in=region_site_ids)
                )
                .select_related("hop_dong__co_hoi__region", "quan_ly_muc_tieu", "quan_ly_vung")
                .distinct()
            )

        return get_request_local_value(
            user,
            ("SiteVisibilityPolicy.managed_sites", effective_date),
            builder,
        )

    @classmethod
    def assigned_sites(cls, user: Any, at_time=None) -> QuerySet[MucTieu]:
        def builder() -> QuerySet[MucTieu]:
            base_qs = cls._base_queryset()
            if cls._is_superuser(user):
                return base_qs.select_related(
                    "hop_dong__co_hoi__region",
                    "quan_ly_muc_tieu",
                    "quan_ly_vung",
                ).distinct()

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()
            return (
                base_qs.filter(pk__in=cls._current_assignment_site_ids(staff))
                .select_related("hop_dong__co_hoi__region", "quan_ly_muc_tieu", "quan_ly_vung")
                .distinct()
            )

        return get_request_local_value(user, ("SiteVisibilityPolicy.assigned_sites",), builder)

    @classmethod
    def visible_sites(cls, user: Any, at_time=None) -> QuerySet[MucTieu]:
        effective_date = RegionVisibilityPolicy._effective_date(at_time)

        def builder() -> QuerySet[MucTieu]:
            base_qs = cls._base_queryset()
            if cls._is_superuser(user):
                return base_qs.select_related(
                    "hop_dong__co_hoi__region",
                    "quan_ly_muc_tieu",
                    "quan_ly_vung",
                ).distinct()

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()

            current_site_ids = cls._current_assignment_site_ids(staff)
            managed_site_ids = cls.managed_sites(user, at_time=effective_date).values_list("pk", flat=True)
            return (
                base_qs.filter(Q(pk__in=managed_site_ids) | Q(pk__in=current_site_ids))
                .select_related("hop_dong__co_hoi__region", "quan_ly_muc_tieu", "quan_ly_vung")
                .distinct()
            )

        return get_request_local_value(
            user,
            ("SiteVisibilityPolicy.visible_sites", effective_date),
            builder,
        )


__all__ = ["RegionVisibilityPolicy", "SiteVisibilityPolicy"]
