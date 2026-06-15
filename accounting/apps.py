<<<<<<< HEAD
from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting"
    verbose_name = "6. Tài chính và kế toán"

    def ready(self):
        import accounting.signals
=======
# accounting/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = "6. TÀI CHÍNH & KẾ TOÁN"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
