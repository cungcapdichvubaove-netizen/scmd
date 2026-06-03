# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/admin.py
Author: Mr. Anh (CTO)
Created Date: 2025-12-06
Description: Cấu hình Admin Vận hành (Operations).
             LAYOUT: Dạng List (Dọc) cho Form nhập liệu.
             UPGRADE: Tối ưu hóa QuerySet & Nâng cấp UI Badge.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    ViTriChot, CaLamViec, PhanCongCaTruc, ChamCong, 
    BaoCaoSuCo, BaoCaoDeXuat, KiemTraQuanSo
)

# --- HELPER: MÀU SẮC TRẠNG THÁI CAO CẤP ---
STATUS_COLORS = {
    'CHUA_TRUC': '#64748b',      # Slate 500
    'DANG_TRUC': '#3b82f6',      # Blue 500
    'HOAN_THANH': '#10b981',     # Emerald 500
    'LOI': '#ef4444',            # Red 500
}

def is_operation_manager(user):
    """Kiểm tra quyền quản lý vận hành của người dùng."""
    if user.is_superuser: 
        return True
    try:
        if hasattr(user, 'nhan_vien') and user.nhan_vien.chuc_danh and user.nhan_vien.chuc_danh.nhom_quyen:
            return user.nhan_vien.chuc_danh.nhom_quyen.name in ['BAN_GIAM_DOC', 'DIEU_HANH', 'THANH_TRA']
    except Exception:
        pass
    return False

# --- CUSTOM FILTER: BỘ LỌC TRẠNG THÁI REAL-TIME ---
class TrangThaiPhanCongFilter(admin.SimpleListFilter):
    title = _('Trạng thái thực hiện')
    parameter_name = 'status_realtime'

    def lookups(self, request, model_admin):
        return (
            ('pending', _('⚪ Chưa trực')),
            ('working', _('⏳ Đang trực')),
            ('done', _('✔ Hoàn thành')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(chamcong__thoi_gian_check_in__isnull=True)
        if self.value() == 'working':
            return queryset.filter(
                chamcong__thoi_gian_check_in__isnull=False,
                chamcong__thoi_gian_check_out__isnull=True
            )
        if self.value() == 'done':
            return queryset.filter(
                chamcong__thoi_gian_check_in__isnull=False,
                chamcong__thoi_gian_check_out__isnull=False
            )
        return queryset

# --- 1. CẤU HÌNH VỊ TRÍ & CA TRỰC ---
@admin.register(ViTriChot)
class ViTriChotAdmin(admin.ModelAdmin):
    list_display = ('ten_vi_tri', 'get_muc_tieu', 'get_dia_chi')
    list_filter = ('muc_tieu',)
    search_fields = ('ten_vi_tri', 'muc_tieu__ten_muc_tieu') 
    autocomplete_fields = ['muc_tieu']

    @admin.display(description='Mục tiêu', ordering='muc_tieu__ten_muc_tieu')
    def get_muc_tieu(self, obj):
        return obj.muc_tieu.ten_muc_tieu if obj.muc_tieu else "-"

    @admin.display(description='Địa chỉ')
    def get_dia_chi(self, obj):
        return obj.muc_tieu.dia_chi if obj.muc_tieu else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('muc_tieu')

@admin.register(CaLamViec)
class CaLamViecAdmin(admin.ModelAdmin):
    list_display = ('ten_ca', 'gio_bat_dau', 'gio_ket_thuc', 'is_night_shift_display')
    search_fields = ('ten_ca',)
    ordering = ('gio_bat_dau',)

    @admin.display(description='Ca đêm?', boolean=True)
    def is_night_shift_display(self, obj):
        return obj.is_night_shift

# --- 2. PHÂN CÔNG CA TRỰC ---
class ChamCongInline(admin.StackedInline):
    model = ChamCong
    can_delete = False
    verbose_name_plural = 'DỮ LIỆU CHẤM CÔNG (REAL-TIME)'
    fk_name = 'ca_truc'
    readonly_fields = (
        'thoi_gian_check_in', 'thoi_gian_check_out',
        'preview_check_in', 'preview_check_out',
        'map_view', 'vi_tri_hop_le', 'khoang_cach_check_in',
        'thiet_bi_check_in', 'ip_check_in', 'ghi_chu'
    )
    
    fieldsets = (
        ('🕒 THÔNG TIN CHECK-IN/OUT', {
            'fields': (
                ('thoi_gian_check_in', 'thoi_gian_check_out'),
                ('preview_check_in', 'preview_check_out'),
            )
        }),
        ('📍 VỊ TRÍ & GPS', {
            'fields': (
                'vi_tri_hop_le',
                'khoang_cach_check_in',
                'map_view'
            )
        }),
        ('📱 THIẾT BỊ & GHI CHÚ', {
            'fields': (
                'thiet_bi_check_in',
                'ip_check_in',
                'ghi_chu'
            ),
            'classes': ('collapse',)
        }),
    )

    def preview_check_in(self, obj):
        if obj.anh_check_in:
            return format_html('<img src="{}" style="height:150px; border-radius:12px; border:2px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);" />', obj.anh_check_in.url)
        return format_html('<span style="color:#cbd5e1;">(Chưa có ảnh)</span>')
    preview_check_in.short_description = "Ảnh Check-in"
    
    def preview_check_out(self, obj):
        if obj.anh_check_out:
            return format_html('<img src="{}" style="height:150px; border-radius:12px; border:2px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);" />', obj.anh_check_out.url)
        return format_html('<span style="color:#cbd5e1;">(Chưa có ảnh)</span>')
    preview_check_out.short_description = "Ảnh Check-out"

    def map_view(self, obj):
        if obj.lat_check_in and obj.long_check_in:
            url = f"https://www.google.com/maps?q={obj.lat_check_in},{obj.long_check_in}"
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background:#4F46E5; color:white; padding:8px 16px; border-radius:6px; text-decoration:none; font-weight:600; display:inline-block;">'
                '<i class="fas fa-map-marked-alt"></i> Mở Google Maps'
                '</a>', url
            )
        return format_html('<span style="color:#ef4444; font-weight:bold;">Chưa có tọa độ GPS</span>')
    map_view.short_description = "Định vị thực tế"

@admin.register(PhanCongCaTruc)
class PhanCongCaTrucAdmin(admin.ModelAdmin):
    list_display = (
        'nhan_vien_info',
        'muc_tieu_info',
        'thoi_gian_truc_vn',
        'status_badge',
        'checkin_thuc_te'
    )
    
    list_filter = (
        ('ngay_truc', admin.DateFieldListFilter),
        TrangThaiPhanCongFilter,
        'ca_lam_viec', 
        'vi_tri_chot__muc_tieu'
    )
    
    search_fields = ('nhan_vien__ho_ten', 'nhan_vien__ma_nhan_vien', 'vi_tri_chot__ten_vi_tri')
    date_hierarchy = 'ngay_truc'
    inlines = [ChamCongInline]
    autocomplete_fields = ['nhan_vien', 'vi_tri_chot', 'ca_lam_viec']
    save_on_top = True

    fieldsets = (
        ("📝 THÔNG TIN PHÂN CÔNG", {
            'fields': (
                ('ngay_truc', 'ca_lam_viec'),
                ('nhan_vien', 'vi_tri_chot'),
            )
        }),
    )

    # --- CUSTOM DISPLAY ---
    def nhan_vien_info(self, obj):
        if obj.nhan_vien:
            return format_html(
                '<div style="min-width:150px;">'
                '<b style="color:#1e293b; font-size:13px;">{}</b><br>'
                '<span style="color:#64748b; font-size:11px; letter-spacing:0.5px;">🆔 {}</span>'
                '</div>',
                obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien
            )
        return "-"
    nhan_vien_info.short_description = "Nhân sự"
    nhan_vien_info.admin_order_field = 'nhan_vien__ho_ten'

    def muc_tieu_info(self, obj):
        if obj.vi_tri_chot:
            return format_html(
                '<div style="min-width:180px;">'
                '<span style="color:#2563eb; font-weight:700; font-size:12px;">🏢 {}</span><br>'
                '<span style="color:#475569; font-size:11px;">📍 {}</span>'
                '</div>',
                obj.vi_tri_chot.muc_tieu.ten_muc_tieu,
                obj.vi_tri_chot.ten_vi_tri
            )
        return "-"
    muc_tieu_info.short_description = "Địa điểm trực"

    def thoi_gian_truc_vn(self, obj):
        vn_date = obj.ngay_truc.strftime('%d/%m/%Y')
        ca = obj.ca_lam_viec.ten_ca if obj.ca_lam_viec else "N/A"
        return format_html(
            '<div style="text-align:center; min-width:100px;">'
            '<b style="font-size:13px; color:#334155;">{}</b><br>'
            '<span style="background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:700; border:1px solid #e2e8f0;">{}</span>'
            '</div>',
            vn_date, ca
        )
    thoi_gian_truc_vn.short_description = "Lịch trực"
    thoi_gian_truc_vn.admin_order_field = 'ngay_truc'

    def status_badge(self, obj):
        status = 'CHUA_TRUC'
        label = '⚪ CHƯA TRỰC'
        
        if hasattr(obj, 'chamcong'):
            cc = obj.chamcong
            if cc.thoi_gian_check_in and cc.thoi_gian_check_out:
                status = 'HOAN_THANH'
                label = '✔ HOÀN THÀNH'
            elif cc.thoi_gian_check_in:
                status = 'DANG_TRUC'
                label = '⏳ ĐANG TRỰC'
        
        color = STATUS_COLORS.get(status, '#999')
        return format_html(
            '<span style="background-color:{}; color:white; padding:5px 10px; border-radius:6px; font-weight:800; font-size:10px; white-space:nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">{}</span>',
            color, label
        )
    status_badge.short_description = "Trạng thái"

    def checkin_thuc_te(self, obj):
        in_time = "--:--"
        out_time = "--:--"
        style_in = "color:#94a3b8"
        style_out = "color:#94a3b8"

        if hasattr(obj, 'chamcong'):
            cc = obj.chamcong
            if cc.thoi_gian_check_in:
                in_time = cc.thoi_gian_check_in.strftime('%H:%M')
                style_in = "color:#059669; font-weight:bold;"
            if cc.thoi_gian_check_out:
                out_time = cc.thoi_gian_check_out.strftime('%H:%M')
                style_out = "color:#059669; font-weight:bold;"

        return format_html(
            '<div style="font-size:11px; white-space:nowrap; line-height:1.5;">'
            'In: <span style="{}">{}</span><br>'
            'Out: <span style="{}">{}</span>'
            '</div>',
            style_in, in_time, style_out, out_time
        )
    checkin_thuc_te.short_description = "Giờ thực tế"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'nhan_vien', 
            'vi_tri_chot__muc_tieu', 
            'ca_lam_viec'
        ).prefetch_related('chamcong')
        
        if is_operation_manager(request.user): 
            return qs
        
        try:
            nv = request.user.nhan_vien
            muc_tieus = nv.cac_muc_tieu_quan_ly.all()
            if muc_tieus.exists():
                return qs.filter(vi_tri_chot__muc_tieu__in=muc_tieus)
            return qs.filter(nhan_vien=nv)
        except Exception: 
            return qs.none()

@admin.register(ChamCong)
class ChamCongAdmin(admin.ModelAdmin):
    list_display = (
        'get_nhan_vien', 'get_muc_tieu', 
        'thoi_gian_check_in_vn', 'thoi_gian_check_out_vn', 
        'show_thumbnail_in', 'show_thumbnail_out',
        'gps_status', 'khoang_cach_display'
    )
    list_filter = (
        'vi_tri_hop_le', 
        ('thoi_gian_check_in', admin.DateFieldListFilter),
        'ca_truc__vi_tri_chot__muc_tieu'
    )
    search_fields = ('ca_truc__nhan_vien__ho_ten', 'ca_truc__nhan_vien__ma_nhan_vien')
    autocomplete_fields = ['ca_truc']
    
    fieldsets = (
        ('📋 THÔNG TIN CA TRỰC', {
            'fields': ('ca_truc',)
        }),
        ('📥 CHECK-IN', {
            'fields': (
                ('thoi_gian_check_in', 'lat_check_in', 'long_check_in'),
                ('anh_check_in', 'preview_in')
            )
        }),
        ('📤 CHECK-OUT', {
            'fields': (
                ('thoi_gian_check_out', 'lat_check_out', 'long_check_out'),
                ('anh_check_out', 'preview_out')
            )
        }),
        ('🛡️ KIỂM TRA HỢP LỆ', {
            'fields': (
                'vi_tri_hop_le',
                'khoang_cach_check_in',
                'ghi_chu'
            )
        }),
    )
    readonly_fields = ('preview_in', 'preview_out')

    def thoi_gian_check_in_vn(self, obj):
        return obj.thoi_gian_check_in.strftime('%H:%M %d/%m') if obj.thoi_gian_check_in else "-"
    thoi_gian_check_in_vn.short_description = "Vào"

    def thoi_gian_check_out_vn(self, obj):
        return obj.thoi_gian_check_out.strftime('%H:%M %d/%m') if obj.thoi_gian_check_out else "-"
    thoi_gian_check_out_vn.short_description = "Ra"

    def get_nhan_vien(self, obj):
        return format_html('<b>{}</b><br><small style="color:#64748b;">{}</small>', obj.ca_truc.nhan_vien.ho_ten, obj.ca_truc.nhan_vien.ma_nhan_vien)
    get_nhan_vien.short_description = "Nhân sự"

    def get_muc_tieu(self, obj):
        return obj.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu
    get_muc_tieu.short_description = "Mục tiêu"

    def show_thumbnail_in(self, obj):
        if obj.anh_check_in:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="width:45px; height:45px; object-fit:cover; border-radius:6px; border:1px solid #e2e8f0;"></a>', obj.anh_check_in.url, obj.anh_check_in.url)
        return "-"
    show_thumbnail_in.short_description = "📷 Vào"

    def show_thumbnail_out(self, obj):
        if obj.anh_check_out:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="width:45px; height:45px; object-fit:cover; border-radius:6px; border:1px solid #e2e8f0;"></a>', obj.anh_check_out.url, obj.anh_check_out.url)
        return "-"
    show_thumbnail_out.short_description = "📷 Ra"

    def gps_status(self, obj):
        if not obj.vi_tri_hop_le:
            return format_html('<span style="color:white; background:#ef4444; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:bold;">SAI VỊ TRÍ</span>')
        return format_html('<span style="color:white; background:#10b981; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:bold;">HỢP LỆ</span>')
    gps_status.short_description = "GPS"

    def khoang_cach_display(self, obj):
        if obj.khoang_cach_check_in > 1000:
            return f"{round(obj.khoang_cach_check_in/1000, 2)} km"
        return f"{int(obj.khoang_cach_check_in)} m"
    khoang_cach_display.short_description = "Khoảng cách"

    def preview_in(self, obj):
        if obj.anh_check_in: 
            return format_html('<img src="{}" style="max-height:300px; border-radius:8px;">', obj.anh_check_in.url)
        return ""
    
    def preview_out(self, obj):
        if obj.anh_check_out:
            return format_html('<img src="{}" style="max-height:300px; border-radius:8px;">', obj.anh_check_out.url)
        return ""

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ca_truc__nhan_vien', 'ca_truc__vi_tri_chot__muc_tieu')

@admin.register(BaoCaoSuCo)
class BaoCaoSuCoAdmin(admin.ModelAdmin):
    list_display = ('ma_su_co', 'get_muc_do_badge', 'tieu_de', 'muc_tieu', 'nhan_vien_bao_cao', 'created_at_vn', 'trang_thai')
    list_filter = ('muc_do', 'trang_thai', 'created_at')
    search_fields = ('ma_su_co', 'tieu_de', 'nhan_vien_bao_cao__ho_ten', 'muc_tieu__ten_muc_tieu')
    readonly_fields = ('ma_su_co', 'created_at', 'updated_at')
    autocomplete_fields = ['nhan_vien_bao_cao', 'muc_tieu', 'ca_truc', 'nguoi_xu_ly', 'nhan_vien_co_loi']
    
    fieldsets = (
        ('🚩 THÔNG TIN CHUNG', { 
            'fields': (
                ('ma_su_co', 'trang_thai'), 
                ('tieu_de', 'muc_do'), 
            ) 
        }),
        ('🔍 CHI TIẾT SỰ CỐ', { 
            'fields': (
                ('nhan_vien_bao_cao', 'muc_tieu'), 
                ('ca_truc', 'thoi_gian_phat_hien'), 
                'mo_ta_chi_tiet'
            ) 
        }),
        ('🖼️ BẰNG CHỨNG (ẢNH/VOICE)', { 
            'fields': (
                ('hinh_anh_1', 'hinh_anh_2'), 
                'file_ghi_am'
            ) 
        }),
        ('💰 XỬ LÝ & THIỆT HẠI', { 
            'fields': (
                ('tong_thiet_hai', 'cong_ty_chi_tra'), 
                ('nhan_vien_co_loi', 'phai_thu_nhan_vien'), 
                ('nguoi_xu_ly', 'ghi_chu_quan_ly')
            ),
            'classes': ('collapse',)
        })
    )

    def created_at_vn(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_vn.short_description = "Thời gian báo cáo"

    @admin.display(description='Mức độ', ordering='muc_do')
    def get_muc_do_badge(self, obj):
        colors = {'THAP': '#64748b', 'TB': '#3b82f6', 'CAO': '#f59e0b', 'NGUY_HIEM': '#ef4444'}
        return format_html(
            '<span style="color:white; background:{}; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:10px;">{}</span>',
            colors.get(obj.muc_do, '#64748b'),
            obj.get_muc_do_display()
        )

@admin.register(BaoCaoDeXuat)
class BaoCaoDeXuatAdmin(admin.ModelAdmin):
    list_display = ['tieu_de', 'loai_de_xuat', 'nhan_vien', 'muc_tieu', 'trang_thai', 'ngay_gui']
    list_filter = ['trang_thai', 'loai_de_xuat', 'ngay_gui']
    search_fields = ['tieu_de', 'nhan_vien__ho_ten']
    readonly_fields = ['ngay_gui']
    autocomplete_fields = ['nhan_vien', 'muc_tieu', 'chi_huy_duyet', 'nguoi_duyet_nghiep_vu']
    
    fieldsets = (
        ('💡 THÔNG TIN ĐỀ XUẤT', {
            'fields': (
                ('nhan_vien', 'muc_tieu'),
                ('loai_de_xuat', 'tieu_de'),
                'noi_dung', 'hinh_anh', 'ngay_gui'
            )
        }),
        ('👮 PHÊ DUYỆT CHỈ HUY', {
            'fields': (
                'chi_huy_duyet', 
                'y_kien_chi_huy', 
                'thoi_gian_chi_huy_duyet'
            ),
            'classes': ('collapse',),
        }),
        ('🏢 PHÊ DUYỆT NGHIỆP VỤ (VĂN PHÒNG)', {
            'fields': (
                'trang_thai', 
                'nguoi_duyet_nghiep_vu', 
                'y_kien_nghiep_vu', 
                'thoi_gian_nghiep_vu_duyet'
            ),
        }),
    )

@admin.register(KiemTraQuanSo)
class KiemTraQuanSoAdmin(admin.ModelAdmin):
    list_display = ('ca_truc', 'thoi_gian_gui_yeu_cau', 'thoi_gian_phan_hoi', 'trang_thai_badge')
    list_filter = ('trang_thai', 'thoi_gian_gui_yeu_cau')
    autocomplete_fields = ['ca_truc']

    @admin.display(description="Trạng thái phản hồi")
    def trang_thai_badge(self, obj):
        color = "#10b981" if obj.trang_thai == 'DA_PHAN_HOI' else "#f59e0b"
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, obj.get_trang_thai_display())
