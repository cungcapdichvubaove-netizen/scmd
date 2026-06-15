<<<<<<< HEAD
=======
# dashboard/apps.py
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
<<<<<<< HEAD
    verbose_name = _("Bảng điều khiển")
=======
    verbose_name = _("Báo cáo & Thống kê")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
