# file: notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):  # Đảm bảo tên class là NotificationsConfig
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
