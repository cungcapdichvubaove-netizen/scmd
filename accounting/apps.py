# accounting/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = "6. TÀI CHÍNH & KẾ TOÁN"
