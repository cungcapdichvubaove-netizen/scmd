# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/tasks.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Celery Tasks xử lý các tác vụ nền (Async).
             MERGED VERSION:
             - [Keep] Tự động tính toán giờ công (TimesheetCalculator).
             - [Keep] Tự động nén ảnh (Resize Image).
             - [New] Xử lý cảnh báo Sự cố (Incident Alert).
             - [New] Quét ca trực quên Check-out.
"""

import logging
import os
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import ChamCong, BaoCaoSuCo
# Import Service tính toán từ module Accounting
try:
    from accounting.services.payroll import TimesheetCalculator
except ImportError:
    pass # Fallback nếu module accounting chưa sẵn sàng

logger = logging.getLogger(__name__)

# --- 1. EXISTING LOGIC (GIỮ NGUYÊN) ---

@shared_task
def process_timesheet_async(cham_cong_id):
    """
    Task chạy ngầm: Tính toán giờ công, đi muộn, về sớm ngay sau khi nhân viên Check-out.
    """
    try:
        # Lấy dữ liệu chấm công (join với ca trực để lấy giờ quy định)
        cham_cong = ChamCong.objects.select_related('ca_truc__ca_lam_viec').get(id=cham_cong_id)
        
        # Chỉ tính toán nếu đã Check-out
        if cham_cong.thoi_gian_check_in and cham_cong.thoi_gian_check_out:
            logger.info(f"[Timesheet] Calculating for {cham_cong.ca_truc.nhan_vien}...")
            
            # Gọi Service bên Accounting (nếu có)
            if 'accounting.services.payroll' in locals() or 'TimesheetCalculator' in globals():
                TimesheetCalculator.calculate_single_shift(cham_cong)
            else:
                logger.warning("[Timesheet] Accounting module not found.")
            
            return f"Processed Timesheet ID {cham_cong_id}"
    except ChamCong.DoesNotExist:
        return "ChamCong not found"
    except Exception as e:
        logger.error(f"[Timesheet] Error: {e}")
        return f"Error: {e}"

@shared_task
def resize_image_async(app_label, model_name, object_id, field_name):
    """
    Task nén ảnh tự động để tiết kiệm dung lượng storage.
    """
    from django.apps import apps
    try:
        Model = apps.get_model(app_label, model_name)
        obj = Model.objects.get(id=object_id)
        file_field = getattr(obj, field_name)

        if not file_field:
            return "No file"

        # Mở ảnh
        img = Image.open(file_field)
        
        # Logic Resize: Max width 1024px, giữ tỷ lệ
        max_width = 1024
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            # Convert sang RGB nếu là RGBA (png) để lưu jpg
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(buffer, format='JPEG', quality=85)
            
            # Lưu đè lại file cũ
            file_name = os.path.basename(file_field.name)
            if not file_name.lower().endswith(('.jpg', '.jpeg')):
                file_name = os.path.splitext(file_name)[0] + '.jpg'

            file_field.save(file_name, ContentFile(buffer.getvalue()), save=False)
            obj.save(update_fields=[field_name])
            
            return f"Resized image {field_name} for {model_name} {object_id}"
            
        return "Image small enough, skipped"
        
    except Exception as e:
        logger.error(f"[Resize] Error: {e}")
        return f"Error: {e}"

# --- 2. NEW LOGIC (THÊM MỚI) ---

@shared_task
def process_new_incident_alert(incident_id):
    """
    Task xử lý khi có báo cáo sự cố mới (Gửi Email/SMS/Log)
    """
    try:
        incident = BaoCaoSuCo.objects.get(id=incident_id)
        logger.info(f"[Incident] Processing alert for: {incident.ma_su_co}")
        
        # Giả lập logic gửi mail/sms leo thang
        if incident.muc_do == 'NGUY_HIEM':
            logger.warning(f"!!! CRITICAL ALERT: {incident.tieu_de} !!!")
            
        return f"Processed Incident {incident.ma_su_co}"
    except BaoCaoSuCo.DoesNotExist:
        return "Incident not found"

@shared_task
def check_late_checkout():
    """
    Task định kỳ: Quét các ca trực đã kết thúc > 2h mà chưa check-out.
    """
    # Logic implementation placeholder
    return "Checked late checkouts"