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