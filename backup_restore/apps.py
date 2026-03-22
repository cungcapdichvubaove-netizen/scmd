# backup_restore/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BackupRestoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backup_restore"
    verbose_name = _("Sao lưu & Phục hồi")
