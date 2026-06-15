# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
---------
File: main/tasks.py
Description: Celery tasks chung cho toàn hệ thống.
"""

import logging

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
=======
Security Command (SCMD) System
------------------------------
File: main/tasks.py
Description: Celery Tasks chung cho toàn hệ thống.
"""

import logging
from celery import shared_task
from django.core.management import call_command
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User
import requests
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

<<<<<<< HEAD

@shared_task(bind=True, max_retries=3, default_retry_delay=3600)
def main_verify_audit_logs_daily(self):
    """
    Task chạy hằng ngày để kiểm tra tính toàn vẹn của AuditLog.
    Nếu phát hiện sai lệch, gửi báo cáo qua email cho Ban Giám đốc.
    Quy ước đặt tên: module_action_target.
    """
    try:
        logger.info("[AuditLog-Verification] Bắt đầu kiểm tra tính toàn vẹn AuditLog.")

        from main.management.commands.verify_audit_logs import Command

        command_instance = Command()
        compromised_logs = command_instance.handle()

        if compromised_logs:
            logger.critical(
                "[AuditLog-Verification] PHÁT HIỆN %s BẢN GHI AUDIT LOG BỊ SAI LỆCH!",
                len(compromised_logs),
            )

            recipients = list(
                User.objects.filter(
                    groups__name="BanGiamDoc",
                    is_active=True,
                ).values_list("email", flat=True)
            )

            if not recipients:
                logger.warning(
                    "[AuditLog-Verification] Không tìm thấy email Ban Giám đốc để gửi cảnh báo sai lệch Audit Log."
                )
                return "No recipients found for alert"

            subject = _("[SCMD] CẢNH BÁO: PHÁT HIỆN SAI LỆCH TRONG AUDIT LOG!")
            html_content = render_to_string(
                "main/emails/audit_log_compromise_report.html",
                {"compromised_logs": compromised_logs},
            )
            text_content = _(
                f"Hệ thống phát hiện {len(compromised_logs)} bản ghi Audit Log bị sai lệch. Vui lòng kiểm tra ngay."
            )

            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, recipients)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            logger.info(
                "[AuditLog-Verification] Đã gửi cảnh báo sai lệch Audit Log tới %s lãnh đạo.",
                len(recipients),
            )
            return f"Compromised logs found. Alert sent to {len(recipients)} recipients."

=======
@shared_task(bind=True, max_retries=3, default_retry_delay=3600)
def main_verify_audit_logs_daily(self):
    """
    Task chạy hàng ngày để kiểm tra tính toàn vẹn của AuditLog.
    Nếu phát hiện sai lệch, gửi báo cáo qua email cho Ban Giám đốc.
    Quy ước đặt tên (Rule 6): module_action_target
    """
    try:
        logger.info("[AuditLog-Verification] Bắt đầu kiểm tra tính toàn vẹn AuditLog.")
        
        # Gọi management command và lấy kết quả
        from main.management.commands.verify_audit_logs import Command
        command_instance = Command()
        compromised_logs = command_instance.handle() # Command đã được sửa để trả về list

        if compromised_logs:
            logger.critical(f"[AuditLog-Verification] PHÁT HIỆN {len(compromised_logs)} BẢN GHI AUDIT LOG BỊ SAI LỆCH!")
            
            # 1. Xác định danh sách nhận tin (Ban Giám đốc)
            recipients = list(User.objects.filter(
                groups__name='BanGiamDoc', # Dựa trên config/roles.py
                is_active=True
            ).values_list('email', flat=True))
            
            if not recipients:
                logger.warning("[AuditLog-Verification] Không tìm thấy email Ban Giám đốc để gửi cảnh báo sai lệch Audit Log.")
                return "No recipients found for alert"

            # 2. Render nội dung Email
            subject = _("[SCMD ERP] CẢNH BÁO: PHÁT HIỆN SAI LỆCH TRONG AUDIT LOG!")
            html_content = render_to_string(
                'main/emails/audit_log_compromise_report.html', 
                {'compromised_logs': compromised_logs}
            )
            text_content = _(f"Hệ thống phát hiện {len(compromised_logs)} bản ghi Audit Log bị sai lệch. Vui lòng kiểm tra ngay.")

            # 3. Gửi Email
            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, recipients)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            logger.info(f"[AuditLog-Verification] Đã gửi cảnh báo sai lệch Audit Log tới {len(recipients)} lãnh đạo.")
            return f"Compromised logs found. Alert sent to {len(recipients)} recipients."
        
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        logger.info("[AuditLog-Verification] Tất cả AuditLog đều hợp lệ. Không phát hiện sai lệch.")
        return "All audit logs are valid."

    except Exception as exc:
<<<<<<< HEAD
        logger.critical("[AuditLog-Verification] Lỗi hệ thống khi chạy kiểm tra AuditLog: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def main_send_fcm_notification(self, fcm_token: str, title: str, body: str, data: dict = None):
    """
    Task gửi push notification qua Firebase Cloud Messaging (FCM).
=======
        logger.critical(f"[AuditLog-Verification] Lỗi hệ thống khi chạy kiểm tra AuditLog: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def main_send_fcm_notification(self, fcm_token: str, title: str, body: str, data: dict = None):
    """
    Task gửi Push Notification qua Firebase Cloud Messaging (FCM).
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """
    if not fcm_token:
        logger.warning("[FCM] Không có FCM token để gửi thông báo.")
        return "No FCM token provided."

    if not settings.FCM_SERVER_KEY:
        logger.error("[FCM] FCM_SERVER_KEY chưa được cấu hình trong settings.")
        return "FCM_SERVER_KEY not configured."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
    }

    payload = {
        "to": fcm_token,
        "notification": {
            "title": title,
            "body": body,
            "sound": "default",
        },
        "data": data or {},
    }

    try:
<<<<<<< HEAD
        response = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers=headers,
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        logger.info("[FCM] Gửi thông báo thành công tới %s: %s", fcm_token, response.json())
        return response.json()
    except requests.exceptions.RequestException as exc:
        logger.error("[FCM] Lỗi khi gửi thông báo tới %s: %s", fcm_token, exc)
        raise self.retry(exc=exc)
=======
        response = requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, json=payload, timeout=5)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"[FCM] Gửi thông báo thành công tới {fcm_token}: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"[FCM] Lỗi khi gửi thông báo tới {fcm_token}: {e}")
        raise self.retry(exc=e)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
