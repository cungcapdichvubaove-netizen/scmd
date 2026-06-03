# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/urls.py
Author: Mr. Anh
Created Date: 2025-12-09
Description: Định tuyến URL module Vận hành.
             FIXED: Đưa Dashboard API lên trên cùng để tránh bị Router 'nuốt' mất request.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from operations import api, api_views, views

app_name = 'operations'

router = DefaultRouter()
router.register(r'mobile/ca-truc', api_views.MobileCaTrucViewSet, basename='mobile-ca-truc')
router.register(r'mobile/su-co', api_views.MobileBaoCaoSuCoViewSet, basename='mobile-su-co')

urlpatterns = [
    # --- API ENDPOINTS ---
    
    # [FIX] Đưa endpoint cụ thể lên TRƯỚC router tổng
    # Nếu để bên dưới, Django sẽ match 'api/' của router trước và gây lỗi 404
    path('api/dashboard/data/', api_views.DashboardDataAPIView.as_view(), name='api_dashboard_data'),
    path('api/dashboard/alive-check-violations/', api_views.AliveCheckViolationAPIView.as_view(), name='api_alive_check_violations'),

    # API Chấm công Mobile (Clean Architecture v2)
    path('api/v1/mobile/checkin/', api_views.CheckInAPI.as_view(), name='mobile_checkin_api'),
    path('api/v1/mobile/checkout/', api_views.CheckOutAPI.as_view(), name='mobile_checkout_api'),
    path('api/v1/mobile/lich-truc/', api.FrozenLegacyAPIView.as_view(), name='mobile_lich_truc_api'),
    path('api/v1/mobile/doi-ca/', api.FrozenLegacyAPIView.as_view(), name='mobile_doi_ca_api'),
    path('api/v1/mobile/doi-ca/phe-duyet/', api.FrozenLegacyAPIView.as_view(), name='mobile_doi_ca_approve_api'),
    path('api/v1/mobile/alive-check/respond/', api_views.MobileAliveCheckResponseAPIView.as_view(), name='mobile_alive_check_respond_api'),

    # Reports & Analytics
    path('api/v1/operations/reports/swap-rate/', api.FrozenLegacyAPIView.as_view(), name='report_swap_rate_api'),

    # Sau đó mới đến router chung
    path('api/', include(router.urls)),
    
    # --- WEB DASHBOARD ---
    path('dashboard/', views.dashboard_vanhanh_view, name='dashboard_vanhanh'),
    path('muc-tieu/', views.danh_sach_muc_tieu, name='danh_sach_muc_tieu'),
    path('muc-tieu/<int:pk>/', views.chi_tiet_muc_tieu, name='chi_tiet_muc_tieu'),

    # --- XẾP LỊCH (HTMX) ---
    path('xep-lich/', views.xep_lich_view, name='xep_lich'),
    path('htmx/them-ca/<int:vi_tri_id>/<int:ca_id>/<str:ngay>/', views.them_ca_form_view, name='them_ca_form'),
    path('htmx/sua-ca/<int:phan_cong_id>/', views.sua_ca_form_view, name='sua_ca_form'),
    path('htmx/luu-ca/', views.luu_ca_view, name='luu_ca'),
    path('htmx/xoa-ca/<int:phan_cong_id>/', views.xoa_ca_view, name='xoa_ca'),

    # --- MOBILE APP VIEWS ---
    path('mobile/', views.mobile_dashboard, name='mobile_dashboard_redirect'), 
    path('mobile/dashboard/', views.mobile_dashboard, name='mobile_dashboard'),
    path('mobile/lich-truc/', views.mobile_lich_truc_view, name='mobile_lich_truc'),
    path('mobile/bao-cao-su-co/', views.bao_cao_su_co_mobile_view, name='bao_cao_su_co'),
    path('mobile/cham-cong/', views.mobile_cham_cong_view, name='mobile_cham_cong'),
    
    # --- LEGACY FUNCTION VIEWS (Giữ tương thích) ---
    path('mobile/check-in/<int:phan_cong_id>/', views.check_in_view, name='check_in'),
    path('mobile/check-out/<int:phan_cong_id>/', views.check_out_view, name='check_out'),
    
    path('mobile/sos/', views.trigger_sos, name='trigger_sos'),
    path('mobile/alive-check/<int:check_id>/', views.xac_nhan_alive_check, name='xac_nhan_alive_check'),

    # --- KHÁC ---
    path('mobile/lich-su-cham-cong/', views.mobile_lich_su_cham_cong, name='mobile_lich_su_cham_cong'),
    path('mobile/de-xuat/', views.mobile_de_xuat_list, name='mobile_de_xuat_list'),
    path('mobile/de-xuat/tao/', views.mobile_de_xuat_create, name='mobile_de_xuat_create'),
    path('mobile/de-xuat/<int:pk>/', views.mobile_de_xuat_detail, name='mobile_de_xuat_detail'),
]
