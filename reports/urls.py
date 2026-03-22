# file: reports/urls.py
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: reports/urls.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: URLs cho Reports App.
             UPDATED: Thêm endpoint Export PDF/Excel.
             ENHANCEMENT: Chuẩn hóa định danh để đồng bộ với Admin Redirect.
"""

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # --- NHÓM DASHBOARD TỔNG HỢP ---
    # Dashboard Báo cáo chính (Sử dụng bởi BaoCaoAdmin để chuyển hướng)
    path('', views.report_dashboard, name='report_dashboard'),
    
    # --- NHÓM BÁO CÁO CHI TIẾT (NGHIỆP VỤ AN NINH) ---
    # Báo cáo Chấm công
    path('cham-cong/tong-hop/', views.tong_hop_cham_cong_thang_view, name='tong_hop_cham_cong'),
    path('cham-cong/ca-nhan/', views.bang_cham_cong_ca_nhan_view, name='cham_cong_ca_nhan'),
    path('cham-cong/muc-tieu/', views.bang_cham_cong_muc_tieu_view, name='cham_cong_muc_tieu'),
    
    # Báo cáo Sự cố An ninh
    path('su-co/', views.bao_cao_su_co_view, name='su_co'),

    # --- NHÓM XUẤT DỮ LIỆU (EXPORT FEATURES) ---
    # Xuất PDF cho từng vụ việc sự cố cụ thể
    path('export/incident/<int:pk>/pdf/', views.export_incident_pdf, name='export_incident_pdf'),
    
    # Xuất bảng tổng hợp chấm công định dạng Excel (Chuẩn d/m/Y)
    path('export/attendance/excel/', views.export_attendance_excel, name='export_attendance_excel'),
]