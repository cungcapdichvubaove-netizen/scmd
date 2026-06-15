<<<<<<< HEAD
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = _("7. Quản lý kho và vật tư")
=======
# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = _('Quản lý Kho & Vật tư')

    def ready(self):
        """
        Khởi tạo signals khi app sẵn sàng.
        Kỷ luật Clean Architecture: Tách biệt logic xử lý sự kiện.
        """
        import inventory.signals
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
