# file: main/urls.py
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: main/urls.py
Author: Mr. Anh
Created Date: 2025-11-30
Description: Định tuyến URL cho ứng dụng Main.
             UPDATED: Thêm Password Change views để fix lỗi NoReverseMatch.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

app_name = 'main'

urlpatterns = [
    # 1. Trang chủ & Điều hướng
    path('', views.homepage, name='homepage'),
    path('hub/', views.central_hub, name='central_hub'),

    # 2. Xác thực (Auth)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 3. ĐỔI MẬT KHẨU (Khi user ĐANG đăng nhập) - FIX LỖI 500
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='main/password_change_form.html',
             success_url='/password-change/done/'
         ), 
         name='password_change'),

    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='main/password_change_done.html'
         ), 
         name='password_change_done'),

    # 4. QUÊN MẬT KHẨU (Khi user CHƯA đăng nhập)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='main/password_reset_form.html',
             email_template_name='main/password_reset_email.html',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='main/password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='main/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),

    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='main/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
# Thêm đoạn này vào cuối file để hiển thị ảnh
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)