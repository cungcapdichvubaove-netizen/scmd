# -*- coding: utf-8 -*-
"""Application use cases for staff dispatch/transfer."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from main.models import AuditLog
from operations.access_policies import DispatchPolicy
from users.models import LichSuCongTac


class TransferStaffUseCase:
    """Transfer a staff member from one site to another with audit trail."""

    @staticmethod
    def execute(*, user, staff, from_site, to_site, effective_date=None, reason=""):
        effective_date = effective_date or timezone.localdate()
        policy = DispatchPolicy.can_transfer_staff(
            user=user,
            staff=staff,
            from_site=from_site,
            to_site=to_site,
            effective_date=effective_date,
        )
        policy.raise_if_denied()

        with transaction.atomic():
            current_assignment = (
                LichSuCongTac.objects.select_for_update()
                .filter(nhan_vien=staff, muc_tieu=from_site, ngay_ket_thuc__isnull=True)
                .order_by("-ngay_bat_dau")
                .first()
            )
            if current_assignment is None:
                raise ValidationError("Không tìm thấy bản ghi công tác hiện tại tại nơi đi để điều động.")
            if effective_date < current_assignment.ngay_bat_dau:
                raise ValidationError("Ngày hiệu lực điều động không được trước ngày bắt đầu công tác hiện tại.")

            current_assignment.ngay_ket_thuc = effective_date - timedelta(days=1)
            current_assignment.save(update_fields=["ngay_ket_thuc"])

            new_assignment = LichSuCongTac.objects.create(
                nhan_vien=staff,
                muc_tieu=to_site,
                ngay_bat_dau=effective_date,
                quan_ly_truc_tiep=getattr(user, "nhan_vien", None),
            )

            AuditLog.objects.create(
                user=user,
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                action=AuditLog.Action.EXECUTE,
                module="operations",
                model_name="LichSuCongTac",
                object_id=str(new_assignment.pk),
                note="Điều động nhân sự giữa mục tiêu",
                changes={
                    "staff_id": staff.pk,
                    "from_site_id": getattr(from_site, "pk", None),
                    "to_site_id": getattr(to_site, "pk", None),
                    "effective_date": effective_date.isoformat(),
                    "closed_assignment_id": getattr(current_assignment, "pk", None),
                    "reason": reason,
                },
            )

        return new_assignment
