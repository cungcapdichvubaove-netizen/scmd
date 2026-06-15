<<<<<<< HEAD
from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"
    verbose_name = "0. Cấu hình chung"

    def ready(self):
        # Rule 12.3: Register custom release checks for production safety
        from . import checks  # noqa
=======
# core/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = "0. CẤU HÌNH CHUNG"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
