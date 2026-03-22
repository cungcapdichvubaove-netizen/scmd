# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System - Inventory Module
--------------------------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: inventory/admin.py
Description: Cấu hình giao diện Admin cho module Quản lý Kho vật tư và Công cụ hỗ trợ.
Optimized by: Gemini AI Specialist
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    LoaiVatTu, 
    VatTu, 
    PhieuNhap, 
    ChiTietPhieuNhap, 
    PhieuXuat, 
    ChiTietPhieuXuat, 
    CongCuTaiMucTieu
)

# --- Setup Inlines (Bảng nhập liệu chi tiết) ---

class ChiTietNhapInline(admin.TabularInline):
    """Bảng nhập liệu chi tiết vật tư trong phiếu nhập kho"""
    model = ChiTietPhieuNhap
    extra = 1  # Số dòng trống hiển thị sẵn
    autocomplete_fields = ['vat_tu']  # Giúp tìm vật tư nhanh nếu list dài
    verbose_name = _("Chi tiết vật tư nhập")
    verbose_name_plural = _("Danh sách vật tư nhập kho")


class ChiTietXuatInline(admin.TabularInline):
    """Bảng nhập liệu chi tiết vật tư trong phiếu xuất kho"""
    model = ChiTietPhieuXuat
    extra = 1
    autocomplete_fields = ['vat_tu']
    verbose_name = _("Chi tiết vật tư xuất")
    verbose_name_plural = _("Danh sách vật tư xuất kho")


# --- Config Admin Chính ---

@admin.register(VatTu)
class VatTuAdmin(admin.ModelAdmin):
    """Quản lý danh mục vật tư, công cụ hỗ trợ và tồn kho hiện tại"""
    list_display = ('ten_vat_tu', 'loai_vat_tu', 'ton_kho_hien_thi', 'don_vi_tinh')
    search_fields = ('ten_vat_tu', 'ma_vattu')
    list_filter = ('loai_vat_tu', 'don_vi_tinh')
    list_select_related = ('loai_vat_tu',)
    
    def ton_kho_hien_thi(self, obj):
        """Hiển thị số lượng tồn kho kèm cảnh báo màu sắc"""
        try:
            val = obj.so_luong_ton or 0
            if val <= 10:
                return format_html('<b style="color: #d9534f;">{} (Sắp hết)</b>', val)
            return format_html('<b style="color: #5cb85c;">{}</b>', val)
        except Exception:
            return "0"
    
    ton_kho_hien_thi.short_description = _("Số lượng tồn")
    ton_kho_hien_thi.admin_order_field = 'so_luong_ton'


@admin.register(PhieuNhap)
class PhieuNhapAdmin(admin.ModelAdmin):
    """Quản lý các đợt nhập kho vật tư từ nhà cung cấp hoặc thu hồi"""
    list_display = ('ma_phieu', 'ngay_nhap_format', 'nguoi_nhap')
    list_select_related = ('nguoi_nhap',)
    inlines = [ChiTietNhapInline]  # Nhúng bảng chi tiết vào
    search_fields = ('ma_phieu',)
    date_hierarchy = 'ngay_nhap'

    def ngay_nhap_format(self, obj):
        """Định dạng ngày nhập chuẩn d/m/Y"""
        return obj.ngay_nhap.strftime('%d/%m/%Y') if obj.ngay_nhap else ""
    
    ngay_nhap_format.short_description = _("Ngày nhập kho")


@admin.register(PhieuXuat)
class PhieuXuatAdmin(admin.ModelAdmin):
    """Quản lý cấp phát vật tư cho nhân viên hoặc mục tiêu bảo vệ"""
    list_display = ('ma_phieu', 'loai_xuat', 'nguoi_nhan_hien_thi', 'ngay_xuat_format')
    list_filter = ('loai_xuat', 'ngay_xuat')
    list_select_related = ('nhan_vien_nhan', 'muc_tieu_nhan')
    inlines = [ChiTietXuatInline]
    autocomplete_fields = ['nhan_vien_nhan', 'muc_tieu_nhan']
    search_fields = ('ma_phieu',)
    
    def nguoi_nhan_hien_thi(self, obj):
        """Logic hiển thị đối tượng nhận dựa trên loại xuất"""
        try:
            if obj.loai_xuat == 'CA_NHAN':
                return format_html('<span style="color: #337ab7;">👤 {}</span>', obj.nhan_vien_nhan)
            elif obj.loai_xuat == 'MUC_TIEU':
                return format_html('<span style="color: #f0ad4e;">🏢 {}</span>', obj.muc_tieu_nhan)
            return _("Hủy/Khác")
        except Exception:
            return _("N/A")

    def ngay_xuat_format(self, obj):
        """Định dạng ngày xuất chuẩn d/m/Y"""
        return obj.ngay_xuat.strftime('%d/%m/%Y') if obj.ngay_xuat else ""

    nguoi_nhan_hien_thi.short_description = _("Đối tượng tiếp nhận")
    ngay_xuat_format.short_description = _("Ngày xuất kho")


@admin.register(CongCuTaiMucTieu)
class CongCuTaiMucTieuAdmin(admin.ModelAdmin):
    """Theo dõi thực tế số lượng công cụ hỗ trợ đang có mặt tại từng mục tiêu"""
    list_display = ('muc_tieu', 'vat_tu', 'so_luong_dang_giu', 'ngay_cap_gan_nhat_format')
    list_filter = ('muc_tieu', 'vat_tu')
    list_select_related = ('muc_tieu', 'vat_tu')
    search_fields = ('muc_tieu__ten_muc_tieu', 'vat_tu__ten_vat_tu')

    def ngay_cap_gan_nhat_format(self, obj):
        """Định dạng ngày cấp chuẩn d/m/Y"""
        return obj.ngay_cap_gan_nhat.strftime('%d/%m/%Y') if obj.ngay_cap_gan_nhat else ""

    ngay_cap_gan_nhat_format.short_description = _("Ngày cập nhật")


# Đăng ký các model danh mục cơ bản
admin.site.register(LoaiVatTu)