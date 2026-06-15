# -*- coding: utf-8 -*-
"""
Application Layer: Employee Use Cases.
Quy tắc: Điều phối logic nghiệp vụ tuyển dụng, tạo mã NV SSOT, tạo tài khoản.
"""
import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.infrastructure.security import encrypt_aes256
from main.models import AuditLog
from users.models import CauHinhMaNhanVien, NhanVien

logger = logging.getLogger(__name__)


class HireEmployeeUseCase:
    @staticmethod
    @transaction.atomic
    def execute(ho_ten, so_cccd, so_tai_khoan, tenant_id, phong_ban_id=None, chuc_danh_id=None, email=None):
        config = CauHinhMaNhanVien.objects.select_for_update().first()
        if not config:
            config = CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)

        config.so_hien_tai += 1
        config.save()
        ma_nv = f"{config.tien_to}{str(config.so_hien_tai).zfill(config.do_dai_so)}"

        try:
            user = User.objects.create_user(
                username=ma_nv,
                password=User.objects.make_random_password(),
                email=email,
                first_name=ho_ten.split(' ')[-1],
                last_name=" ".join(ho_ten.split(' ')[:-1]),
            )
        except IntegrityError:
            logger.error("User %s already exists.", ma_nv)
            raise

        nhan_vien = NhanVien.objects.create(
            user=user,
            ho_ten=ho_ten,
            ma_nhan_vien=ma_nv,
            so_cccd=encrypt_aes256(so_cccd),
            so_tai_khoan=encrypt_aes256(so_tai_khoan),
            phong_ban_id=phong_ban_id,
            chuc_danh_id=chuc_danh_id,
            email=email,
            ngay_vao_lam=timezone.now().date(),
            trang_thai_lam_viec='THUVIEC'
        )

        logger.info("Hiring success: %s for tenant %s", ma_nv, tenant_id)
        return nhan_vien


class LockResignedEmployeeUseCase:
    @staticmethod
    def execute():
        today = timezone.now().date()
        lock_date_threshold = today - timedelta(days=30)
        resigned_employees = NhanVien.objects.filter(
            trang_thai_lam_viec='NGHIVIEC',
            ngay_nghi_viec__lte=lock_date_threshold,
            user__is_active=True
        ).select_related('user')

        count = 0
        with transaction.atomic():
            for nv in resigned_employees:
                try:
                    nv.user.is_active = False
                    nv.user.save(update_fields=['is_active'])
                    AuditLog.objects.create(
                        action=AuditLog.Action.UPDATE,
                        module='users',
                        model_name='NhanVien',
                        object_id=str(nv.pk),
                        tenant_id=settings.SCMD_ORGANIZATION_ID,
                        note=f"Tu dong khoa ho so nhan su (Ngay nghi: {nv.ngay_nghi_viec})",
                        status='SUCCESS'
                    )
                    count += 1
                except Exception:
                    logger.exception("Failed to auto-lock employee %s", nv.ma_nhan_vien)

        if count > 0:
            payload = {
                "title": "Khoa ho so tu dong",
                "message": f"He thong vua tu dong khoa {count} ho so nhan su da nghi viec qua 30 ngay.",
                "count": count
            }

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "hr_notifications",
                {
                    "type": "hr.alert",
                    "payload": payload
                }
            )

            AuditLog.objects.create(
                action=AuditLog.Action.EXECUTE,
                module='users',
                model_name='SystemAlert',
                note='hr_alert_summary',
                changes=payload,
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                status='SUCCESS'
            )

        return count
