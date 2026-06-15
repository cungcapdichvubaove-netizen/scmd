# -*- coding: utf-8 -*-
"""
Application Layer: Notification Use Cases.
Description: Xử lý đăng ký thiết bị và thông báo.
"""

import logging
from main.decorators import application_audit_log
from main.models import AuditLog

logger = logging.getLogger(__name__)

class UpdateFCMTokenUseCase:
    """
    UseCase: Cập nhật FCM Token cho nhân viên.
    Đảm bảo ghi log để theo dõi thiết bị truy cập.
    """
    @staticmethod
    @application_audit_log(module='users', model_name='NhanVien', action=AuditLog.Action.UPDATE)
    def execute(user, fcm_token, **kwargs):
        if not hasattr(user, 'nhan_vien'):
            raise ValueError("Tài khoản người dùng không liên kết với hồ sơ nhân viên.")
        
        nv = user.nhan_vien
        nv.fcm_token = fcm_token
        nv.save()
        
        return nv