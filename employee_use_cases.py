# -*- coding: utf-8 -*-
"""
Application Layer: Employee Use Cases.
Quy tắc: Điều phối logic nghiệp vụ tuyển dụng, tạo mã NV SSOT, tạo tài khoản.
"""
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from django.utils import timezone
from users.models import NhanVien, CauHinhMaNhanVien
from core.infrastructure.security import encrypt_aes256
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging
from django.conf import settings

from main.models import AuditLog

logger = logging.getLogger(__name__)

class HireEmployeeUseCase:
    """
    Nghiệp vụ tiếp nhận nhân viên mới.
    Bao gồm: Tạo User, Tạo Profile, Sinh mã NV duy nhất.
    """
    @staticmethod
    @transaction.atomic
    def execute(ho_ten, so_cccd, so_tai_khoan, tenant_id, phong_ban_id=None, chuc_danh_id=None, email=None):
        # 1. Sinh mã nhân viên an toàn (Database Lock)
        config = CauHinhMaNhanVien.objects.select_for_update().first()
        if not config:
            config = CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
        
        config.so_hien_tai += 1
        config.save()
        ma_nv = f"{config.tien_to}{str(config.so_hien_tai).zfill(config.do_dai_so)}"

        # 2. Tạo User hệ thống (Username = Mã NV)
        password = User.objects.make_random_password()
        try:
            user = User.objects.create_user(
                username=ma_nv, 
                password=password, 
                email=email,
                first_name=ho_ten.split(' ')[-1],
                last_name=" ".join(ho_ten.split(' ')[:-1])
            )
        except IntegrityError:
            logger.error(f"User {ma_nv} already exists.")
            raise

        # 3. Tạo Profile NhanVien (Infrastructure)
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

        logger.info(f"Hiring success: {ma_nv} for tenant {tenant_id}")
        return nhan_vien

class LockResignedEmployeeUseCase:
    """
    Nghiệp vụ tự động khóa hồ sơ nhân sự đã nghỉ việc.
    Quy tắc: Khóa tài khoản User sau 30 ngày kể từ ngày nghỉ việc.
    """
    @staticmethod
    def execute():
        today = timezone.now().date()
        lock_date_threshold = today - timedelta(days=30)
        
        # Tìm nhân viên đã nghỉ việc đủ 30 ngày và tài khoản User vẫn đang hoạt động
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
                    
                    # Ghi Audit Log tập trung
                    AuditLog.objects.create(
                        action=AuditLog.Action.UPDATE,
                        module='users',
                        model_name='NhanVien',
                        object_id=str(nv.pk),
                        tenant_id=settings.SCMD_ORGANIZATION_ID,
                        note=f"Tự động khóa hồ sơ nhân sự (Ngày nghỉ: {nv.ngay_nghi_viec})",
                        status='SUCCESS'
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to auto-lock employee {nv.ma_nhan_vien}: {str(e)}")
        
        # Gửi thông báo WebSocket tới bộ phận HR nếu có hồ sơ bị khóa
        if count > 0:
            payload = {
                "title": "Khóa hồ sơ tự động",
                "message": f"Hệ thống vừa tự động khóa {count} hồ sơ nhân sự đã nghỉ việc quá 30 ngày.",
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

            # Lưu vào AuditLog để có thể truy vấn lịch sử qua API
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
