<<<<<<< HEAD
import logging
=======
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/apps.py
Author: Mr. Anh (CTO)
Updated Date: 2026-03-21
Description: Cấu hình ứng dụng Quản trị nhân sự (Users App).
             UPGRADE: Kích hoạt hệ thống Signals để tự động gán Roles.
"""
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

<<<<<<< HEAD

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = _("4. Quản trị nhân sự")

    def ready(self):
        try:
            import users.signals
        except ImportError as exc:
            logger.error("[SCMD-SYSTEM] Không thể kích hoạt signals trong app users: %s", exc)
=======
class UsersConfig(AppConfig):
    """
    Cấu hình App Users: Quản lý tài khoản, Profile và Phân quyền.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    
    # Hiển thị tên App đẹp mắt trong trang Django Admin/Jazzmin
    verbose_name = _("4. QUẢN TRỊ NHÂN SỰ (HR)")

    def ready(self):
        """
        Hàm ready() được gọi khi Django khởi động. 
        Đây là nơi bắt buộc để import signals nhằm kích hoạt các trình lắng nghe sự kiện.
        """
        try:
            # Import signals để bắt đầu lắng nghe sự kiện tạo User
            import users.signals
            
            # Log nhẹ để xác nhận hệ thống phân quyền đã online (tùy chọn)
            # print("SCMD System: User Signals & RBAC activated successfully.")
            
        except ImportError as e:
            # Xử lý lỗi nếu file signals bị lỗi cú pháp hoặc thiếu file
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[SCMD-SYSTEM] Không thể kích hoạt Signals trong app users: {str(e)}")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
