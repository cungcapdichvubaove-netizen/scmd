# -*- coding: utf-8 -*-
"""Use case for append-only payroll adjustments after payroll lock."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.models import BangLuongThang, ChiTietLuong, PayrollAdjustment
from main.models import AuditLog
from users.models import NhanVien


class CreatePayrollAdjustmentUseCase:
    """Create a retroactive payroll adjustment without mutating locked payslips."""

    @staticmethod
    def execute(
        *,
        bang_luong_id: int,
        nhan_vien_id: int,
        so_tien_dieu_chinh,
        ly_do: str,
        actor_user=None,
        tenant_id=None,
        chi_tiet_luong_id: int | None = None,
        metadata: dict | None = None,
    ) -> PayrollAdjustment:
        scoped_tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        amount = Decimal(str(so_tien_dieu_chinh))
        reason = (ly_do or "").strip()
        if not reason:
            raise ValidationError("Lý do điều chỉnh lương là bắt buộc.")

        with transaction.atomic():
            payroll = (
                BangLuongThang.objects.for_tenant(scoped_tenant_id)
                .select_for_update()
                .get(pk=bang_luong_id)
            )
            if not payroll.is_locked:
                raise ValidationError(
                    "Chỉ tạo điều chỉnh hồi tố cho kỳ lương đã LOCKED/PAID."
                )

            employee = NhanVien.objects.for_tenant(scoped_tenant_id).get(pk=nhan_vien_id)
            payslip = None
            if chi_tiet_luong_id:
                payslip = (
                    ChiTietLuong.objects.for_tenant(scoped_tenant_id)
                    .select_related("bang_luong", "nhan_vien")
                    .get(pk=chi_tiet_luong_id)
                )

            adjustment = PayrollAdjustment(
                tenant_id=scoped_tenant_id,
                bang_luong=payroll,
                chi_tiet_luong=payslip,
                nhan_vien=employee,
                so_tien_dieu_chinh=amount,
                ly_do=reason,
                metadata=metadata or {},
                created_by=actor_user if getattr(actor_user, "is_authenticated", False) else None,
            )
            adjustment.save()

            AuditLog.objects.create(
                tenant_id=scoped_tenant_id,
                user=adjustment.created_by,
                action=AuditLog.Action.CREATE,
                module="accounting",
                model_name="PayrollAdjustment",
                object_id=str(adjustment.pk),
                changes={
                    "bang_luong_id": payroll.pk,
                    "chi_tiet_luong_id": payslip.pk if payslip else None,
                    "nhan_vien_id": employee.pk,
                    "so_tien_dieu_chinh": str(amount),
                },
                note=reason,
            )
            return adjustment
