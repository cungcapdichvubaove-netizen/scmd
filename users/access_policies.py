# -*- coding: utf-8 -*-
"""Direct staff visibility policies for SCMD Pro.

Phase B scope only:
- centralize direct staff queryset filtering;
- support scheduling dropdown/queryset visibility only;
- do not authorize scheduling actions;
- fail closed when user/profile/site scope is missing.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy
from core.request_local import get_request_local_value
from clients.models import MucTieu
from users.models import LichSuCongTac, NhanVien


class StaffVisibilityPolicy:
    """Query-level visibility for staff records."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[NhanVien]:
        return NhanVien.objects.for_tenant(cls._organization_id())

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

    @classmethod
    def _has_global_staff_visibility(cls, user: Any) -> bool:
        """Administrative roles with global data access (WHITEPAPER.md 9)."""
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (
                cls._is_superuser(user)
                or has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"])
            )
        )

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not StaffVisibilityPolicy._is_authenticated(user):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @classmethod
    def _staff_ids_currently_assigned_to_sites(cls, sites: QuerySet[MucTieu]) -> QuerySet:
        org_id = cls._organization_id()
        return (
            LichSuCongTac.objects.filter(
                nhan_vien__tenant_id=org_id,
                muc_tieu__in=sites,
                muc_tieu__hop_dong__tenant_id=org_id,
                ngay_ket_thuc__isnull=True,
            )
            .values_list("nhan_vien_id", flat=True)
            .distinct()
        )

    @classmethod
    def visible_staff(cls, user: Any, at_time=None) -> QuerySet[NhanVien]:
        """Return staff visible to ``user`` under direct management scope.

        The authenticated staff profile can always see itself. Coworkers are
        visible only if they are currently assigned to a site returned by
        ``SiteVisibilityPolicy.managed_sites(user)``. Current assignment to the
        same site as a guard does not reveal other staff at that site.
        """

        def builder() -> QuerySet[NhanVien]:
            base_qs = cls._base_queryset()
            if cls._has_global_staff_visibility(user):
                return base_qs.select_related("phong_ban", "chuc_danh", "user").distinct()

            staff = cls._staff_profile(user)
            if staff is None:
                return base_qs.none()

            managed_sites = SiteVisibilityPolicy.managed_sites(user, at_time=at_time)
            scoped_staff_ids = cls._staff_ids_currently_assigned_to_sites(managed_sites)
            return (
                base_qs.filter(Q(pk=staff.pk) | Q(pk__in=scoped_staff_ids))
                .select_related("phong_ban", "chuc_danh", "user")
                .distinct()
            )

        return get_request_local_value(user, ("StaffVisibilityPolicy.visible_staff", at_time), builder)

    @classmethod
    def visible_staff_for_scheduling(
        cls,
        user: Any,
        site: MucTieu | None,
        at_date=None,
    ) -> QuerySet[NhanVien]:
        """Return active staff candidates for scheduling at ``site``.

        Scheduling visibility requires management scope over the target site.
        A guard who is merely assigned to a site must not become able to list
        assignable coworkers if they accidentally receive a functional schedule
        permission.
        """

        def builder() -> QuerySet[NhanVien]:
            base_qs = cls._base_queryset()
            if cls._has_global_staff_visibility(user):
                return (
                    base_qs.filter(
                        trang_thai_lam_viec__in=[
                            NhanVien.TrangThaiLamViec.CHINH_THUC,
                            NhanVien.TrangThaiLamViec.THU_VIEC,
                        ]
                    )
                    .select_related("phong_ban", "chuc_danh", "user")
                    .distinct()
                )

            staff = cls._staff_profile(user)
            if staff is None or site is None or getattr(site, "pk", None) is None:
                return base_qs.none()

            managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
            org_id = cls._organization_id()
            scoped_staff_ids = (
                LichSuCongTac.objects.filter(
                    nhan_vien__tenant_id=org_id,
                    muc_tieu=site,
                    muc_tieu_id__in=managed_site_ids,
                    muc_tieu__hop_dong__tenant_id=org_id,
                    ngay_ket_thuc__isnull=True,
                )
                .values_list("nhan_vien_id", flat=True)
                .distinct()
            )
            return (
                base_qs.filter(
                    pk__in=scoped_staff_ids,
                    trang_thai_lam_viec__in=[
                        NhanVien.TrangThaiLamViec.CHINH_THUC,
                        NhanVien.TrangThaiLamViec.THU_VIEC,
                    ],
                )
                .select_related("phong_ban", "chuc_danh", "user")
                .distinct()
            )

        site_id = getattr(site, "pk", None)
        return get_request_local_value(
            user,
            ("StaffVisibilityPolicy.visible_staff_for_scheduling", site_id, at_date),
            builder,
        )


__all__ = ["StaffVisibilityPolicy"]
