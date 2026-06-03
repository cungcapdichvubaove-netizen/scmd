# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: inventory/signals.py
Author: Principal Software Architect
Version: v2.0.0.6
Description: Tín hiệu hệ thống xử lý Invalidation Cache cho Kho.
             Đảm bảo tính nhất quán giữa dữ liệu thực và Dashboard (SSOT).
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import PhieuNhap, ChiTietPhieuNhap, PhieuXuat, ChiTietPhieuXuat

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=PhieuNhap)
@receiver([post_save, post_delete], sender=ChiTietPhieuNhap)
@receiver([post_save, post_delete], sender=PhieuXuat)
@receiver([post_save, post_delete], sender=ChiTietPhieuXuat)
def invalidate_inventory_dashboard_cache(sender, instance, **kwargs):
    """
    Xóa toàn bộ cache dashboard vật tư khi có bất kỳ biến động kho nào.
    Nguyên tắc: Stability First & Source of Truth.
    """
    try:
        # Pattern này khớp với logic key tại inventory/views.py:
        # cache_key = f"inventory_dashboard_stats_u{request.user.id}"
        cache.delete_pattern("inventory_dashboard_stats_u*")
        logger.info(f"[Cache-Invalidation] Đã xóa cache Dashboard Kho do thay đổi tại {sender.__name__}")
    except Exception as e:
        # Đảm bảo lỗi cache không làm gián đoạn luồng nghiệp vụ chính (Persistence)
        logger.error(f"[Cache-Error] Lỗi khi xóa cache Dashboard: {str(e)}")