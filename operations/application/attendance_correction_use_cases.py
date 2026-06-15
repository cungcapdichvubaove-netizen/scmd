# -*- coding: utf-8 -*-
"""
Application Layer: Attendance correction use case.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from core.audit_context import allow_attendance_mutation
from main.models import AuditLog
from operations.models import ChamCong, ChamCongAdjustment
from accounting.application.payroll_lock_policy import PayrollLockPolicy


class CorrectAttendanceUseCase:
    """SSOT cho mọi chỉnh sửa chấm công nhạy cảm."""

    TRACKED_STATE_FIELDS = (
        "thoi_gian_check_in",
        "thoi_gian_check_out",
        "thuc_lam_gio",
        "ghi_chu",
        "location_check_in",
        "location_check_out",
    )

    @classmethod
    def _serialize_state(cls, cham_cong):
        return {
            "thoi_gian_check_in": cham_cong.thoi_gian_check_in.isoformat() if cham_cong.thoi_gian_check_in else None,
            "thoi_gian_check_out": cham_cong.thoi_gian_check_out.isoformat() if cham_cong.thoi_gian_check_out else None,
            "thuc_lam_gio": cham_cong.thuc_lam_gio,
            "ghi_chu": cham_cong.ghi_chu,
            "location_check_in": cham_cong.location_check_in.wkt if cham_cong.location_check_in else None,
            "location_check_out": cham_cong.location_check_out.wkt if cham_cong.location_check_out else None,
        }

    @classmethod
    def execute(cls, *, cham_cong_id, candidate, changed_fields, reason, actor_user=None):
        if not reason or not reason.strip():
            raise ValidationError("Phải nhập lý do điều chỉnh khi sửa dữ liệu chấm công.")

        with transaction.atomic():
            # Khóa bản ghi gốc để mọi correction đi qua cùng một transaction boundary.
            persisted = ChamCong.objects.select_for_update().select_related("ca_truc").get(pk=cham_cong_id)
            payroll_period = PayrollLockPolicy.enforce_attendance_mutable(persisted)

            before_state = cls._serialize_state(persisted)
            for field_name in changed_fields:
                setattr(persisted, field_name, getattr(candidate, field_name))

            with allow_attendance_mutation("ATTENDANCE_CORRECTION_USE_CASE"):
                persisted.save()
            after_state = cls._serialize_state(persisted)
            actor = getattr(actor_user, "nhan_vien", None) if actor_user else None

            ChamCongAdjustment.objects.create(
                cham_cong=persisted,
                bang_luong=payroll_period,
                nguoi_dieu_chinh=actor,
                ly_do=reason.strip(),
                truoc_dieu_chinh=before_state,
                sau_dieu_chinh=after_state,
            )
            AuditLog.objects.create(
                user=actor_user,
                action=AuditLog.Action.UPDATE,
                module="operations",
                model_name="ChamCong",
                object_id=str(persisted.pk),
                tenant_id=persisted.tenant_id,
                note=f"Manual correction chấm công qua use case: {reason.strip()}",
                changes={
                    "correction_type": "MANUAL_ATTENDANCE_CORRECTION",
                    "changed_fields": list(changed_fields),
                    "reason": reason.strip(),
                    "payroll_period_id": payroll_period.pk if payroll_period else None,
                    "payroll_period_state": payroll_period.trang_thai if payroll_period else None,
                    "before": before_state,
                    "after": after_state,
                },
                status="SUCCESS",
            )
            return persisted
