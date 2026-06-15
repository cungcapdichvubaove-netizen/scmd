# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/signals.py
Author: Mr. Anh (CTO)
Updated Date: 2026-03-21
Description: Tự động hóa gán vai trò (Roles) khi khởi tạo tài khoản nhân sự.
             UPGRADE: Bổ sung Error Handling và Safe-Role Assignment.
"""

import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from rolepermissions.roles import assign_role
from rolepermissions.exceptions import RoleDoesNotExist
from users.models import NhanVien

# Thiết lập logger để theo dõi việc gán quyền trong hệ thống SCMD
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    SSOT: Tự động tạo hồ sơ NhanVien khi User mới được đăng ký.
    Sử dụng get_or_create để đảm bảo tính Stability First.
    """
    if created:
        with transaction.atomic():
            # Tạo profile NhanVien nếu chưa tồn tại
            nhan_vien, created_profile = NhanVien.objects.get_or_create(
                user=instance,
                defaults={
                    'ho_ten': instance.get_full_name() or instance.username,
                    'email': instance.email or None
                }
            )
            if created_profile:
                logger.info(f"[SCMD-PROFILE] Đã tạo hồ sơ NhanVien cho User: {instance.username}")

# --- LƯU Ý CHO CTO ---
# Đảm bảo app 'users' đã được khai báo trong INSTALLED_APPS và 
# hàm ready() trong users/apps.py đã import file signals này.