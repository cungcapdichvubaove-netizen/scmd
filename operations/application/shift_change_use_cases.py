# -*- coding: utf-8 -*-
"""Phase C workflow use cases for shift-change integration.

``ShiftChangeRequest`` is the SSOT for đổi ca/tăng ca/hủy ca. Generic
field-proposal records remain outside this roster workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounting.application.payroll_lock_policy import PayrollLockPolicy
from main.models import AuditLog
from operations.models import ChamCong, PhanCongCaTruc, ShiftChangeRequest
from users.models import ACTIVE_EMPLOYEE_STATUSES
from operations.application.shift_change_permission_policy import ShiftChangePermissionPolicy


@dataclass(frozen=True)
class AppliedShiftChangeResult:
    assignment_id: int | None
    action: str
    message: str


@dataclass(frozen=True)
class ApprovedShiftChangeResult:
    request_id: int
    status: str
    message: str


class ApproveShiftChangeRequestUseCase:
    """Approve a pending shift-change request with business authorization."""

    @classmethod
    def execute(cls, request_id: int, *, actor=None, tenant_id=None, note="") -> ApprovedShiftChangeResult:
        with transaction.atomic():
            qs = ShiftChangeRequest.objects
            if tenant_id:
                qs = qs.for_tenant(tenant_id)
            request = qs.select_for_update().select_related(
                "nguoi_yeu_cau__user",
                "phan_cong_goc__vi_tri_chot__muc_tieu",
                "vi_tri_mong_muon__muc_tieu",
            ).get(pk=request_id)

            ShiftChangePermissionPolicy.enforce_approve(actor, request)
            if request.trang_thai != ShiftChangeRequest.TrangThai.PENDING_APPROVAL:
                raise ValidationError(_("Chỉ được duyệt yêu cầu đổi ca đang chờ duyệt."))
            request.transition_status(
                ShiftChangeRequest.TrangThai.APPROVED,
                actor=actor,
                note=note or "Shift-change request approved through authorized use case",
            )
            return ApprovedShiftChangeResult(request.pk, request.trang_thai, "Đã duyệt yêu cầu đổi ca.")


class ApplyShiftChangeRequestUseCase:
    """Apply an already-approved shift-change request to ``PhanCongCaTruc``.

    Guardrails:
    - payroll period for source/target work date must be mutable;
    - no attendance may already exist on the original assignment;
    - target employee must be active;
    - target employee/date/shift must not conflict with an existing assignment;
    - every apply writes an AuditLog.
    """

    @staticmethod
    def _active_staff_or_raise(staff):
        if staff is None or staff.trang_thai_lam_viec not in ACTIVE_EMPLOYEE_STATUSES:
            raise ValidationError(_("Nhân viên áp dụng đổi ca phải đang active/thử việc."))
        return staff

    @staticmethod
    def _has_attendance(assignment):
        if not assignment or not assignment.pk:
            return False
        return ChamCong.objects.filter(ca_truc=assignment).exists()

    @staticmethod
    def _target_assignment_values(request: ShiftChangeRequest, original=None):
        target_staff = request.nhan_vien_thay_the or (original.nhan_vien if original else request.nguoi_yeu_cau)
        target_date = request.ngay_mong_muon or (original.ngay_truc if original else None)
        target_shift = request.ca_mong_muon or (original.ca_lam_viec if original else None)
        target_post = request.vi_tri_mong_muon or (original.vi_tri_chot if original else None)
        if not target_date or not target_shift or not target_post:
            raise ValidationError(_("Yêu cầu đổi ca chưa đủ ngày/ca/vị trí để áp dụng."))
        return target_staff, target_date, target_shift, target_post

    @staticmethod
    def _enforce_no_conflict(*, tenant_id, staff, work_date, shift, exclude_assignment_id=None):
        qs = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            nhan_vien=staff,
            ngay_truc=work_date,
            ca_lam_viec=shift,
        )
        if exclude_assignment_id:
            qs = qs.exclude(pk=exclude_assignment_id)
        if qs.exists():
            raise ValidationError(_("Nhân viên đã có phân công trùng ngày/ca."))

    @staticmethod
    def _audit_apply(request, *, actor=None, assignment=None, action="apply", changes=None):
        return AuditLog.objects.create(
            user=actor if getattr(actor, "is_authenticated", False) else None,
            action=AuditLog.Action.EXECUTE,
            module="operations",
            model_name="ShiftChangeRequest",
            object_id=str(request.pk),
            tenant_id=request.tenant_id,
            note="Apply approved shift-change request into PhanCongCaTruc",
            changes={
                "workflow_apply": action,
                "ma_yeu_cau": request.ma_yeu_cau,
                "assignment_id": getattr(assignment, "pk", None),
                **(changes or {}),
            },
        )

    @classmethod
    def execute(cls, request_id: int, *, actor=None, tenant_id=None) -> AppliedShiftChangeResult:
        scoped_tenant = tenant_id
        with transaction.atomic():
            qs = ShiftChangeRequest.objects
            if scoped_tenant:
                qs = qs.for_tenant(scoped_tenant)
            request = qs.select_for_update().select_related(
                "nguoi_yeu_cau",
                "phan_cong_goc__nhan_vien",
                "phan_cong_goc__ca_lam_viec",
                "phan_cong_goc__vi_tri_chot",
                "ca_mong_muon",
                "vi_tri_mong_muon",
                "nhan_vien_thay_the",
            ).get(pk=request_id)

            ShiftChangePermissionPolicy.enforce_apply(actor, request)
            if request.trang_thai != ShiftChangeRequest.TrangThai.APPROVED:
                raise ValidationError(_("Chỉ áp dụng yêu cầu đổi ca đã được duyệt và chưa áp dụng."))

            original = request.phan_cong_goc
            if original:
                PayrollLockPolicy.enforce_assignment_mutable(original)
                if cls._has_attendance(original):
                    raise ValidationError(_("Ca gốc đã có chấm công, không được áp dụng đổi ca trực tiếp."))

            if request.loai_yeu_cau == ShiftChangeRequest.LoaiYeuCau.CANCEL_SHIFT:
                if not original:
                    raise ValidationError(_("Yêu cầu hủy ca phải có phân công gốc."))
                assignment_id = original.pk
                original.delete()
                cls._audit_apply(request, actor=actor, assignment=None, action="cancel_shift", changes={"cancelled_assignment_id": assignment_id})
                request.transition_status(
                    ShiftChangeRequest.TrangThai.APPLIED,
                    actor=actor,
                    note="Shift-change request applied into roster",
                )
                return AppliedShiftChangeResult(None, "cancel_shift", "Đã hủy phân công theo yêu cầu được duyệt.")

            target_staff, target_date, target_shift, target_post = cls._target_assignment_values(request, original=original)
            cls._active_staff_or_raise(target_staff)
            tenant = request.tenant_id
            transient = PhanCongCaTruc(
                tenant_id=tenant,
                nhan_vien=target_staff,
                ngay_truc=target_date,
                ca_lam_viec=target_shift,
                vi_tri_chot=target_post,
            )
            PayrollLockPolicy.enforce_assignment_mutable(transient)

            exclude_id = original.pk if original else None
            cls._enforce_no_conflict(
                tenant_id=tenant,
                staff=target_staff,
                work_date=target_date,
                shift=target_shift,
                exclude_assignment_id=exclude_id,
            )

            if request.loai_yeu_cau == ShiftChangeRequest.LoaiYeuCau.OVERTIME or original is None:
                assignment = PhanCongCaTruc.objects.create(
                    tenant_id=tenant,
                    nhan_vien=target_staff,
                    ngay_truc=target_date,
                    ca_lam_viec=target_shift,
                    vi_tri_chot=target_post,
                )
                action = "create_overtime_assignment"
            else:
                assignment = original
                before = {
                    "nhan_vien_id": original.nhan_vien_id,
                    "ngay_truc": original.ngay_truc.isoformat(),
                    "ca_lam_viec_id": original.ca_lam_viec_id,
                    "vi_tri_chot_id": original.vi_tri_chot_id,
                }
                assignment.nhan_vien = target_staff
                assignment.ngay_truc = target_date
                assignment.ca_lam_viec = target_shift
                assignment.vi_tri_chot = target_post
                assignment.save(update_fields=["nhan_vien", "ngay_truc", "ca_lam_viec", "vi_tri_chot", "tenant_id"])
                action = "update_assignment"
                cls._audit_apply(
                    request,
                    actor=actor,
                    assignment=assignment,
                    action=action,
                    changes={
                        "before": before,
                        "after": {
                            "nhan_vien_id": assignment.nhan_vien_id,
                            "ngay_truc": assignment.ngay_truc.isoformat(),
                            "ca_lam_viec_id": assignment.ca_lam_viec_id,
                            "vi_tri_chot_id": assignment.vi_tri_chot_id,
                        },
                    },
                )
                request.transition_status(
                    ShiftChangeRequest.TrangThai.APPLIED,
                    actor=actor,
                    note="Shift-change request applied into roster",
                )
                return AppliedShiftChangeResult(assignment.pk, action, "Đã cập nhật phân công ca trực.")

            cls._audit_apply(request, actor=actor, assignment=assignment, action=action)
            request.transition_status(
                ShiftChangeRequest.TrangThai.APPLIED,
                actor=actor,
                note="Shift-change request applied into roster",
            )
            return AppliedShiftChangeResult(assignment.pk, action, "Đã tạo/cập nhật phân công ca trực.")


class LeaveScheduleConflictUseCase:
    """Find approved leave requests that overlap planned shifts."""

    @staticmethod
    def execute(*, tenant_id, target_date=None, start_date=None, end_date=None, target_scope_qs=None, max_results=None):
        from users.models import DonNghiPhep

        if target_date:
            start_date = end_date = target_date
        if not start_date or not end_date:
            today = timezone.localdate()
            start_date = start_date or today
            end_date = end_date or today

        leave_qs = DonNghiPhep.objects.for_tenant(tenant_id).filter(
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
            tu_ngay__lte=end_date,
            den_ngay__gte=start_date,
        ).select_related("nhan_vien")

        # Evaluate approved leaves once. The previous implementation queried the
        # same leave queryset for staff ids and then iterated it again. For the
        # dashboard day/range check this keeps the business meaning but removes a
        # duplicated DonNghiPhep query.
        leaves = list(leave_qs)
        if not leaves:
            return []

        staff_ids = {leave.nhan_vien_id for leave in leaves}
        assignments = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            nhan_vien_id__in=staff_ids,
            ngay_truc__gte=start_date,
            ngay_truc__lte=end_date,
        ).select_related("nhan_vien", "ca_lam_viec", "vi_tri_chot__muc_tieu")
        if target_scope_qs is not None:
            assignments = assignments.filter(vi_tri_chot__muc_tieu__in=target_scope_qs)

        leaves_by_staff = {}
        for leave in leaves:
            leaves_by_staff.setdefault(leave.nhan_vien_id, []).append(leave)

        conflicts = []
        for assignment in assignments.iterator():
            for leave in leaves_by_staff.get(assignment.nhan_vien_id, []):
                if leave.tu_ngay <= assignment.ngay_truc <= leave.den_ngay:
                    conflicts.append({
                        "assignment_id": assignment.pk,
                        "leave_id": leave.pk,
                        "ma_don": leave.ma_don,
                        "loai_nghi": leave.loai_nghi,
                        "nhan_vien_id": assignment.nhan_vien_id,
                        "nhan_vien": assignment.nhan_vien.ho_ten,
                        "ngay_truc": assignment.ngay_truc.isoformat(),
                        "ca": getattr(assignment.ca_lam_viec, "ten_ca", ""),
                        "muc_tieu": getattr(assignment.vi_tri_chot.muc_tieu, "ten_muc_tieu", ""),
                        "severity": "WARNING",
                        "message": "Nhân viên có đơn nghỉ phép đã duyệt trùng lịch trực; cần điều phối lại.",
                    })
                    if max_results and len(conflicts) >= max_results:
                        return conflicts
        return conflicts
