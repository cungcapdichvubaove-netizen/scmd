# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: reports/models.py
Author: Mr. Anh
Description: Model điều hướng cho module Báo cáo & Thống kê.
             FIXED: Sửa lỗi TypeError Proxy bằng cách dùng managed=False.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaoCao(models.Model):
    """
    Model ảo (Virtual Model).
    Sử dụng managed = False để Django không tự ý tạo/xóa bảng này trong DB.
    """
    # Cần ít nhất một trường để Django không báo lỗi khởi tạo
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False  # Không tạo bảng trong Database
        db_table = 'virtual_reports_anchor' # Tên bảng giả lập
        verbose_name = _("Trung tâm Báo cáo & Thống kê")
        verbose_name_plural = _("6. Báo cáo & Thống kê")

    def __str__(self):
        return str(self._meta.verbose_name)