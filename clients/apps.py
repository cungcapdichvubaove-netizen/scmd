<<<<<<< HEAD
from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clients"
    verbose_name = "1. Quản lý kinh doanh"
=======
# clients/apps.py
from django.apps import AppConfig

class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clients'
    verbose_name = "1. QUẢN LÝ KINH DOANH (CRM)" # Thêm số để sắp xếp
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
