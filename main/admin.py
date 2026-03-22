# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System - Main Module
-------------------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: main/admin.py
Description: Cấu hình giao diện Admin cho thông tin pháp nhân và cấu hình hệ thống SCMD.
Optimized by: Gemini AI Specialist
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import CompanyProfile  # Sửa ThongTinCongTy thành CompanyProfile theo yêu cầu


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    """
    Quản lý thông tin hồ sơ doanh nghiệp (Pháp nhân SCMD).
    Cấu hình các thông tin liên hệ, mã số thuế và nhận diện thương hiệu.
    """
    list_display = ('ten_cong_ty', 'email_lien_he', 'so_dien_thoai', 'website_link')
    search_fields = ('ten_cong_ty', 'email', 'mst')
    
    fieldsets = (
        (_('Thông tin cơ bản'), {
            'fields': ('ten_cong_ty', 'mst', 'logo')
        }),
        (_('Thông tin liên hệ'), {
            'fields': ('email', 'sdt', 'website', 'dia_chi')
        }),
        (_('Cấu hình hệ thống'), {
            'fields': ('mo_ta',),
            'classes': ('collapse',),
        }),
    )

    def email_lien_he(self, obj):
        """Hiển thị email dưới dạng link mailto"""
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return "-"
    email_lien_he.short_description = _("Email liên hệ")

    def so_dien_thoai(self, obj):
        """Hiển thị số điện thoại định dạng chuẩn"""
        return obj.sdt if obj.sdt else "-"
    so_dien_thoai.short_description = _("Số điện thoại")

    def website_link(self, obj):
        """Hiển thị website dưới dạng clickable link"""
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website)
        return "-"
    website_link.short_description = _("Website chính thức")

    def has_add_permission(self, request):
        """
        Giới hạn: Chỉ cho phép tạo tối đa 1 hồ sơ công ty để tránh sai lệch dữ liệu hệ thống.
        """
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)