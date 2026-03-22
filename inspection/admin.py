# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System - Inspection Module
--------------------------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: inspection/admin.py
Description: Cấu hình giao diện Admin cho module tuần tra, thanh tra và vi phạm.
Optimized by: Gemini AI Specialist
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# IMPORT MODELS
from .models import (
    LoaiTuanTra, 
    DiemTuanTra, 
    LuotTuanTra, 
    GhiNhanTuanTra, 
    BienBanViPham, 
    DotThanhTra, 
    HangMucKiemTra, 
    BienBanThanhTra
)


class DiemTuanTraInline(admin.TabularInline):
    """
    Inline cho phép quản lý các điểm tuần tra trực tiếp trong Loại tuần tra.
    """
    model = DiemTuanTra
    extra = 1
    fields = ('ten_diem', 'ma_qr', 'thu_tu')
    verbose_name = _("Điểm tuần tra chi tiết")
    verbose_name_plural = _("Danh sách điểm tuần tra")


@admin.register(LoaiTuanTra)
class LoaiTuanTraAdmin(admin.ModelAdmin):
    """
    Quản lý các loại hình tuần tra (ví dụ: Tuần tra vòng ngoài, Kiểm tra mục tiêu).
    """
    list_display = ('ten_loai', 'muc_tieu', 'thoi_gian_quy_dinh', 'actions_column')
    list_select_related = ('muc_tieu',)  # Tối ưu hiệu suất query ForeignKey
    search_fields = ('ten_loai', 'muc_tieu__ten_muc_tieu')
    inlines = [DiemTuanTraInline]
    
    def actions_column(self, obj):
        """
        Cột công cụ bổ sung: In mã QR cho toàn bộ các điểm thuộc loại tuần tra này.
        """
        try:
            if obj.pk:
                url = reverse('inspection:export_qr_pdf', args=[obj.pk])
                return format_html(
                    '<a href="{}" target="_blank" class="button" '
                    'style="background-color: #447e9b; color: white; padding: 4px 8px; border-radius: 4px;">'
                    '🖨️ In QR</a>', 
                    url
                )
        except Exception:
            pass
        return ""
    
    actions_column.short_description = _("Công cụ nghiệp vụ")


@admin.register(LuotTuanTra)
class LuotTuanTraAdmin(admin.ModelAdmin):
    """
    Quản lý lịch sử và trạng thái thực tế của các lượt tuần tra từ nhân viên.
    """
    list_display = ('nhan_vien', 'loai_tuan_tra', 'thoi_gian_bat_dau', 'trang_thai', 'tien_do_display')
    list_filter = ('trang_thai', 'thoi_gian_bat_dau', 'loai_tuan_tra__muc_tieu')
    list_select_related = ('nhan_vien', 'loai_tuan_tra') # Tránh N+1 query
    search_fields = ('nhan_vien__ho_ten', 'loai_tuan_tra__ten_loai')
    readonly_fields = ('thoi_gian_bat_dau',)

    def tien_do_display(self, obj):
        """
        Hiển thị tiến độ hoàn thành dưới dạng phần trăm với màu sắc trực quan.
        """
        try:
            val = getattr(obj, 'tien_do', 0)
            color = "#28a745" if val == 100 else "#ffc107"
            return format_html(
                '<b style="color: {};">{}%</b>',
                color,
                val
            )
        except (ValueError, TypeError):
            return "0%"
            
    tien_do_display.short_description = _("Tiến độ thực hiện")


@admin.register(BienBanViPham)
class BienBanViPhamAdmin(admin.ModelAdmin):
    """
    Quản lý hồ sơ vi phạm của nhân viên/đối tượng trong mục tiêu.
    """
    list_display = ('ma_bien_ban', 'doi_tuong_vi_pham', 'loai_loi', 'hinh_thuc_xu_ly', 'so_tien_phat_vnd', 'trang_thai')
    list_filter = ('trang_thai', 'hinh_thuc_xu_ly', 'loai_loi')
    list_select_related = ('doi_tuong_vi_pham',)
    search_fields = ('ma_bien_ban', 'doi_tuong_vi_pham__ho_ten')
    
    def so_tien_phat_vnd(self, obj):
        """Định dạng tiền tệ VNĐ cho chuyên nghiệp"""
        if obj.so_tien_phat:
            return format_html('{:,.0f} VNĐ', obj.so_tien_phat)
        return "0 VNĐ"
    so_tien_phat_vnd.short_description = _("Số tiền phạt")


@admin.register(DotThanhTra)
class DotThanhTraAdmin(admin.ModelAdmin):
    """
    Quản lý các đợt thanh tra đột xuất hoặc định kỳ từ cán bộ điều lệnh.
    """
    list_display = ('muc_tieu', 'can_bo', 'thoi_gian_den', 'ket_qua_display')
    list_filter = ('ket_qua', 'thoi_gian_den')
    list_select_related = ('muc_tieu', 'can_bo')
    
    def ket_qua_display(self, obj):
        if obj.ket_qua == 'DAT':
            return format_html('<span style="color: green;">✔ Đạt</span>')
        return format_html('<span style="color: red;">✘ Không đạt</span>')
    ket_qua_display.short_description = _("Kết quả thanh tra")


# Register Old Models (Để không mất dữ liệu Admin - Giữ nguyên theo yêu cầu)
admin.site.register(HangMucKiemTra)
admin.site.register(BienBanThanhTra)
admin.site.register(GhiNhanTuanTra) # Đảm bảo model này cũng được đăng ký nếu chưa có