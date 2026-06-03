# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
File: accounting/tasks.py
Description: Celery Tasks cho module Kế toán (Accounting).
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from accounting.services.payroll import PayrollService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=3600)
def accounting_calculate_monthly_payroll(self):
    """
    Task tự động quyết toán lương cho tháng trước.
    Quy ước đặt tên (Rule 6): module_action_target
    Tần suất: Chạy vào ngày 1 hàng tháng qua Celery Beat.
    """
    try:
        # 1. Xác định tháng/năm cần tính (tháng vừa trôi qua)
        # Nếu hôm nay là 01/02, chúng ta cần tính lương cho tháng 01
        today = timezone.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        
        target_month = last_day_last_month.month
        target_year = last_day_last_month.year

        logger.info(f"[Payroll-Task] Bắt đầu quyết toán lương tự động cho kỳ {target_month}/{target_year}")

        # 2. Gọi Service để thực hiện nghiệp vụ
        success, message = PayrollService.tinh_luong_thang(target_month, target_year)

        if not success:
            logger.error(f"[Payroll-Task] Quyết toán thất bại: {message}")
            # Retry sau 1 tiếng nếu có lỗi logic chưa xác định
            raise self.retry(countdown=3600)

        logger.info(f"[Payroll-Task] Hoàn tất quyết toán kỳ {target_month}/{target_year}: {message}")
        return message

    except Exception as exc:
        logger.critical(f"[Payroll-Task] Lỗi hệ thống khi chạy quyết toán: {str(exc)}")
        if not isinstance(exc, self.retry_backoff):
            raise self.retry(exc=exc)
        raise exc

@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def accounting_send_debt_reminder_email_task(self):
    """
    Task định kỳ: Gửi email nhắc nhở nợ cho nhân viên có tạm ứng chưa thanh toán.
    Tần suất: Chạy hàng tuần hoặc theo cấu hình.
    """
    # Placeholder implementation as per prompt.
    # Full logic would involve querying SoQuy for outstanding TAM_UNG,
    # fetching employee emails, rendering email templates, and sending.
    logger.info("[Debt-Reminder-Task] Bắt đầu quét và gửi nhắc nhở nợ.")
    
    try:
        count_reminders_sent = 0 # Placeholder
        logger.info(f"[Debt-Reminder-Task] Hoàn tất. Đã gửi {count_reminders_sent} nhắc nhở nợ.")
        return f"Sent {count_reminders_sent} debt reminders."
    except Exception as exc:
        logger.error(f"[Debt-Reminder-Task] Lỗi khi gửi nhắc nhở nợ: {str(exc)}")
        raise self.retry(exc=exc)