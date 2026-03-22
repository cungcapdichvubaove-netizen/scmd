# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System - Main Module
-------------------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: main/models.py
Author: Mr. Anh
Description: Model quản lý hồ sơ pháp nhân và thông tin nhận diện thương hiệu SCMD.
Optimized by: Gemini AI Specialist
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class CompanyProfile(models.Model):
    """
    Hồ sơ pháp nhân duy nhất của hệ thống SCMD.
    Lưu trữ thông tin liên hệ, nhận diện thương hiệu và cấu hình toàn cục.
    """
    ten_cong_ty = models.CharField(_("Tên doanh nghiệp"), max_length=255)
    mst = models.CharField(
        _("Mã số thuế"), 
        max_length=20, 
        blank=True, 
        null=True, 
        help_text=_("Mã số thuế pháp nhân để xuất hóa đơn và chứng từ")
    )
    logo = models.ImageField(
        _("Logo thương hiệu"), 
        upload_to="logos/%Y/", 
        null=True, 
        blank=True,
        help_text=_("Ảnh định dạng PNG/JPG, kích thước khuyến nghị 500x500px")
    )
    dia_chi = models.CharField(_("Địa chỉ trụ sở"), max_length=255, blank=True)
    email = models.EmailField(_("Email giao dịch"), max_length=100, blank=True)
    sdt = models.CharField(_("Số điện thoại hotline"), max_length=20, blank=True)
    website = models.URLField(_("Website chính thức"), blank=True)
    mo_ta = models.TextField(_("Giới thiệu ngắn"), blank=True, help_text=_("Hiển thị trên chân trang hoặc báo cáo"))

    class Meta:
        verbose_name = _("Thông tin Công ty")
        verbose_name_plural = _("Thông tin Công ty")

    def __str__(self):
        return str(self.ten_cong_ty)

    def clean(self):
        """
        Giao thức Singleton: Ngăn chặn việc tạo bản ghi thứ 2 thông qua mã nguồn.
        """
        if not self.pk and CompanyProfile.objects.exists():
            raise ValidationError(_("Hệ thống SCMD chỉ hỗ trợ duy nhất một hồ sơ Công ty."))

    def save(self, *args, **kwargs):
        """
        Override phương thức save để đảm bảo dữ liệu luôn nhất quán.
        """
        self.full_clean()  # Gọi hàm clean trước khi lưu
        super(CompanyProfile, self).save(*args, **kwargs)

    @property
    def logo_url(self):
        """
        Gia cố Error Handling: Trả về URL logo an toàn, tránh lỗi khi file không tồn tại.
        """
        try:
            if self.logo and hasattr(self.logo, 'url'):
                return self.logo.url
        except Exception:
            pass
        return "/static/assets/img/default-logo.png"