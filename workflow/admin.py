# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: task_proposal/admin.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-21
Description: Quản lý Công việc, Tờ trình và Quy trình Phê duyệt đa cấp.
             ENHANCEMENT: Tối ưu SQL (N+1 queries), UI Badge chuyên nghiệp, 
             với liên kết dữ liệu chéo (Cross-reference).
"""

import datetime
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db import models

from .models import Task, Proposal, PheDuyetLog

# --- CONFIG MÀU SẮC ĐỒNG BỘ HỆ THỐNG SCMD ---
UI_COLORS = {
    'SUCCESS': '#10b981', # Green (Hoàn thành/Đã duyệt)
    'INFO': '#3b82f6',    # Blue (Mới/Yêu cầu sửa)
    'WARNING': '#f59e0b', # Amber (Chờ duyệt/Ưu tiên cao)
    'DANGER': '#ef4444',  # Red (Hủy/Từ chối/Khẩn cấp)
    'PURPLE': '#8b5cf6',  # Purple (Đang làm)
    'SLATE': '#64748b',   # Slate (Nháp/Ưu tiên thấp)
}

# ==============================================================================
# 1. QUẢN LÝ CÔNG VIỆC (TASK)
# ==============================================================================
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # --- UI & DISPLAY CONFIG ---
    list_display = (
        'tieu_de', 
        'nguoi_nhan_short', 
        'nguoi_giao_short', 
        'uu_tien_badge', 
        'trang_thai_badge', 
        'han_chot_display', 
        'tien_do_bar'
    )
    
    list_filter = (
        'trang_thai', 
        'uu_tien', 
        ('han_chot', admin.DateFieldListFilter),
        'nguoi_nhan',
        'muc_tieu'
    )
    
    search_fields = (
        'tieu_de', 
        'nguoi_nhan__ho_ten', 
        'nguoi_giao__ho_ten', 
        'muc_tieu__ten_muc_tieu'
    )
    filter_horizontal = ('nguoi_phoi_hop',)
    autocomplete_fields = ['nguoi_nhan', 'nguoi_giao', 'muc_tieu']
    date_hierarchy = 'ngay_tao'
    save_on_top = True
    list_per_page = 25

    fieldsets = (
        (_("📌 THÔNG TIN CHUNG"), {
            'fields': ('tieu_de', 'noi_dung', 'muc_tieu', 'file_dinh_kem')
        }),
        (_("👥 PHÂN CÔNG"), {
            'fields': (('nguoi_giao', 'nguoi_nhan'), 'nguoi_phoi_hop')
        }),
        (_("📊 TIẾN ĐỘ & TRẠNG THÁI"), {
            'fields': (('uu_tien', 'trang_thai'), ('han_chot', 'tien_do'))
        }),
    )

    # --- TỐI ƯU HIỆU NĂNG TRUY VẤN ---
    def get_queryset(self, request):
        """Giảm số lượng SQL queries từ N+1 xuống 1 bằng select_related & prefetch_related."""
        return super().get_queryset(request).select_related(
            'nguoi_nhan', 'nguoi_giao', 'muc_tieu'
        ).prefetch_related('nguoi_phoi_hop')

    # --- CUSTOM DISPLAY METHODS ---
    @admin.display(description=_("Người nhận"), ordering='nguoi_nhan__ho_ten')
    def nguoi_nhan_short(self, obj):
        try:
            return obj.nguoi_nhan.ho_ten if obj.nguoi_nhan else "-"
        except Exception:
            return "-"

    @admin.display(description=_("Người giao"), ordering='nguoi_giao__ho_ten')
    def nguoi_giao_short(self, obj):
        try:
            return obj.nguoi_giao.ho_ten if obj.nguoi_giao else "-"
        except Exception:
            return "-"

    @admin.display(description=_("Hạn chót"), ordering='han_chot')
    def han_chot_display(self, obj):
        if not obj.han_chot: 
            return "-"
        return obj.han_chot.strftime('%d/%m/%Y')

    @admin.display(description=_("Độ ưu tiên"))
    def uu_tien_badge(self, obj):
        colors = {
            'THAP': UI_COLORS['SLATE'], 
            'TB': UI_COLORS['INFO'], 
            'CAO': UI_COLORS['WARNING'], 
            'KHAN': UI_COLORS['DANGER']
        }
        label = obj.get_uu_tien_display().upper() if obj.uu_tien else "-"
        color = colors.get(obj.uu_tien, 'black')
        return format_html(
            '<span style="color:{}; font-weight:800; font-size:10px;">● {}</span>',
            color, label
        )

    @admin.display(description=_("Trạng thái"))
    def trang_thai_badge(self, obj):
        bg_colors = {
            'MOI': UI_COLORS['INFO'], 
            'DANG_LAM': UI_COLORS['PURPLE'], 
            'CHO_DUYET': UI_COLORS['WARNING'], 
            'HOAN_THANH': UI_COLORS['SUCCESS'], 
            'HUY': UI_COLORS['DANGER']
        }
        label = obj.get_trang_thai_display() if obj.trang_thai else "-"
        bg_color = bg_colors.get(obj.trang_thai, '#666')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 10px; border-radius:12px; '
            'font-size:10px; font-weight:bold; box-shadow:0 1px 2px rgba(0,0,0,0.15);">{}</span>',
            bg_color, label
        )

    @admin.display(description=_("Tiến độ"))
    def tien_do_bar(self, obj):
        val = obj.tien_do or 0
        color = UI_COLORS['SUCCESS'] if val == 100 else UI_COLORS['INFO']
        return format_html(
            '<div style="width:80px; background:#f1f5f9; border-radius:10px; height:8px; '
            'display:inline-block; border:1px solid #e2e8f0; vertical-align:middle; overflow:hidden;">'
            '<div style="width:{}%; background:{}; height:100%;"></div>'
            '</div> <span style="font-size:11px; font-weight:800; color:#475569; margin-left:5px;">{}%</span>',
            val, color, val
        )


# ==============================================================================
# 2. QUẢN LÝ TỜ TRÌNH (PROPOSAL)
# ==============================================================================
class PheDuyetLogInline(admin.TabularInline):
    model = PheDuyetLog
    extra = 0
    readonly_fields = ('nguoi_xu_ly', 'hanh_dong_badge', 'y_kien', 'nguoi_nhan_tiep_theo', 'thoi_gian_display')
    can_delete = False
    verbose_name = _("Nhật ký xử lý")
    verbose_name_plural = _("📅 LỊCH SỬ PHÊ DUYỆT")
    classes = ['collapse']

    def has_add_permission(self, request, obj=None): 
        return False
    
    @admin.display(description=_("Thời gian"))
    def thoi_gian_display(self, obj):
        if not obj.thoi_gian:
            return "-"
        return obj.thoi_gian.strftime('%H:%M %d/%m/%Y')

    @admin.display(description=_("Hành động"))
    def hanh_dong_badge(self, obj):
        label = obj.get_hanh_dong_display() if obj.hanh_dong else "-"
        return format_html('<b>{}</b>', label)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    # --- UI & DISPLAY CONFIG ---
    list_display = (
        'tieu_de', 
        'loai_de_xuat', 
        'nguoi_de_xuat', 
        'current_approver', 
        'status_badge', 
        'ngay_tao_vn'
    )
    list_filter = ('trang_thai', 'loai_de_xuat', ('ngay_tao', admin.DateFieldListFilter))
    search_fields = ('tieu_de', 'nguoi_de_xuat__ho_ten', 'noi_dung')
    autocomplete_fields = ['nguoi_de_xuat', 'nguoi_duyet_hien_tai']
    inlines = [PheDuyetLogInline]
    save_on_top = True
    date_hierarchy = 'ngay_tao'

    fieldsets = (
        (_("📄 NỘI DUNG TỜ TRÌNH"), {
            'fields': ('tieu_de', 'loai_de_xuat', 'noi_dung', 'file_dinh_kem')
        }),
        (_("⚙️ QUY TRÌNH DUYỆT"), {
            'fields': (('nguoi_de_xuat', 'nguoi_duyet_hien_tai'), 'trang_thai')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('nguoi_de_xuat', 'nguoi_duyet_hien_tai')

    @admin.display(description=_("Ngày tạo"), ordering='ngay_tao')
    def ngay_tao_vn(self, obj):
        if not obj.ngay_tao:
            return "-"
        return obj.ngay_tao.strftime('%d/%m/%Y %H:%M')

    @admin.display(description=_("Đang chờ duyệt"))
    def current_approver(self, obj):
        if obj.nguoi_duyet_hien_tai:
            return format_html(
                '<div style="color:{}; font-weight:700;">'
                '<i class="fas fa-user-clock" style="font-size:11px; margin-right:4px;"></i>{}'
                '</div>',
                UI_COLORS['WARNING'],
                obj.nguoi_duyet_hien_tai.ho_ten
            )
        return format_html('<small style="color:#cbd5e1; font-style:italic;">(Kết thúc quy trình)</small>')

    @admin.display(description=_("Trạng thái"))
    def status_badge(self, obj):
        colors = {
            'NHAP': UI_COLORS['SLATE'],
            'CHO_DUYET': UI_COLORS['WARNING'], 
            'DA_DUYET': UI_COLORS['SUCCESS'],  
            'TU_CHOI': UI_COLORS['DANGER'],   
            'YEU_CAU_SUA': UI_COLORS['INFO'] 
        }
        label = obj.get_trang_thai_display() if obj.trang_thai else "-"
        bg_color = colors.get(obj.trang_thai, '#666')
        return format_html(
            '<span style="background-color:{}; color:white; padding:4px 10px; border-radius:6px; '
            'font-size:10px; font-weight:800; text-transform:uppercase;">{}</span>',
            bg_color, label
        )


# ==============================================================================
# 3. NHẬT KÝ PHÊ DUYỆT (LOGS - READONLY SYSTEM)
# ==============================================================================
@admin.register(PheDuyetLog)
class PheDuyetLogAdmin(admin.ModelAdmin):
    list_display = ('thoi_gian_vn', 'proposal_link', 'nguoi_xu_ly', 'hanh_dong_badge', 'y_kien_short')
    list_filter = ('hanh_dong', ('thoi_gian', admin.DateFieldListFilter))
    search_fields = ('proposal__tieu_de', 'nguoi_xu_ly__ho_ten', 'y_kien')
    ordering = ('-thoi_gian',)
    
    def has_add_permission(self, request): 
        return False
    
    def has_change_permission(self, request, obj=None): 
        return False
    
    def has_delete_permission(self, request, obj=None): 
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposal', 'nguoi_xu_ly')

    @admin.display(description=_("Thời gian"), ordering='thoi_gian')
    def thoi_gian_vn(self, obj):
        if not obj.thoi_gian:
            return "-"
        return obj.thoi_gian.strftime('%H:%M %d/%m/%Y')

    @admin.display(description=_("Tờ trình liên quan"))
    def proposal_link(self, obj):
        if obj.proposal:
            # Lưu ý: admin:task_proposal_proposal_change tùy thuộc vào app_label và model_name
            try:
                url = reverse("admin:task_proposal_proposal_change", args=[obj.proposal.id])
                return format_html('<a href="{}" style="font-weight:bold; color:#3b82f6;">{}</a>', url, obj.proposal.tieu_de)
            except Exception:
                return obj.proposal.tieu_de
        return "-"

    @admin.display(description=_("Hành động"))
    def hanh_dong_badge(self, obj):
        bg = UI_COLORS['SUCCESS'] if obj.hanh_dong == 'DUYET' else UI_COLORS['DANGER'] if obj.hanh_dong == 'TU_CHOI' else UI_COLORS['INFO']
        label = obj.get_hanh_dong_display() if obj.hanh_dong else "-"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            bg, label
        )

    @admin.display(description=_("Ý kiến xử lý"))
    def y_kien_short(self, obj):
        if not obj.y_kien: 
            return "-"
        return obj.y_kien[:50] + "..." if len(obj.y_kien) > 50 else obj.y_kien