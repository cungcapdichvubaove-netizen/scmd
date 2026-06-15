# -*- coding: utf-8 -*-
"""Authorization policy for shift-change approval/apply/report workflows.

ShiftChangeRequest mutates duty rosters and may impact attendance/payroll.
Authentication alone is never enough for approving, applying, or reporting on
shift-change activity. This policy is intentionally used from application use
cases, not only API views, so admin/API/mobile callers share the same
authorization boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy
from operations.models import PhanCongCaTruc, ShiftChangeRequest
from users.models import NhanVien


@dataclass(frozen=True)
class ShiftChangePermissionDecision:
    allowed: bool
    reason: str = ""
    code: str = "SHIFT_CHANGE_FORBIDDEN"


class ShiftChangePermissionPolicy:
    """Least-privilege authorization for shift-change lifecycle actions."""

    GLOBAL_APPROVER_ROLES = ["ban_giam_doc", "nghiep_vu"]
    SCOPED_APPROVER_ROLES = ["doi_truong", "quan_ly_vung"]
    REPORT_GLOBAL_ROLES = GLOBAL_APPROVER_ROLES
    REPORT_SCOPED_ROLES = SCOPED_APPROVER_ROLES

    @staticmethod
    def _is_authenticated(user: Any) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False))

    @staticmethod
    def _staff_profile(user: Any) -> NhanVien | None:
        if not ShiftChangePermissionPolicy._is_authenticated(user):
            return None
        try:
            return user.nhan_vien
        except (AttributeError, NhanVien.DoesNotExist):
            return None

    @staticmethod
    def _deny(reason: str, code: str = "SHIFT_CHANGE_FORBIDDEN") -> ShiftChangePermissionDecision:
        return ShiftChangePermissionDecision(False, reason, code)

    @staticmethod
    def _allow(reason: str = "allowed") -> ShiftChangePermissionDecision:
        return ShiftChangePermissionDecision(True, reason, "OK")

    @staticmethod
    def _relevant_site_ids(shift_request: ShiftChangeRequest) -> set[int]:
        site_ids: set[int] = set()
        original = getattr(shift_request, "phan_cong_goc", None)
        desired_post = getattr(shift_request, "vi_tri_mong_muon", None)
        if original and getattr(original, "vi_tri_chot", None) and getattr(original.vi_tri_chot, "muc_tieu_id", None):
            site_ids.add(original.vi_tri_chot.muc_tieu_id)
        if desired_post and getattr(desired_post, "muc_tieu_id", None):
            site_ids.add(desired_post.muc_tieu_id)
        return site_ids

    @classmethod
    def _has_global_operations_role(cls, user: Any) -> bool:
        return bool(getattr(user, "is_superuser", False) or has_role(user, cls.GLOBAL_APPROVER_ROLES))

    @classmethod
    def _has_scoped_operations_role(cls, user: Any) -> bool:
        return bool(has_role(user, cls.SCOPED_APPROVER_ROLES))

    @classmethod
    def can_create(cls, user: Any, *, original_assignment: PhanCongCaTruc | None = None, requester: NhanVien | None = None) -> ShiftChangePermissionDecision:
        """Employees may create only their own shift-change request."""
        staff = cls._staff_profile(user)
        if staff is None:
            return cls._deny(str(_("Tài khoản chưa liên kết hồ sơ nhân viên.")), "NO_EMPLOYEE_PROFILE")
        requester = requester or staff
        if requester.pk != staff.pk:
            return cls._deny(str(_("Nhân viên chỉ được tạo yêu cầu đổi ca của chính mình.")), "CREATE_NOT_SELF")
        if original_assignment is not None and original_assignment.nhan_vien_id != staff.pk:
            return cls._deny(str(_("Nhân viên chỉ được tạo yêu cầu từ ca trực của chính mình.")), "ORIGINAL_SHIFT_NOT_SELF")
        return cls._allow("create_own_request")

    @classmethod
    def can_approve(cls, user: Any, shift_request: ShiftChangeRequest) -> ShiftChangePermissionDecision:
        if not cls._is_authenticated(user):
            return cls._deny(str(_("Bạn cần đăng nhập để duyệt yêu cầu đổi ca.")), "NOT_AUTHENTICATED")
        requester_user_id = getattr(getattr(shift_request, "nguoi_yeu_cau", None), "user_id", None)
        if requester_user_id and requester_user_id == getattr(user, "pk", None):
            return cls._deny(str(_("Người tạo yêu cầu không được tự duyệt yêu cầu đổi ca của mình.")), "SELF_APPROVAL_DENIED")
        if cls._has_global_operations_role(user):
            return cls._allow("global_operations_approver")
        if has_role(user, "ke_toan") and not cls._has_scoped_operations_role(user):
            return cls._deny(str(_("Vai trò kế toán không được duyệt đổi ca nếu không có vai trò vận hành.")), "ACCOUNTING_ROLE_NOT_OPERATIONAL")
        if cls._has_scoped_operations_role(user):
            site_ids = cls._relevant_site_ids(shift_request)
            if not site_ids:
                return cls._deny(str(_("Yêu cầu đổi ca chưa có mục tiêu để xác định phạm vi duyệt.")), "NO_SITE_SCOPE")
            managed_ids = set(SiteVisibilityPolicy.managed_sites(user).values_list("pk", flat=True))
            if site_ids.issubset(managed_ids):
                return cls._allow("managed_site_scope")
            return cls._deny(str(_("Yêu cầu đổi ca nằm ngoài mục tiêu/vùng bạn quản lý.")), "OUT_OF_MANAGED_SCOPE")
        return cls._deny(str(_("Bạn không có quyền vận hành để duyệt yêu cầu đổi ca.")), "MISSING_OPERATIONAL_ROLE")

    @classmethod
    def can_apply(cls, user: Any, shift_request: ShiftChangeRequest) -> ShiftChangePermissionDecision:
        """Apply has at least the same authorization bar as approval."""
        return cls.can_approve(user, shift_request)

    @classmethod
    def can_view_swap_rate_report(cls, user: Any) -> ShiftChangePermissionDecision:
        """Report scope is operational, not accounting/employee self-service."""
        if not cls._is_authenticated(user):
            return cls._deny(str(_("Bạn cần đăng nhập để xem báo cáo đổi ca.")), "NOT_AUTHENTICATED")
        if getattr(user, "is_superuser", False) or has_role(user, cls.REPORT_GLOBAL_ROLES):
            return cls._allow("global_swap_rate_report")
        if has_role(user, "ke_toan") and not has_role(user, cls.REPORT_SCOPED_ROLES + cls.REPORT_GLOBAL_ROLES):
            return cls._deny(str(_("Kế toán không có vai trò vận hành không được xem báo cáo đổi ca.")), "ACCOUNTING_ROLE_NOT_OPERATIONAL")
        if has_role(user, cls.REPORT_SCOPED_ROLES):
            return cls._allow("scoped_swap_rate_report")
        return cls._deny(str(_("Bạn không có quyền vận hành để xem báo cáo đổi ca.")), "MISSING_OPERATIONAL_ROLE")

    @classmethod
    def allowed_sites_for_swap_rate_report(cls, user: Any):
        """Return a tenant-scoped MucTieu queryset or raise PermissionDenied."""
        decision = cls.can_view_swap_rate_report(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)
        if getattr(user, "is_superuser", False) or has_role(user, cls.REPORT_GLOBAL_ROLES):
            from clients.models import MucTieu

            return MucTieu.objects.for_tenant(SiteVisibilityPolicy._organization_id()).distinct()
        return SiteVisibilityPolicy.managed_sites(user).distinct()

    @classmethod
    def enforce_create(cls, user: Any, *, original_assignment: PhanCongCaTruc | None = None, requester: NhanVien | None = None) -> None:
        decision = cls.can_create(user, original_assignment=original_assignment, requester=requester)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_approve(cls, user: Any, shift_request: ShiftChangeRequest) -> None:
        decision = cls.can_approve(user, shift_request)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_apply(cls, user: Any, shift_request: ShiftChangeRequest) -> None:
        decision = cls.can_apply(user, shift_request)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_swap_rate_report(cls, user: Any) -> None:
        decision = cls.can_view_swap_rate_report(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)
