# file: clients/urls.py
# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: clients/urls.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: URLs cho Clients App (CRM).
             FIXED: Khôi phục lại đúng logic Dashboard CRM.
"""

from django.urls import path
from . import views

app_name = "clients"

urlpatterns = [
    # Dashboard CRM (Lưu ý: name='dashboard_crm' để khớp với Sidebar)
    path("dashboard/", views.dashboard_view, name="dashboard_crm"),
    
    # Pipeline Kinh doanh
    path("pipeline/", views.pipeline_view, name="pipeline"),
]