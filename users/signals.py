# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/signals.py
Author: Mr. Anh (CTO)
Updated Date: 2026-03-21
Description: Tự động hóa gán vai trò (Roles) khi khởi tạo tài khoản nhân sự.
             UPGRADE: Bổ sung Error Handling và Safe-Role Assignment.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from rolepermissions.roles import assign_role
from rolepermissions.exceptions import RoleDoesNotExist
from config.roles import NhanVienBaoVe, DoiTruong, QuanLyVung, BanGiamDoc

# Thiết lập logger để theo dõi việc gán quyền trong hệ thống SCMD
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def save_user_role(sender, instance, created, **kwargs):
    """
    Tự động gán quyền dựa trên domain email hoặc chức vụ trong Profile khi User được tạo mới.
    """
    if created:
        # 1. Trích xuất domain email một cách an toàn
        email_domain = ""
        if instance.email and '@' in instance.email:
            email_domain = instance.email.split('@')[-1].lower()
        
        target_role = 'nhan_vien_bao_ve'  # Vai trò mặc định (Fallback)

        # 2. Logic phân loại vai trò
        try:
            if email_domain == 'scmd.vn':
                target_role = 'ban_giam_doc'
            elif hasattr(instance, 'profile') and instance.profile:
                # Kiểm tra chức vụ từ Model Profile (nếu có liên kết)
                chuc_vu = getattr(instance.profile, 'chuc_vu', None)
                if chuc_vu == 'DOI_TRUONG':
                    target_role = 'doi_truong'
                elif chuc_vu == 'QUAN_LY_VUNG':
                    target_role = 'quan_ly_vung'
            
            # 3. Thực hiện gán quyền vào Database
            assign_role(instance, target_role)
            logger.info(f"[SCMD-AUTH] Đã gán vai trò '{target_role}' cho người dùng: {instance.username}")

        except RoleDoesNotExist:
            logger.error(f"[SCMD-ERROR] Vai trò '{target_role}' chưa được định nghĩa trong roles.py")
        except Exception as e:
            logger.error(f"[SCMD-ERROR] Lỗi hệ thống khi gán quyền cho {instance.username}: {str(e)}")

# --- LƯU Ý CHO CTO ---
# Đảm bảo app 'users' đã được khai báo trong INSTALLED_APPS và 
# hàm ready() trong users/apps.py đã import file signals này.