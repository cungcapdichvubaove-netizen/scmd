# -*- coding: utf-8 -*-
"""
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
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


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

        logger.info("[AuditLog-Verification] Tất cả AuditLog đều hợp lệ. Không phát hiện sai lệch.")
        return "All audit logs are valid."

    except Exception as exc:
        logger.critical("[AuditLog-Verification] Lỗi hệ thống khi chạy kiểm tra AuditLog: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def main_send_fcm_notification(self, fcm_token: str, title: str, body: str, data: dict = None):
    """
    Task gửi push notification qua Firebase Cloud Messaging (FCM).
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
