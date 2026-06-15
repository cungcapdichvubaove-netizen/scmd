import logging

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = _("4. Quản trị nhân sự")

    def ready(self):
        try:
            import users.signals
        except ImportError as exc:
            logger.error("[SCMD-SYSTEM] Không thể kích hoạt signals trong app users: %s", exc)
