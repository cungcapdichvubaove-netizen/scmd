# -*- coding: utf-8 -*-
"""
Application Layer: maintenance and scheduled operations use cases.
"""

import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from main.constants import OPERATIONS_NOTIFICATION_GROUPS

from main.models import AuditLog
from operations.models import ChamCong, KiemTraQuanSo

logger = logging.getLogger(__name__)


class ExpireAliveChecksUseCase:
    @staticmethod
    def execute(now=None, tenant_id=None):
        now = now or timezone.now()
        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID

        with transaction.atomic():
            expired_qs = KiemTraQuanSo.objects.for_tenant(tenant_id).filter(
                trang_thai="PENDING",
                thoi_gian_gui_yeu_cau__lt=now - timedelta(minutes=10),
            )
            count = expired_qs.count()

            if count == 0:
                return {"count": 0, "message": "No expired checks found."}

            expired_qs.update(trang_thai="LATE")
            AuditLog.objects.create(
                action=AuditLog.Action.UPDATE,
                module="operations",
                model_name="KiemTraQuanSo",
                note=f"He thong tu dong danh dau {count} yeu cau Alive Check qua han.",
                tenant_id=tenant_id,
                status="SUCCESS",
            )

        channel_layer = get_channel_layer()
        if channel_layer:
            for group in OPERATIONS_NOTIFICATION_GROUPS:
                async_to_sync(channel_layer.group_send)(
                    group,
                    {
                        "type": "send_notification",
                        "payload": {
                            "type": "ALIVE_CHECK_EXPIRED",
                            "message": f"CANH BAO: {count} nhan su khong phan hoi Alive Check!",
                            "count": count,
                            "severity": "HIGH",
                            "timestamp": now.strftime("%H:%M:%S"),
                        },
                    },
                )

        logger.info(
            "[Alive-Check-Cleanup] Da xu ly %s ban ghi qua han tai %s",
            count,
            now,
        )
        return {"count": count, "message": f"Processed {count} expired checks."}


class AutoExpireAliveCheckUseCase:
    @staticmethod
    def execute(check_id, tenant_id=None):
        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID

        with transaction.atomic():
            check_req = (
                KiemTraQuanSo.objects.for_tenant(tenant_id)
                .select_for_update()
                .get(id=check_id)
            )

            if check_req.trang_thai != "PENDING":
                return {
                    "expired": False,
                    "message": (
                        f"Check {check_id} was already processed "
                        f"(Status: {check_req.trang_thai})."
                    ),
                }

            check_req.trang_thai = "LATE"
            check_req.save(update_fields=["trang_thai"])

            AuditLog.objects.create(
                action=AuditLog.Action.UPDATE,
                module="operations",
                model_name="KiemTraQuanSo",
                object_id=str(check_id),
                note="He thong tu dong danh dau qua han sau thoi gian cho.",
                tenant_id=tenant_id,
                status="SUCCESS",
            )

        return {"expired": True, "message": f"Check {check_id} marked as EXPIRED."}


class FlagLateCheckoutUseCase:
    AUTO_FLAG_NOTE = "[LATE_CHECKOUT_AUTO_FLAGGED]"

    @staticmethod
    def execute(now=None, tenant_id=None):
        now = now or timezone.now()
        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        late_checkout_threshold = now - timedelta(hours=2)

        late_checkouts_qs = (
            ChamCong.objects.for_tenant(tenant_id)
            .filter(
                thoi_gian_check_out__isnull=True,
                ca_truc__ngay_truc__lte=late_checkout_threshold.date(),
            )
            .select_related("ca_truc__ca_lam_viec", "ca_truc__nhan_vien")
        )

        count = 0
        with transaction.atomic():
            for cham_cong in late_checkouts_qs:
                shift_end_time = cham_cong.ca_truc.get_thoi_gian_ket_thuc_thuc_te()
                if not shift_end_time or shift_end_time >= late_checkout_threshold:
                    continue

                if FlagLateCheckoutUseCase.AUTO_FLAG_NOTE in (cham_cong.ghi_chu or ""):
                    continue

                cham_cong.ghi_chu = (
                    f"{cham_cong.ghi_chu or ''} {FlagLateCheckoutUseCase.AUTO_FLAG_NOTE}"
                ).strip()
                cham_cong.save(update_fields=["ghi_chu"])

                AuditLog.objects.create(
                    action=AuditLog.Action.UPDATE,
                    module="operations",
                    model_name="ChamCong",
                    object_id=str(cham_cong.id),
                    tenant_id=tenant_id,
                    note=(
                        "He thong tu dong danh dau LATE_CHECKOUT cho NV "
                        f"{cham_cong.ca_truc.nhan_vien.ma_nhan_vien} "
                        f"(Ca ket thuc: {shift_end_time})."
                    ),
                    status="WARNING",
                )
                logger.warning(
                    "LATE_CHECKOUT: ChamCong ID %s for %s flagged.",
                    cham_cong.id,
                    cham_cong.ca_truc.nhan_vien.ho_ten,
                )
                count += 1

        return {"count": count, "message": f"Processed {count} late checkouts."}
