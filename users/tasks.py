# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
File: users/tasks.py
Description: Celery Tasks cho module Nhân sự (HR).
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User
from users.application.employee_use_cases import LockResignedEmployeeUseCase

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def send_monthly_hr_turnover_report_async(self, tenant_id=None):
    """
    Task định kỳ: Gửi báo cáo tỷ lệ biến động nhân sự hàng tháng cho Ban Giám đốc.
    Trigger: Celery Beat (thường vào ngày 01 hàng tháng).
    """
    try:
        # 1. Xác định kỳ báo cáo (tháng trước)
        today = timezone.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        month = last_day_last_month.month
        year = last_day_last_month.year
        
        if tenant_id is None:
            tenant_id = getattr(settings, 'SCMD_ORGANIZATION_ID', None)

        # 2. Lấy dữ liệu từ Use Case (Application Layer)
        from users.application.hr_analytics_use_cases import HRAnalyticsUseCase
        report_data = HRAnalyticsUseCase.get_turnover_report_by_region(month, year, tenant_id)
        
        # 3. Xác định danh sách nhận tin (Ban Giám đốc)
        # Dựa trên role system trong config/roles.py
        recipients = list(User.objects.filter(
            groups__name='BanGiamDoc', 
            is_active=True
        ).values_list('email', flat=True))
        
        if not recipients:
            logger.warning(f"[HR-Analytics] Không tìm thấy email Ban Giám đốc để gửi báo cáo tháng {month}/{year}")
            return "No recipients found"

        # 4. Render nội dung Email
        subject = f"[SCMD ERP] Báo cáo Biến động Nhân sự - Tháng {month}/{year}"
        html_content = render_to_string(
            'users/emails/hr_turnover_report.html', 
            {'report': report_data}
        )
        text_content = f"Báo cáo biến động nhân sự tháng {month}/{year} đã sẵn sàng trên Dashboard."

        # 5. Gửi Email
        msg = EmailMultiAlternatives(
            subject, 
            text_content, 
            settings.DEFAULT_FROM_EMAIL, 
            recipients
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"[HR-Analytics] Đã gửi báo cáo tháng {month}/{year} thành công tới {len(recipients)} lãnh đạo.")
        return f"Report sent to {len(recipients)} users"

    except Exception as e:
        logger.error(f"[HR-Analytics] Lỗi khi gửi báo cáo: {str(e)}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.critical(f"[HR-Analytics] Không thể gửi báo cáo tháng {month}/{year} sau nhiều lần thử.")
            return "Failed after retries"

@shared_task
def auto_lock_resigned_employees_task():
    """
    Task chạy hàng ngày để quét và khóa hồ sơ nhân sự đã nghỉ việc > 30 ngày.
    """
    logger.info("[HR-Task] Bắt đầu quét hồ sơ nhân sự đã nghỉ việc để khóa tài khoản.")
    count = LockResignedEmployeeUseCase.execute()
    msg = f"[HR-Task] Đã tự động khóa {count} hồ sơ nhân sự."
    logger.info(msg)
    return msg
