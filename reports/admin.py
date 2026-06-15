# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: reports/admin.py
Author: Mr. Anh
Description: Cấu hình giao diện điều hướng Báo cáo trong hệ thống Admin.
             FIXED: Chặn truy vấn Database để tránh lỗi 500 trên Docker.
"""

import logging
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _
from .models import BaoCao

logger = logging.getLogger(__name__)

@admin.register(BaoCao)
class BaoCaoAdmin(admin.ModelAdmin):
    """
    Admin điều hướng. Chặn đứng mọi tương tác Database.
    """

    def changelist_view(self, request, extra_context=None):
        """
        Điều hướng trực tiếp tới bảng điều hành.
        """
        try:
            # Ưu tiên URL chính xác trong urls.py
            target_url = reverse("reports:report_dashboard")
            return HttpResponseRedirect(target_url)
        except NoReverseMatch:
            try:
                # Fallback nếu cache cũ chưa cập nhật
                target_url = reverse("reports:dashboard")
                return HttpResponseRedirect(target_url)
            except NoReverseMatch:
                self.message_user(request, _("Lỗi: Không tìm thấy trang bảng điều hành."), level='error')
                return super().changelist_view(request, extra_context)

    # --- GIẢI PHÁP CHO DOCKER: CHẶN TRUY VẤN DATABASE ---

    def get_queryset(self, request):
        """
        Ép buộc trả về kết quả rỗng mà không SELECT vào bảng ảo.
        Triệt tiêu lỗi: relation "virtual_reports_anchor" does not exist.
        """
        return self.model.objects.none()

    # Vô hiệu hóa các nút chức năng để tránh người dùng tác động vào model ảo
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True