# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/urls.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: URLs cho Users App.
             UPDATED: Thêm route mobile password & salary detail.
"""

from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # Dashboard HR
    path("dashboard/", views.dashboard_view, name="dashboard"),
    
    # Desktop Profile
    path("profile/", views.profile_view, name="profile"),
    
    # --- MOBILE ROUTES ---
    path("mobile/profile/", views.mobile_profile_view, name="mobile_profile"),
    path("mobile/password-change/", views.mobile_password_change_view, name="mobile_password_change"),
    path("mobile/salary/<int:luong_id>/", views.mobile_salary_detail_view, name="mobile_salary_detail"),

    # Export PDF
    path("<int:nhan_vien_id>/export-options/", views.export_ly_lich_options_view, name="export-ly-lich-options"),
    path("<int:nhan_vien_id>/export-pdf/", views.export_ly_lich_pdf, name="export-ly-lich"),
]