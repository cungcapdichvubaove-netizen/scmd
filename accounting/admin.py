# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: accounting/admin.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-04
Updated Date: 2026-03-21
Description: Cấu hình Admin Kế toán (PRO UI).
             UPDATED: Sửa lỗi lọc phòng ban (E116), Tối ưu SQL, 
             Chuyên nghiệp hóa định dạng tiền tệ & Ngày tháng.
"""

from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import CauHinhLuong, BangLuongThang, ChiTietLuong
from .models_soquy import SoQuy
from .services.payroll import PayrollService

# --- CONFIG MÀU SẮC ĐỒNG BỘ HỆ THỐNG SCMD ---
UI_COLORS = {
    'SUCCESS': '#059669', # Emerald 600
    'DANGER': '#dc2626',  # Red 600
    'WARNING': '#ea580c', # Orange 600
    'INFO': '#3b82f6',    # Blue 600
    'NEUTRAL': '#374151', # Gray 700
    'BG_SUCCESS': '#dcfce7',
    'BORDER_SUCCESS': '#86efac',
}

# ==============================================================================
# 1. CẤU HÌNH LƯƠNG CƠ BẢN
# ==============================================================================
@admin.register(CauHinhLuong)
class CauHinhLuongAdmin(admin.ModelAdmin):
    """Quản lý cấu hình lương cơ bản cho nhân viên an ninh SCMD"""
    list_display = [
        'nhan_vien', 
        'phu_cap_trach_nhiem_vnd', 
        'phu_cap_xang_xe_vnd', 
        'phu_cap_an_uong_vnd'
    ]
    search_fields = ['nhan_vien__ho_ten', 'nhan_vien__ma_nhan_vien']
    autocomplete_fields = ['nhan_vien']
    list_per_page = 25

    def get_queryset(self, request):
        """Tối ưu hóa truy vấn liên kết nhân viên"""
        return super().get_queryset(request).select_related('nhan_vien')

    @admin.display(description=_("P.Cấp Trách Nhiệm"))
    def phu_cap_trach_nhiem_vnd(self, obj):
        val = obj.phu_cap_trach_nhiem or 0
        return f"{val:,.0f} ₫".replace(",", ".")

    @admin.display(description=_("P.Cấp Xăng Xe"))
    def phu_cap_xang_xe_vnd(self, obj):
        val = obj.phu_cap_xang_xe or 0
        return f"{val:,.0f} ₫".replace(",", ".")

    @admin.display(description=_("P.Cấp Ăn Uống"))
    def phu_cap_an_uong_vnd(self, obj):
        val = obj.phu_cap_an_uong or 0
        return f"{val:,.0f} ₫".replace(",", ".")


# ==============================================================================
# 2. INLINE CHI TIẾT LƯƠNG
# ==============================================================================
class ChiTietLuongInline(admin.TabularInline):
    """Hiển thị chi tiết bảng lương dạng dòng (Inline) cho chuyên viên kế toán"""
    model = ChiTietLuong
    extra = 0
    can_delete = False
    
    fields = [
        'nhan_vien', 
        'hien_thi_cong', 
        'hien_thi_luong_chinh', 
        'hien_thi_phu_cap', 
        'hien_thi_phat', 
        'hien_thi_ung', 
        'hien_thi_thuc_lanh'
    ]
    readonly_fields = [
        'nhan_vien',
        'hien_thi_cong', 
        'hien_thi_luong_chinh', 
        'hien_thi_phu_cap', 
        'hien_thi_phat', 
        'hien_thi_ung', 
        'hien_thi_thuc_lanh'
    ]

    @admin.display(description=_("Giờ công"))
    def hien_thi_cong(self, obj):
        """Định dạng hiển thị giờ công nhân viên"""
        val = obj.tong_gio_lam or 0
        return format_html(
            '<span style="font-weight:bold; background:#e2e8f0; padding:3px 8px; border-radius:4px;">{}h</span>',
            val
        )

    @admin.display(description=_("Lương chính"))
    def hien_thi_luong_chinh(self, obj):
        """Định dạng lương cơ bản"""
        val = obj.luong_chinh or 0
        return f"{val:,.0f} ₫".replace(",", ".")

    @admin.display(description=_("P.Cấp Khác"))
    def hien_thi_phu_cap(self, obj):
        """Hiển thị phụ cấp khác (Màu xanh dương/lá)"""
        val = obj.phu_cap_khac or 0
        if val > 0:
            return format_html('<span style="color:{}; font-weight:500;">+{:,.0f}</span>', UI_COLORS['SUCCESS'], val)
        return "-"

    @admin.display(description=_("Phạt/Vi phạm"))
    def hien_thi_phat(self, obj):
        """Hiển thị khoản trừ/phạt (Màu đỏ)"""
        val = obj.phat_vi_pham or 0
        if val > 0:
            return format_html('<span style="color:{}; font-weight:bold;">-{:,.0f}</span>', UI_COLORS['DANGER'], val)
        return "-"

    @admin.display(description=_("Tạm ứng"))
    def hien_thi_ung(self, obj):
        """Hiển thị tạm ứng (Màu cam)"""
        val = obj.ung_luong or 0
        if val > 0:
            return format_html('<span style="color:{};">-{:,.0f}</span>', UI_COLORS['WARNING'], val)
        return "-"

    @admin.display(description=_("THỰC LÃNH"))
    def hien_thi_thuc_lanh(self, obj):
        """Tổng hợp số tiền thực nhận sau khi trừ các khoản"""
        val = obj.thuc_lanh or 0
        return format_html(
            '<span style="font-size:12px; font-weight:bold; color:{}; background:{}; '
            'padding:4px 8px; border-radius:4px; border:1px solid {}; display:inline-block; min-width:100px; text-align:right;">'
            '{:,.0f} VNĐ</span>',
            UI_COLORS['SUCCESS'], UI_COLORS['BG_SUCCESS'], UI_COLORS['BORDER_SUCCESS'], val
        )


# ==============================================================================
# 3. BẢNG LƯƠNG THÁNG (MAIN)
# ==============================================================================
@admin.register(BangLuongThang)
class BangLuongThangAdmin(admin.ModelAdmin):
    """Quản trị bảng lương tổng hợp hàng tháng của SCMD"""
    list_display = [
        'ten_bang_luong', 
        'thang', 
        'nam', 
        'hien_thi_tong_chi', 
        'trang_thai_badge', 
        'nut_xem_bao_cao'
    ]
    list_filter = ['nam', 'trang_thai', 'thang']
    search_fields = ['ten_bang_luong']
    inlines = [ChiTietLuongInline]
    actions = ['tinh_luong_lai', 'phat_hanh_luong']
    list_per_page = 20

    @admin.display(description=_("Tổng ngân sách chi"))
    def hien_thi_tong_chi(self, obj):
        val = obj.tong_chi_tra or 0
        return format_html('<b>{:,.0f} VNĐ</b>', val)

    @admin.display(description=_("Trạng thái phê duyệt"))
    def trang_thai_badge(self, obj):
        """Badge trạng thái bảng lương chuẩn UI/UX SCMD"""
        colors = {
            'DA_PHAT_HANH': (UI_COLORS['SUCCESS'], UI_COLORS['BG_SUCCESS']),
            'CHO_DUYET': (UI_COLORS['WARNING'], '#ffedd5'),
            'NHAP': (UI_COLORS['NEUTRAL'], '#f3f4f6'),
        }
        text_color, bg_color = colors.get(obj.trang_thai, (UI_COLORS['NEUTRAL'], '#f3f4f6'))
        return format_html(
            '<span style="color:{}; background:{}; padding:2px 10px; border-radius:12px; font-weight:bold; font-size:11px;">{}</span>',
            text_color, bg_color, obj.get_trang_thai_display()
        )

    @admin.display(description=_("Công cụ báo cáo"))
    def nut_xem_bao_cao(self, obj):
        """Nút truy cập nhanh báo cáo chuyên nghiệp"""
        if obj.pk:
            url = f"/accounting/bang-luong/{obj.pk}/"
            return format_html(
                '<a href="{}" target="_blank" class="button" '
                'style="background:#3b82f6; color:white; padding:4px 12px; border-radius:4px; '
                'text-decoration:none; font-size:11px; font-weight:bold;">🖨️ XEM PHIẾU LƯƠNG</a>', 
                url
            )
        return "-"

    def tinh_luong_lai(self, request, queryset):
        """Thực thi tính toán lại số liệu lương định kỳ"""
        count = 0
        error_count = 0
        for bl in queryset:
            if bl.trang_thai == 'DA_PHAT_HANH':
                self.message_user(request, f"Cảnh báo: Bảng lương {bl} đã khóa sổ!", messages.WARNING)
                continue
            
            try:
                with transaction.atomic():
                    success, msg = PayrollService.tinh_luong_thang(bl.thang, bl.nam)
                    if success:
                        count += 1
                        bl.refresh_from_db()
                    else:
                        error_count += 1
                        self.message_user(request, f"Lỗi nghiệp vụ tại {bl}: {msg}", messages.ERROR)
            except Exception as e:
                error_count += 1
                self.message_user(request, f"Lỗi hệ thống khi xử lý {bl}: {str(e)}", messages.ERROR)
        
        if count > 0:
            self.message_user(request, f"Thực thi thành công: Đã cập nhật {count} bảng lương.", messages.SUCCESS)
        if error_count > 0:
            self.message_user(request, f"Thông báo: Có {error_count} bảng lương gặp lỗi.", messages.ERROR)

    tinh_luong_lai.short_description = "⚡ TÁNH TOÁN LẠI SỐ LIỆU (TỰ ĐỘNG)"

    def phat_hanh_luong(self, request, queryset):
        """Chốt sổ lương hàng tháng"""
        try:
            updated = queryset.filter(trang_thai__in=['NHAP', 'CHO_DUYET']).update(trang_thai='DA_PHAT_HANH')
            self.message_user(request, f"Xác nhận: Đã khóa sổ {updated} bảng lương thành công.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Lỗi khi thực hiện khóa sổ: {str(e)}", messages.ERROR)

    phat_hanh_luong.short_description = "✅ CHỐT SỔ & PHÁT HÀNH (KHÔNG SỬA)"


# ==============================================================================
# 4. CHI TIẾT LƯƠNG CÁ NHÂN
# ==============================================================================
@admin.register(ChiTietLuong)
class ChiTietLuongAdmin(admin.ModelAdmin):
    """Quản lý chi tiết thu nhập từng nhân viên an ninh"""
    list_display = [
        'nhan_vien', 
        'bang_luong', 
        'tong_gio_lam_format', 
        'luong_chinh_format', 
        'thuc_lanh_format'
    ]
    # FIXED: Sửa lỗi (admin.E116) - nhan_vien__bo_phan -> nhan_vien__phong_ban
    list_filter = ['bang_luong__thang', 'bang_luong__nam', 'nhan_vien__phong_ban']
    search_fields = ['nhan_vien__ho_ten', 'nhan_vien__ma_nhan_vien']
    readonly_fields = ['thuc_lanh']

    def get_queryset(self, request):
        """Tối ưu hóa query tránh N+1 cho thông tin nhân viên và phòng ban"""
        return super().get_queryset(request).select_related(
            'nhan_vien', 
            'nhan_vien__phong_ban', 
            'bang_luong'
        )

    @admin.display(description=_("Công làm việc"), ordering='tong_gio_lam')
    def tong_gio_lam_format(self, obj):
        val = obj.tong_gio_lam or 0
        return f"{val} giờ"

    @admin.display(description=_("Lương cơ bản"))
    def luong_chinh_format(self, obj):
        val = obj.luong_chinh or 0
        return f"{val:,.0f} ₫".replace(",", ".")

    @admin.display(description=_("Thực lĩnh"))
    def thuc_lanh_format(self, obj):
        val = obj.thuc_lanh or 0
        return format_html('<b style="color: {};">{:,.0f} VNĐ</b>', UI_COLORS['SUCCESS'], val)


# ==============================================================================
# 5. QUẢN LÝ SỔ QUỸ (CASHFLOW)
# ==============================================================================
@admin.register(SoQuy)
class SoQuyAdmin(admin.ModelAdmin):
    """Quản lý sổ quỹ tiền mặt và dòng tiền nghiệp vụ SCMD"""
    list_display = [
        'ma_phieu', 
        'loai_phieu', 
        'hang_muc', 
        'so_tien_vnd', 
        'ngay_lap_format', 
        'trang_thai_format'
    ]
    list_filter = ['loai_phieu', 'hang_muc', 'trang_thai', 'ngay_lap']
    search_fields = ['ma_phieu', 'dien_giai']
    date_hierarchy = 'ngay_lap'
    ordering = ['-ngay_lap', '-ma_phieu']

    @admin.display(description=_("Số tiền giao dịch"), ordering='so_tien')
    def so_tien_vnd(self, obj):
        val = obj.so_tien or 0
        is_chi = obj.loai_phieu == 'CHI'
        color = UI_COLORS['DANGER'] if is_chi else UI_COLORS['SUCCESS']
        prefix = "-" if is_chi else "+"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}{:,.0f} ₫</span>', 
            color, prefix, val
        )

    @admin.display(description=_("Ngày lập phiếu"), ordering='ngay_lap')
    def ngay_lap_format(self, obj):
        if not obj.ngay_lap: return "-"
        return obj.ngay_lap.strftime('%d/%m/%Y')

    @admin.display(description=_("Tình trạng"))
    def trang_thai_format(self, obj):
        status_colors = {
            'HOAN_THANH': UI_COLORS['SUCCESS'],
            'HUY': UI_COLORS['DANGER'],
            'CHO_DUYET': UI_COLORS['WARNING'],
        }
        color = status_colors.get(obj.trang_thai, UI_COLORS['NEUTRAL'])
        label = obj.get_trang_thai_display() if hasattr(obj, 'get_trang_thai_display') else obj.trang_thai
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, label)