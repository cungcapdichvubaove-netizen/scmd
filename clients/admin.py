# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: clients/admin.py
Author: Mr. Anh
Updated Date: 2026-03-21
Description: Cấu hình Admin Phân hệ Khách hàng (CRM) - Vertical Layout.
             UPGRADE: Tối ưu hiệu năng Query & Giao diện Trạng thái chuyên nghiệp.
"""

from django.contrib import admin
from django.db import models
from django.forms import TextInput, NumberInput, Textarea
from django.utils.html import format_html
from django.urls import reverse
from .models import KhachHangTiemNang, CoHoiKinhDoanh, HopDong, MucTieu

# --- CONFIG MÀU SẮC ĐỒNG BỘ HỆ THỐNG SCMD ---
UI_COLORS = {
    'MOI': '#3b82f6',           # Blue
    'TIEM_NANG': '#f59e0b',     # Amber
    'CHOT_HOP_DONG': '#10b981', # Green
    'HUY': '#ef4444',           # Red
    'HIEU_LUC': '#10b981',      # Emerald
    'SAP_HET_HAN': '#eab308',   # Yellow
    'DA_THANH_LY': '#64748b',   # Slate
}

def format_html_status(text, status_code):
    """Định dạng Badge trạng thái theo chuẩn giao diện SCMD Erp"""
    color = UI_COLORS.get(status_code, '#475569')
    return format_html(
        '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; '
        'font-weight: 800; font-size: 10px; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.12); '
        'display: inline-block; min-width: 80px; text-align: center;">{}</span>',
        color, text
    )

# --- 1. KHÁCH HÀNG TIỀM NĂNG ---
class CoHoiInline(admin.TabularInline):
    model = CoHoiKinhDoanh
    fk_name = 'khach_hang_tiem_nang'
    extra = 0
    fields = ['ten_co_hoi', 'gia_tri_uoc_tinh', 'trang_thai', 'nguoi_phu_trach', 'ngay_tao']
    readonly_fields = ['ngay_tao']
    show_change_link = True
    classes = ['collapse']
    verbose_name = "Cơ hội kinh doanh"
    verbose_name_plural = "⚡ PIPELINE BÁN HÀNG (CÁC CƠ HỘI LIÊN QUAN)"

@admin.register(KhachHangTiemNang)
class KhachHangTiemNangAdmin(admin.ModelAdmin):
    list_display = ['ten_cong_ty', 'nguoi_lien_he', 'sdt', 'show_trang_thai', 'nguon', 'ngay_tao_vn']
    list_filter = ['trang_thai', 'nguon', ('ngay_tao', admin.DateFieldListFilter)]
    search_fields = ['ten_cong_ty', 'sdt', 'email', 'nguoi_lien_he']
    inlines = [CoHoiInline]
    save_on_top = True
    list_per_page = 20
    readonly_fields = ['ngay_tao']
    search_help_text = "Tìm theo tên công ty, số điện thoại hoặc email khách hàng."

    # LAYOUT DỌC (VERTICAL) - Đảm bảo căn chỉnh thẳng hàng
    fieldsets = (
        ("🏢 THÔNG TIN CHUNG", {
            'description': "Thông tin pháp lý và định danh tổ chức khách hàng.",
            'fields': (
                'ten_cong_ty',
                'trang_thai',
                'nguon',
                'dia_chi',
                'ngay_tao'
            )
        }),
        ("👤 THÔNG TIN LIÊN HỆ", {
            'description': "Đầu mối liên lạc trực tiếp tại đơn vị khách hàng.",
            'fields': (
                'nguoi_lien_he',
                'sdt',
                'email',
            )
        }),
        ("📝 GHI CHÚ", {
            'fields': (
                'ghi_chu',
            )
        }),
    )

    def get_queryset(self, request):
        """Tối ưu hóa query tránh N+1 cho các trường liên quan nếu có"""
        return super().get_queryset(request)

    def ngay_tao_vn(self, obj):
        try:
            return obj.ngay_tao.strftime('%d/%m/%Y') if obj.ngay_tao else "-"
        except (AttributeError, ValueError):
            return "-"
    ngay_tao_vn.short_description = "Ngày tạo"
    ngay_tao_vn.admin_order_field = 'ngay_tao'

    def show_trang_thai(self, obj):
        if not obj.trang_thai:
            return "-"
        return format_html_status(obj.get_trang_thai_display(), obj.trang_thai)
    show_trang_thai.short_description = "Trạng thái"

# --- 2. CƠ HỘI KINH DOANH ---
@admin.register(CoHoiKinhDoanh)
class CoHoiKinhDoanhAdmin(admin.ModelAdmin):
    list_display = ['ten_co_hoi', 'link_khach_hang', 'show_gia_tri', 'show_trang_thai', 'nguoi_phu_trach', 'ngay_tao_vn']
    list_filter = ['trang_thai', 'nguoi_phu_trach', 'ngay_tao']
    search_fields = ['ten_co_hoi', 'khach_hang_tiem_nang__ten_cong_ty']
    autocomplete_fields = ['khach_hang_tiem_nang']
    save_on_top = True
    readonly_fields = ['ngay_tao']

    fieldsets = (
        ("💎 CHI TIẾT CƠ HỘI", {
            'fields': (
                'ten_co_hoi',
                'khach_hang_tiem_nang',
                'gia_tri_uoc_tinh',
                'trang_thai',
                'nguoi_phu_trach',
                'ngay_tao'
            )
        }),
    )

    def get_queryset(self, request):
        """Sử dụng select_related để tối ưu hiệu suất truy vấn quan hệ"""
        return super().get_queryset(request).select_related('khach_hang_tiem_nang', 'nguoi_phu_trach')

    def link_khach_hang(self, obj):
        if obj.khach_hang_tiem_nang:
            try:
                url = reverse("admin:clients_khachhangtiemnang_change", args=[obj.khach_hang_tiem_nang.id])
                return format_html('<a href="{}" style="font-weight:bold; color:#3b82f6;">{}</a>', url, obj.khach_hang_tiem_nang.ten_cong_ty)
            except Exception:
                return obj.khach_hang_tiem_nang.ten_cong_ty
        return "-"
    link_khach_hang.short_description = "Khách hàng"

    def show_gia_tri(self, obj):
        val = obj.gia_tri_uoc_tinh or 0
        return format_html('<span style="font-weight:600; color:#059669;">{:,.0f} ₫</span>', val)
    show_gia_tri.short_description = "Giá trị dự kiến"

    def show_trang_thai(self, obj):
        if not obj.trang_thai:
            return "-"
        return format_html_status(obj.get_trang_thai_display(), obj.trang_thai)
    show_trang_thai.short_description = "Giai đoạn bán hàng"

    def ngay_tao_vn(self, obj):
        return obj.ngay_tao.strftime('%d/%m/%Y') if obj.ngay_tao else "-"
    ngay_tao_vn.short_description = "Ngày tạo"
    ngay_tao_vn.admin_order_field = 'ngay_tao'

# --- 3. HỢP ĐỒNG ---
class MucTieuInline(admin.StackedInline):
    model = MucTieu
    extra = 0
    classes = ['collapse']
    verbose_name = "Mục tiêu bảo vệ"
    verbose_name_plural = "📍 DANH SÁCH MỤC TIÊU THUỘC HỢP ĐỒNG"

@admin.register(HopDong)
class HopDongAdmin(admin.ModelAdmin):
    list_display = ['so_hop_dong', 'khach_hang_info', 'ngay_hieu_luc_vn', 'ngay_het_han_vn', 'show_trang_thai']
    list_filter = ['trang_thai', ('ngay_het_han', admin.DateFieldListFilter)]
    search_fields = ['so_hop_dong', 'khach_hang_cu__ten_cong_ty']
    inlines = [MucTieuInline]
    autocomplete_fields = ['khach_hang_cu']
    save_on_top = True

    fieldsets = (
        ("📜 THÔNG TIN HỢP ĐỒNG", {
            'fields': (
                'so_hop_dong',
                'trang_thai',
                'khach_hang_cu',
                'co_hoi',
                'gia_tri',
                'file_hop_dong'
            )
        }),
        ("🕒 THỜI HẠN & HIỆU LỰC", {
            'fields': (
                'ngay_ky',
                'ngay_hieu_luc',
                'ngay_het_han'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('khach_hang_cu')

    def khach_hang_info(self, obj): 
        return obj.khach_hang_cu.ten_cong_ty if obj.khach_hang_cu else "---"
    khach_hang_info.short_description = "Tên khách hàng"
    
    def show_trang_thai(self, obj):
        if not obj.trang_thai:
            return "-"
        return format_html_status(obj.get_trang_thai_display(), obj.trang_thai)
    show_trang_thai.short_description = "Trạng thái hiệu lực"

    def ngay_hieu_luc_vn(self, obj):
        return obj.ngay_hieu_luc.strftime('%d/%m/%Y') if obj.ngay_hieu_luc else "-"
    ngay_hieu_luc_vn.short_description = "Ngày hiệu lực"

    def ngay_het_han_vn(self, obj):
        return obj.ngay_het_han.strftime('%d/%m/%Y') if obj.ngay_het_han else "-"
    ngay_het_han_vn.short_description = "Ngày hết hạn"

# --- 4. MỤC TIÊU ---
@admin.register(MucTieu)
class MucTieuAdmin(admin.ModelAdmin):
    list_display = ['ten_muc_tieu', 'hop_dong_link', 'quan_ly_muc_tieu', 'so_luong_nhan_vien', 'co_gps']
    list_filter = ['quan_ly_muc_tieu', 'so_gio_mot_ngay']
    search_fields = ['ten_muc_tieu', 'dia_chi', 'hop_dong__so_hop_dong']
    autocomplete_fields = ['hop_dong', 'quan_ly_muc_tieu']
    save_on_top = True

    class Media:
        css = { 'all': ('css/admin_tweaks.css',) }

    formfield_overrides = {
        models.FloatField: {'widget': NumberInput(attrs={'class': 'fix-gps-input', 'step': '0.000001'})},
        models.IntegerField: {'widget': NumberInput(attrs={'class': 'fix-num-input'})},
        models.DecimalField: {'widget': NumberInput(attrs={'class': 'fix-money-input'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'style': 'width: 100%;'})},
    }

    fieldsets = (
        ("📌 CƠ BẢN", {
            'fields': (
                'hop_dong',
                'ten_muc_tieu',
                'quan_ly_muc_tieu',
                'so_luong_nhan_vien',
                'dia_chi'
            )
        }),
        ("📡 CẤU HÌNH GPS (GEOFENCING)", {
            'description': "Thiết lập tọa độ địa lý để kiểm soát tuần tra (Check-in/Check-out).",
            'fields': (
                'vi_do',
                'kinh_do',
                'ban_kinh_cho_phep'
            )
        }),
        ("💰 CHẾ ĐỘ & LƯƠNG", {
            'description': "Cấu hình định mức lương và chế độ đặc thù tại mục tiêu.",
            'fields': (
                'luong_khoan_bao_ve',
                'so_gio_mot_ngay',
                'tien_chuyen_can',
                'tru_nghi_1_ngay',
                'tru_nghi_2_ngay',
                'tru_nghi_3_ngay'
            )
        }),
        ("📞 LIÊN HỆ TẠI MỤC TIÊU", {
            'fields': (
                'nguoi_lien_he',
                'sdt_lien_he'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hop_dong', 'quan_ly_muc_tieu')

    def hop_dong_link(self, obj):
        if obj.hop_dong:
            try:
                url = reverse("admin:clients_hopdong_change", args=[obj.hop_dong.id])
                return format_html('<a href="{}" style="font-weight:bold;">{}</a>', url, obj.hop_dong.so_hop_dong)
            except Exception:
                return obj.hop_dong.so_hop_dong
        return "-"
    hop_dong_link.short_description = "Hợp đồng kinh tế"

    def co_gps(self, obj):
        """Kiểm tra tình trạng cấu hình tọa độ mục tiêu"""
        has_gps = obj.vi_do is not None and obj.kinh_do is not None
        if has_gps:
            return format_html(
                '<b style="color: #10b981;"><i class="fas fa-map-marker-alt"></i> ✔ OK ({}m)</b>', 
                obj.ban_kinh_cho_phep or 0
            )
        return format_html('<span style="color: #cbd5e1;">✘ Chưa có tọa độ</span>')
    co_gps.short_description = "Cấu hình GPS"