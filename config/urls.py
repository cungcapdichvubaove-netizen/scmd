# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: config/urls.py
Author: Mr. Anh
Created Date: 2025-12-11
Description: Cấu hình URL gốc.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

def logout_redirect_handler(request):
    """
    Xử lý trung gian để fix lỗi 405 Method Not Allowed khi truy cập admin/logout qua GET.
    """
    from django.contrib.auth import logout
    if request.user.is_authenticated:
        logout(request)
    return redirect('main:login')

urlpatterns = [
    # 1. Admin & Core (Xử lý Logout trước)
    path('admin/logout/', logout_redirect_handler, name='admin_logout_fix'),
    path('admin/', admin.site.urls),
    
    # Service Worker cho PWA
    path('sw.js', TemplateView.as_view(
        template_name='sw.js', 
        content_type='application/javascript'
    ), name='sw.js'),

    # 2. API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # 3. Business Apps
    path('', include('main.urls')),
    path('users/', include('users.urls')),
    path('clients/', include('clients.urls')),
    path('operations/', include('operations.urls')),
    path('inspection/', include('inspection.urls')),
    path('accounting/', include('accounting.urls')),
    path('inventory/', include('inventory.urls')),
    path('workflow/', include('workflow.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reports/', include('reports.urls')),
]

# Tối ưu hóa Static & Media trong Debug mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]

# Cấu hình UI cho Admin Dashboard
admin.site.site_header = "Security Command System"
admin.site.site_title = "SCMD Admin"
admin.site.index_title = "Trung tâm quản trị hệ thống"

# Xử lý lỗi toàn cục
handler404 = 'main.views.handler404' if 'main' in settings.INSTALLED_APPS else None
handler500 = 'main.views.handler500' if 'main' in settings.INSTALLED_APPS else None