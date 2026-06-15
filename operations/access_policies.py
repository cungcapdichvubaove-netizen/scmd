# -*- coding: utf-8 -*-
"""Operational access policies for SCMD Pro.

These policies are the Phase B/C enforcement layer for operations data. They
centralize queryset visibility and object-level scheduling/dispatch checks so
views, APIs and admin surfaces do not duplicate or bypass scope logic.

Scope rules here are deliberately conservative:
- no organization id is accepted from requests or callers;
- no unscoped ``.objects.all()`` queries are used;
- when direct scope data is missing, access is denied rather than widened;
- temporary delegation and historical assignment are not emulated here.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.conf import settings
from rolepermissions.checkers import has_permission, has_role
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet

from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from core.request_local import get_request_local_value
from core.policy_result import (
    ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
    ERR_PAYROLL_LOCKED,
    ERR_SCOPE_SHIFT_OUT_OF_SCOPE,
    ERR_SCOPE_SITE_OUT_OF_SCOPE,
    ERR_SCOPE_STAFF_OUT_OF_SCOPE,
    PolicyResult,
)
from operations.models import BaoCaoDeXuat, BaoCaoSuCo, ChamCong, KiemTraQuanSo, PhanCongCaTruc, ViTriChot
from users.access_policies import StaffVisibilityPolicy
from users.models import LichSuCongTac, NhanVien


class PostVisibilityPolicy:
    """Query-level visibility for guard posts/positions under managed sites."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[ViTriChot]:
        return ViTriChot.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _has_global_post_visibility(user: Any) -> bool:
        """Roles that intentionally retain global post visibility."""
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"]))
        )

    @classmethod
    def visible_posts(cls, user: Any, at_time=None) -> QuerySet[ViTriChot]:
        base_qs = cls._base_queryset().select_related("muc_tieu", "muc_tieu__hop_dong")
        if cls._has_global_post_visibility(user):
            return base_qs.distinct()

        managed_sites = SiteVisibilityPolicy.managed_sites(user, at_time=at_time)
        return (
            base_qs
            .filter(muc_tieu__in=managed_sites)
            .distinct()
        )


class ShiftVisibilityPolicy:
    """Query-level visibility for shift assignments."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[PhanCongCaTruc]:
        return PhanCongCaTruc.objects.for_tenant(cls._organization_id())


    @staticmethod
    def _has_global_shift_visibility(user: Any) -> bool:
        """Roles that intentionally retain global shift visibility.

        Technical superuser must be evaluated before staff-profile scoping so
        Django Admin does not hide seeded organization data from maintenance
        accounts. Business users still require explicit global roles.
        """
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"]))
        )

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not (user is not None and getattr(user, "is_authenticated", False)):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @classmethod
    def visible_shifts(cls, user: Any, date_range: tuple[date, date] | None = None) -> QuerySet[PhanCongCaTruc]:
        """Return shifts visible to the user at database-query level.

        Guards see their own shifts. Site/region managers also see shifts whose
        post belongs to managed sites. Current staff assignment alone must not
        reveal coworkers' shifts at the same site.
        """

        def builder() -> QuerySet[PhanCongCaTruc]:
            base_qs = cls._base_queryset().select_related(
                "nhan_vien",
                "vi_tri_chot",
                "vi_tri_chot__muc_tieu",
                "vi_tri_chot__muc_tieu__hop_dong",
                "ca_lam_viec",
            )
            if cls._has_global_shift_visibility(user):
                qs = base_qs
            else:
                staff = cls._staff_profile(user)
                if staff is None:
                    return base_qs.none()

                managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
                qs = base_qs.filter(Q(nhan_vien=staff) | Q(vi_tri_chot__muc_tieu_id__in=managed_site_ids)).distinct()
            if date_range is not None:
                start_date, end_date = date_range
                qs = qs.filter(ngay_truc__gte=start_date, ngay_truc__lte=end_date)
            return qs

        return get_request_local_value(user, ("ShiftVisibilityPolicy.visible_shifts", date_range), builder)


class AttendanceVisibilityPolicy:
    """Query-level visibility for attendance records."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[ChamCong]:
        return ChamCong.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _has_global_attendance_visibility(user: Any) -> bool:
        """Roles that intentionally retain global attendance visibility (Rule 6.2)."""
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"]))
        )

    @classmethod
    def visible_attendance(cls, user: Any) -> QuerySet[ChamCong]:
        base_qs = cls._base_queryset().select_related(
            "ca_truc", "ca_truc__nhan_vien", "ca_truc__vi_tri_chot__muc_tieu"
        )
        if cls._has_global_attendance_visibility(user):
            return base_qs

        staff = getattr(user, "nhan_vien", None)
        if staff is None:
            return base_qs.none()

        managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
        return base_qs.filter(
            Q(ca_truc__nhan_vien=staff) | Q(ca_truc__vi_tri_chot__muc_tieu_id__in=managed_site_ids)
        ).distinct()


class ProposalVisibilityPolicy:
    """Query-level visibility for field proposals."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[BaoCaoDeXuat]:
        return BaoCaoDeXuat.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _has_global_proposal_visibility(user: Any) -> bool:
        """Administrative roles with global proposal visibility (BGD, HR, OPS)."""
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "is_superuser", False) 
                or has_role(user, ["ban_giam_doc", "nhan_su", "nghiep_vu"])
            )
        )

    @classmethod
    def visible_proposals(cls, user: Any) -> QuerySet[BaoCaoDeXuat]:
        base_qs = cls._base_queryset().select_related("nhan_vien", "muc_tieu")
        if cls._has_global_proposal_visibility(user):
            return base_qs

        staff = getattr(user, "nhan_vien", None)
        if staff is None:
            return base_qs.none()

        managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
        return base_qs.filter(
            Q(nhan_vien=staff) | Q(muc_tieu_id__in=managed_site_ids)
        ).distinct()


class AliveCheckVisibilityPolicy:
    """Query-level visibility for Alive Check records."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[KiemTraQuanSo]:
        return KiemTraQuanSo.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _has_global_alive_visibility(user: Any) -> bool:
        """Administrative roles with global alive check visibility (BGD, Inspectors, OPS)."""
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "is_superuser", False) 
                or has_role(user, ["ban_giam_doc", "thanh_tra", "nghiep_vu"])
            )
        )

    @classmethod
    def visible_alive_checks(cls, user: Any) -> QuerySet[KiemTraQuanSo]:
        base_qs = cls._base_queryset().select_related("ca_truc", "ca_truc__nhan_vien", "ca_truc__vi_tri_chot__muc_tieu")
        if cls._has_global_alive_visibility(user):
            return base_qs

        staff = getattr(user, "nhan_vien", None)
        if staff is None:
            return base_qs.none()

        managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
        return base_qs.filter(
            Q(ca_truc__nhan_vien=staff) | Q(ca_truc__vi_tri_chot__muc_tieu_id__in=managed_site_ids)
        ).distinct()


class ShiftAssignmentPolicy:
    """Object-level policy for scheduling actions.

    This class does not mutate data. Use cases/admin/views must call it before
    creating/updating/deleting shift assignments.
    """

    BUSINESS_PERMISSION = "giao_ca_truc"
    ADD_PERMISSION = "operations.add_phancongcatruc"
    CHANGE_PERMISSION = "operations.change_phancongcatruc"
    DELETE_PERMISSION = "operations.delete_phancongcatruc"

    @staticmethod
    def _has_perm(user: Any, permission: str) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False) and user.has_perm(permission))

    @classmethod
    def _has_mutation_authority(cls, user: Any, django_permission: str) -> bool:
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and has_permission(user, cls.BUSINESS_PERMISSION)
            and user.has_perm(django_permission)
        )

    @classmethod
    def _deny_missing_mutation_authority(cls, django_permission: str, action_label: str) -> PolicyResult:
        return cls._safe_denial(
            ERR_SCOPE_SHIFT_OUT_OF_SCOPE,
            f"Bạn chưa có đủ quyền nghiệp vụ để {action_label} ca trực.",
            details={
                "required_rolepermission": cls.BUSINESS_PERMISSION,
                "required_django_permission": django_permission,
            },
        )

    @staticmethod
    def _safe_denial(error_code: str, message: str, *, details: dict | None = None) -> PolicyResult:
        return PolicyResult.deny(error_code, message, details=details or {}, scope_source="DIRECT")

    @classmethod
    def _can_place_staff_at_site(cls, user: Any, staff: NhanVien | None, site: MucTieu | None, shift_date: date | None) -> PolicyResult:
        if site is None or getattr(site, "pk", None) is None:
            return cls._safe_denial(ERR_SCOPE_SITE_OUT_OF_SCOPE, "Mục tiêu không thuộc phạm vi được phép.")
        if staff is None or getattr(staff, "pk", None) is None:
            return cls._safe_denial(ERR_SCOPE_STAFF_OUT_OF_SCOPE, "Nhân viên không thuộc phạm vi được phép.")

        managed_site_ids = SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True)
        if not SiteVisibilityPolicy.managed_sites(user).filter(pk=site.pk).exists():
            return cls._safe_denial(ERR_SCOPE_SITE_OUT_OF_SCOPE, "Mục tiêu không thuộc phạm vi quản lý của bạn.")

        assignable_staff = StaffVisibilityPolicy.visible_staff_for_scheduling(user, site, at_date=shift_date)
        if not assignable_staff.filter(pk=staff.pk).exists():
            return cls._safe_denial(ERR_SCOPE_STAFF_OUT_OF_SCOPE, "Nhân viên không thuộc phạm vi điều phối tại mục tiêu này.")

        # Defense-in-depth: ensure current staff-site assignment is scoped at DB level.
        if not LichSuCongTac.objects.filter(
            nhan_vien=staff,
            muc_tieu_id__in=managed_site_ids,
            muc_tieu=site,
            ngay_ket_thuc__isnull=True,
        ).exists():
            return cls._safe_denial(ERR_SCOPE_STAFF_OUT_OF_SCOPE, "Không tìm thấy phân công hiện tại phù hợp phạm vi.")

        return PolicyResult.allow(
            message="Được phép thao tác ca trong phạm vi trực tiếp.",
            details={"policy": "ShiftAssignmentPolicy._can_place_staff_at_site"},
            effective_scope_level="SITE",
            scope_source="DIRECT",
        )

    @classmethod
    def can_assign_shift(cls, user: Any, staff: NhanVien | None, site: MucTieu | None, shift_date: date | None) -> PolicyResult:
        if not cls._has_mutation_authority(user, cls.ADD_PERMISSION):
            return cls._deny_missing_mutation_authority(cls.ADD_PERMISSION, "phân công")
        return cls._can_place_staff_at_site(user, staff, site, shift_date)

    @classmethod
    def can_update_shift(cls, user: Any, shift: PhanCongCaTruc | None) -> PolicyResult:
        if shift is None or getattr(shift, "pk", None) is None:
            return cls._safe_denial(ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, "Không tìm thấy ca trực hoặc bạn không có quyền xem.")
        if not cls._has_mutation_authority(user, cls.CHANGE_PERMISSION):
            return cls._deny_missing_mutation_authority(cls.CHANGE_PERMISSION, "sửa")
        if getattr(shift, "is_payroll_locked", False):
            return cls._safe_denial(ERR_PAYROLL_LOCKED, "Kỳ lương liên quan đã khóa/đã thanh toán, không được sửa ca trực.")
        if not ShiftVisibilityPolicy.visible_shifts(user).filter(pk=shift.pk).exists():
            return cls._safe_denial(ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, "Không tìm thấy ca trực hoặc bạn không có quyền xem.")
        site = getattr(getattr(shift, "vi_tri_chot", None), "muc_tieu", None)
        return cls._can_place_staff_at_site(user, shift.nhan_vien, site, shift.ngay_truc)

    @classmethod
    def can_delete_shift(cls, user: Any, shift: PhanCongCaTruc | None) -> PolicyResult:
        if shift is None or getattr(shift, "pk", None) is None:
            return cls._safe_denial(ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, "Không tìm thấy ca trực hoặc bạn không có quyền xem.")
        if not cls._has_mutation_authority(user, cls.DELETE_PERMISSION):
            return cls._deny_missing_mutation_authority(cls.DELETE_PERMISSION, "xóa")
        if getattr(shift, "is_payroll_locked", False):
            return cls._safe_denial(ERR_PAYROLL_LOCKED, "Kỳ lương liên quan đã khóa/đã thanh toán, không được xóa ca trực.")
        if not ShiftVisibilityPolicy.visible_shifts(user).filter(pk=shift.pk).exists():
            return cls._safe_denial(ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, "Không tìm thấy ca trực hoặc bạn không có quyền xem.")
        return PolicyResult.allow(message="Được phép xóa ca trong phạm vi trực tiếp.", effective_scope_level="SITE", scope_source="DIRECT")


class DispatchPolicy:
    """Object-level policy for direct staff transfers.

    Actual transfer use case is intentionally not implemented here. This policy
    is a guard used by future dispatch workflows and admin/actions.
    """

    CHANGE_PERMISSION = "users.change_nhanvien"
    DISPATCH_PERMISSION = "users.xu_ly_dieu_chuyen_nhan_su"

    @classmethod
    def can_transfer_staff(
        cls,
        user: Any,
        staff: NhanVien | None,
        from_site: MucTieu | None,
        to_site: MucTieu | None,
        effective_date: date | None,
    ) -> PolicyResult:
        # Enforcement of specific dispatch permission (F-01 Residual)
        has_perm = (
            user is not None and 
            user.is_authenticated and 
            (user.has_perm(cls.CHANGE_PERMISSION) or user.has_perm(cls.DISPATCH_PERMISSION))
        )
        if not has_perm:
            return PolicyResult.deny(
                ERR_SCOPE_STAFF_OUT_OF_SCOPE,
                "Bạn chưa có quyền nghiệp vụ để điều động nhân viên.",
                details={"required_permission": cls.DISPATCH_PERMISSION},
                scope_source="DIRECT",
            )
        if staff is None or from_site is None or to_site is None:
            return PolicyResult.deny(ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, "Không tìm thấy đối tượng hoặc không có quyền xem.", scope_source="DIRECT")
        managed_sites = SiteVisibilityPolicy.managed_sites(user)
        if not managed_sites.filter(pk=from_site.pk).exists():
            return PolicyResult.deny(ERR_SCOPE_SITE_OUT_OF_SCOPE, "Nơi đi không thuộc phạm vi điều động.", scope_source="DIRECT")
        if not managed_sites.filter(pk=to_site.pk).exists():
            return PolicyResult.deny(ERR_SCOPE_SITE_OUT_OF_SCOPE, "Nơi đến không thuộc phạm vi điều động.", scope_source="DIRECT")
        if not StaffVisibilityPolicy.visible_staff(user).filter(pk=staff.pk).exists():
            return PolicyResult.deny(ERR_SCOPE_STAFF_OUT_OF_SCOPE, "Nhân viên không thuộc phạm vi điều động.", scope_source="DIRECT")
        return PolicyResult.allow(message="Được phép điều động trong phạm vi trực tiếp.", effective_scope_level="REGION", scope_source="DIRECT")


class IncidentVisibilityPolicy:
    """Query-level visibility for incidents."""

    @staticmethod
    def _organization_id():
        return settings.SCMD_ORGANIZATION_ID

    @classmethod
    def _base_queryset(cls) -> QuerySet[BaoCaoSuCo]:
        return BaoCaoSuCo.objects.for_tenant(cls._organization_id())

    @staticmethod
    def _has_global_incident_visibility(user: Any) -> bool:
        """Roles that intentionally retain global incident visibility.

        The legacy mobile API allowed executive and payroll/accounting roles to
        see all incidents in the configured organization. Technical superuser
        also needs full Django Admin visibility before staff-profile scoping.
        """
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"]))
        )

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not (user is not None and getattr(user, "is_authenticated", False)):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @classmethod
    def visible_incidents(cls, user: Any, at_time=None) -> QuerySet[BaoCaoSuCo]:
        base_qs = cls._base_queryset().select_related("nhan_vien_bao_cao", "muc_tieu", "ca_truc")
        if cls._has_global_incident_visibility(user):
            return base_qs

        staff = cls._staff_profile(user)
        if staff is None:
            return base_qs.none()
        managed_site_ids = SiteVisibilityPolicy.managed_sites(user, at_time=at_time).values_list("pk", flat=True)
        visible_shift_ids = ShiftVisibilityPolicy.visible_shifts(user).values_list("pk", flat=True)
        return base_qs.filter(
            Q(nhan_vien_bao_cao=staff)
            | Q(muc_tieu_id__in=managed_site_ids)
            | Q(ca_truc_id__in=visible_shift_ids)
        ).distinct()


class ShiftAccessPolicy:
    """Backward-compatible attendance access policy.

    Existing mobile web/API entrypoints import ``ShiftAccessPolicy`` and call
    ``get_accessible_shift_for_attendance`` before check-in/check-out. Keep that
    public contract stable while the newer visibility/action policies are added.

    Attendance is stricter than shift visibility: guards may only operate their
    own shift. Management scope does not allow checking in/out on behalf of other
    staff, and technical superuser is not used as a business bypass here.
    ``tenant_id`` is accepted only for legacy caller compatibility; the
    organization scope remains the configured SCMD organization.
    """

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not (user is not None and getattr(user, "is_authenticated", False)):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @classmethod
    def get_accessible_shift_for_attendance(cls, user: Any, shift_id: int, tenant_id=None) -> PhanCongCaTruc:
        staff = cls._staff_profile(user)
        if staff is None:
            raise PermissionDenied("Không có quyền thao tác ca trực này.")

        shift = (
            PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
            .select_related(
                "nhan_vien",
                "vi_tri_chot",
                "vi_tri_chot__muc_tieu",
                "ca_lam_viec",
            )
            .filter(pk=shift_id, nhan_vien=staff)
            .first()
        )
        if shift is None:
            raise PermissionDenied("Không tìm thấy ca trực hợp lệ hoặc bạn không có quyền thao tác.")
        return shift


__all__ = [
    "AliveCheckVisibilityPolicy",
    "AttendanceVisibilityPolicy",
    "DispatchPolicy",
    "IncidentVisibilityPolicy",
    "PostVisibilityPolicy",
    "ProposalVisibilityPolicy",
    "ShiftAccessPolicy",
    "ShiftAssignmentPolicy",
    "ShiftVisibilityPolicy",
]
