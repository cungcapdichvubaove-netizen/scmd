# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/apps.py
Author: Mr. Anh
Created Date: 2025-12-03
Description: Cấu hình App Operations.
             Quan trọng: Phải import signals trong hàm ready() để kích hoạt Trigger.
"""
# operations/apps.py
from django.apps import AppConfig

class OperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operations'
    verbose_name = "2. ĐIỀU HÀNH & GIÁM SÁT"

    def ready(self):
        """
        Import signals khi ứng dụng khởi động để lắng nghe sự kiện DB.
        """
        import operations.signals