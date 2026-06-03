# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/urls.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Định tuyến URL cho module Kế toán.
             FIXED: Đồng bộ tên view dashboard_accounting.
"""

from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    # WEB ADMIN (Kế toán trưởng)
    # Fix lỗi: Dùng 'dashboard_accounting' thay vì 'dashboard'
    path('dashboard/', views.dashboard_accounting, name='dashboard'),
    
    # Các tính năng xử lý lương
    path('tinh-luong/', views.tinh_luong_view, name='tinh_luong'),
    path('bang-luong/<int:pk>/', views.chi_tiet_bang_luong, name='bang_luong_detail'),
    path('chot-luong/<int:pk>/', views.chot_luong_view, name='chot_luong'),
    path('doi-soat-khau-tru/<int:pk>/', views.bao_cao_doi_soat_khau_tru, name='doi_soat_khau_tru'),
    path('export-doi-soat-khau-tru/<int:pk>/', views.export_doi_soat_khau_tru_excel, name='export_doi_soat_khau_tru_excel'),
    
    # MOBILE APP (Nhân viên xem lương)
    path('mobile/luong/', views.mobile_phieu_luong_list, name='mobile_phieu_luong_list'),
    path('mobile/luong/<int:pk>/', views.mobile_phieu_luong_detail, name='mobile_phieu_luong_detail'),
]