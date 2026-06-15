# -*- coding: utf-8 -*-
"""
Celery tasks for accounting workflows.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.services.payroll import PayrollService

logger = logging.getLogger(__name__)

LOCKED_PERIOD_MESSAGE_FRAGMENT = "da khoa so"


def _is_retryable_payroll_failure(message):
    normalized_message = (message or "").lower()
    return LOCKED_PERIOD_MESSAGE_FRAGMENT not in normalized_message


@shared_task(bind=True, max_retries=3, default_retry_delay=3600)
def accounting_calculate_monthly_payroll(self):
    """
    Automatically calculate payroll for the previous month.
    """
    try:
        today = timezone.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)

        target_month = last_day_last_month.month
        target_year = last_day_last_month.year

        logger.info(
            "[Payroll-Task] Start monthly payroll calculation for %s/%s.",
            target_month,
            target_year,
        )

        success, message = PayrollService.tinh_luong_thang(target_month, target_year)

        if not success:
            logger.error("[Payroll-Task] Payroll calculation failed: %s", message)
            if _is_retryable_payroll_failure(message):
                raise self.retry(countdown=3600)
            return message

        logger.info(
            "[Payroll-Task] Payroll calculation completed for %s/%s: %s",
            target_month,
            target_year,
            message,
        )
        return message

    except Exception as exc:
        logger.critical(
            "[Payroll-Task] System error during payroll calculation: %s",
            str(exc),
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def accounting_send_debt_reminder_email_task(self):
    """
    Periodic task placeholder for debt reminder emails.
    """
    logger.info("[Debt-Reminder-Task] Start scanning and sending reminders.")

    try:
        count_reminders_sent = 0
        logger.info(
            "[Debt-Reminder-Task] Completed. Sent %s reminders.",
            count_reminders_sent,
        )
        return f"Sent {count_reminders_sent} debt reminders."
    except Exception as exc:
        logger.error("[Debt-Reminder-Task] Reminder sending failed: %s", str(exc))
        raise self.retry(exc=exc)
