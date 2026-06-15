# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'inspection'

urlpatterns = [
    # WEB MANAGER
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('export-qr/<int:loai_id>/', views.export_qr_pdf, name='export_qr_pdf'),

    # MOBILE
    path('mobile/list/', views.mobile_tuan_tra_list, name='mobile_tuan_tra_list'),
    path('mobile/bat-dau/<int:loai_id>/', views.bat_dau_tuan_tra, name='bat_dau_tuan_tra'),
    path('mobile/thuc-hien/<int:luot_id>/', views.thuc_hien_tuan_tra, name='thuc_hien_tuan_tra'),
    path('mobile/ghi-nhan/', views.ghi_nhan_diem, name='ghi_nhan_diem'),
    path('mobile/ghi-nhan/quet-qr/', views.ghi_nhan_diem, name='xu_ly_quet_qr'),
    path('mobile/hoan-thanh/<int:luot_id>/', views.hoan_thanh_tuan_tra, name='hoan_thanh_tuan_tra'),
    
    path('mobile/lap-bien-ban/', views.mobile_lap_bien_ban, name='mobile_lap_bien_ban'),
    path('mobile/kiem-tra-muc-tieu/', views.mobile_dot_thanh_tra, name='mobile_dot_thanh_tra'),
]