# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: accounting/admin.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-04
<<<<<<< HEAD
Updated Date: 2026-06-08
Description: Cấu hình Admin Kế toán (SCMD Pro).
=======
Updated Date: 2026-03-21
Description: Cấu hình Admin Kế toán (PRO UI).
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
             UPDATED: Sửa lỗi lọc phòng ban (E116), Tối ưu SQL, 
             Chuyên nghiệp hóa định dạng tiền tệ & Ngày tháng.
"""

<<<<<<< HEAD
import csv
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.contrib import admin
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.contrib import messages
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.workflow_transition_policy import WorkflowTransitionPolicy
from .models import CauHinhLuong, BangLuongThang, ChiTietLuong, PayrollAdjustment, TamUngLuong, KhoanKhauTruNhanVien
from users.access_policies import StaffVisibilityPolicy
from accounting.application.payroll_use_cases import (
    AuditPayrollUseCase,
    LockPayrollBatchUseCase,
    RecalculatePayrollBatchUseCase,
)
from .models_soquy import SoQuy
from main.models import AuditLog
=======
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import CauHinhLuong, BangLuongThang, ChiTietLuong
from accounting.application.payroll_use_cases import AuditPayrollUseCase
from .models_soquy import SoQuy
from .services.payroll import PayrollService
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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

<<<<<<< HEAD

def _format_vnd(value):
    """Format tiền VND nhất quán trong admin kế toán."""
    value = value or 0
    return f"{value:,.0f} ₫".replace(",", ".")


def _current_employee(request):
    try:
        return request.user.nhan_vien
    except Exception:
        return None


def _request_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _audit_admin_action(request, *, action, model_name, object_id="", note="", changes=None):
    payload = {
        "user": request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        "action": action,
        "module": "accounting",
        "model_name": model_name,
        "object_id": str(object_id) if object_id else "",
        "changes": changes or {},
        "ip_address": _request_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:1000],
        "note": note,
    }
    if hasattr(settings, "SCMD_ORGANIZATION_ID"):
        payload["tenant_id"] = settings.SCMD_ORGANIZATION_ID
    AuditLog.objects.create(**payload)



def _apply_accounting_status_action(request, queryset, *, model_name, target_status, note, filter_status=None, update_extra=None):
    changed = 0
    qs = queryset.filter(trang_thai=filter_status) if filter_status else queryset
    update_extra = update_extra or {}
    with transaction.atomic():
        for obj in qs.select_for_update().order_by("pk"):
            old_status = obj.trang_thai
            if old_status == target_status:
                continue
            obj.trang_thai = target_status
            update_fields = ["trang_thai"]
            for field_name, value in update_extra.items():
                setattr(obj, field_name, value)
                update_fields.append(field_name)
            obj.save(update_fields=update_fields)
            _audit_admin_action(
                request,
                action=AuditLog.Action.UPDATE,
                model_name=model_name,
                object_id=obj.pk,
                note=note,
                changes={"trang_thai": {"old": old_status, "new": target_status}},
            )
            changed += 1
    return changed

class SalaryConfigOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng cấu hình"
    parameter_name = "salary_config_issue"

    def lookups(self, request, model_admin):
        return (
            ("missing_base", "Thiếu lương BHXH"),
            ("no_allowance", "Chưa có phụ cấp"),
            ("has_allowance", "Có phụ cấp"),
            ("responsibility", "Có phụ cấp trách nhiệm"),
            ("transport", "Có phụ cấp xăng xe"),
            ("meal", "Có phụ cấp ăn ca"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing_base":
            return queryset.filter(Q(luong_co_ban_ngay__isnull=True) | Q(luong_co_ban_ngay=0))
        if value == "no_allowance":
            return queryset.filter(
                Q(phu_cap_trach_nhiem__isnull=True) | Q(phu_cap_trach_nhiem=0),
                Q(phu_cap_xang_xe__isnull=True) | Q(phu_cap_xang_xe=0),
                Q(phu_cap_an_uong__isnull=True) | Q(phu_cap_an_uong=0),
            )
        if value == "has_allowance":
            return queryset.filter(
                Q(phu_cap_trach_nhiem__gt=0) | Q(phu_cap_xang_xe__gt=0) | Q(phu_cap_an_uong__gt=0)
            )
        if value == "responsibility":
            return queryset.filter(phu_cap_trach_nhiem__gt=0)
        if value == "transport":
            return queryset.filter(phu_cap_xang_xe__gt=0)
        if value == "meal":
            return queryset.filter(phu_cap_an_uong__gt=0)
        return queryset


class PayrollDetailOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng phiếu lương"
    parameter_name = "payroll_detail_issue"

    def lookups(self, request, model_admin):
        return (
            ("locked_batch", "Thuộc kỳ đã khóa/đã trả"),
            ("editable_batch", "Kỳ còn được rà soát"),
            ("has_violation", "Có phạt vi phạm"),
            ("has_advance", "Có tạm ứng"),
            ("has_uniform", "Có khấu trừ đồng phục"),
            ("has_compensation", "Có đền bù sự cố"),
            ("zero_hours", "Không có giờ công"),
            ("non_positive_net", "Thực lĩnh <= 0"),
            ("missing_snapshot", "Thiếu snapshot nguồn"),
            ("missing_reconciliation", "Thiếu ghi chú đối soát"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        locked_states = [BangLuongThang.TrangThai.LOCKED, BangLuongThang.TrangThai.PAID]
        if value == "locked_batch":
            return queryset.filter(bang_luong__trang_thai__in=locked_states)
        if value == "editable_batch":
            return queryset.exclude(bang_luong__trang_thai__in=locked_states)
        if value == "has_violation":
            return queryset.filter(phat_vi_pham__gt=0)
        if value == "has_advance":
            return queryset.filter(ung_luong__gt=0)
        if value == "has_uniform":
            return queryset.filter(tien_dong_phuc__gt=0)
        if value == "has_compensation":
            return queryset.filter(tien_den_bu__gt=0)
        if value == "zero_hours":
            return queryset.filter(Q(tong_gio_lam__isnull=True) | Q(tong_gio_lam=0))
        if value == "non_positive_net":
            return queryset.filter(thuc_lanh__lte=0)
        if value == "missing_snapshot":
            return queryset.filter(Q(nguon_du_lieu_snapshot__isnull=True) | Q(nguon_du_lieu_snapshot={}))
        if value == "missing_reconciliation":
            return queryset.filter(Q(reconciliation_note__isnull=True) | Q(reconciliation_note__exact=""))
        return queryset


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# ==============================================================================
# 1. CẤU HÌNH LƯƠNG CƠ BẢN
# ==============================================================================
@admin.register(CauHinhLuong)
class CauHinhLuongAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    """Quản lý cấu hình lương cố định theo từng nhân viên, có audit khi export/sửa dữ liệu."""
    change_list_template = 'accounting/admin/cauhinhluong_change_list.html'
    list_display = [
        'nhan_vien_hien_thi',
        'luong_bhxh_vnd',
        'phu_cap_trach_nhiem_vnd',
        'phu_cap_xang_xe_vnd',
        'phu_cap_an_uong_vnd',
        'tong_phu_cap_vnd',
        'trang_thai_cau_hinh',
        'hanh_dong_nhanh',
    ]
    list_filter = [SalaryConfigOperationalFilter]
    search_fields = ['nhan_vien__ho_ten', 'nhan_vien__ma_nhan_vien', 'nhan_vien__so_dien_thoai']
    autocomplete_fields = ['nhan_vien']
    readonly_fields = ['tenant_id']
    list_per_page = 25
    save_on_top = True
    ordering = ['nhan_vien__ho_ten']

    fieldsets = (
        ('Nhân viên thụ hưởng', {
            'fields': ('nhan_vien',),
            'description': 'Mỗi nhân viên chỉ có một hồ sơ cấu hình lương cố định. Dữ liệu này ảnh hưởng trực tiếp đến đối soát lương.',
        }),
        ('Lương căn bản và phụ cấp cố định', {
            'fields': (
                'luong_co_ban_ngay',
                ('phu_cap_trach_nhiem', 'phu_cap_xang_xe', 'phu_cap_an_uong'),
            ),
        }),
        ('Thông tin hệ thống', {
            'fields': ('tenant_id',),
            'classes': ('collapse',),
        }),
    )

    def get_urls(self):
        custom_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv), name='accounting_cauhinhluong_export_csv'),
        ]
        return custom_urls + super().get_urls()

    def get_queryset(self, request):
        """Tối ưu query nhân viên và phòng ban, tránh N+1 trên changelist."""
        scoped_staff_ids = StaffVisibilityPolicy.visible_staff(request.user).values_list("pk", flat=True)
        return (
            super().get_queryset(request)
            .filter(nhan_vien_id__in=scoped_staff_ids)
            .select_related('nhan_vien', 'nhan_vien__phong_ban')
        )

    def changelist_view(self, request, extra_context: Optional[dict[str, Any]] = None):
        queryset = self.get_queryset(request)
        summary = queryset.aggregate(
            total_configs=Count('id'),
            total_base=Sum('luong_co_ban_ngay'),
            total_responsibility=Sum('phu_cap_trach_nhiem'),
            total_transport=Sum('phu_cap_xang_xe'),
            total_meal=Sum('phu_cap_an_uong'),
        )
        no_allowance_count = queryset.filter(
            Q(phu_cap_trach_nhiem__isnull=True) | Q(phu_cap_trach_nhiem=0),
            Q(phu_cap_xang_xe__isnull=True) | Q(phu_cap_xang_xe=0),
            Q(phu_cap_an_uong__isnull=True) | Q(phu_cap_an_uong=0),
        ).count()
        summary.update({
            'missing_base_count': queryset.filter(Q(luong_co_ban_ngay__isnull=True) | Q(luong_co_ban_ngay=0)).count(),
            'no_allowance_count': no_allowance_count,
            'has_allowance_count': queryset.filter(
                Q(phu_cap_trach_nhiem__gt=0) | Q(phu_cap_xang_xe__gt=0) | Q(phu_cap_an_uong__gt=0)
            ).count(),
            'responsibility_count': queryset.filter(phu_cap_trach_nhiem__gt=0).count(),
            'transport_count': queryset.filter(phu_cap_xang_xe__gt=0).count(),
            'meal_count': queryset.filter(phu_cap_an_uong__gt=0).count(),
        })
        query_string = request.GET.urlencode()
        extra_context = extra_context or {}
        extra_context.update({
            'salary_config_summary': summary,
            'export_csv_url': f'export-csv/?{query_string}' if query_string else 'export-csv/',
        })
        return super().changelist_view(request, extra_context=extra_context)

    def _filtered_queryset_for_export(self, request):
        request.GET = request.GET.copy()
        request.GET.pop('all', None)
        request.GET.pop('o', None)
        request.GET.pop('p', None)
        return self.get_changelist_instance(request).queryset

    def export_csv(self, request):
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        queryset = self._filtered_queryset_for_export(request)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="scmdpro-cau-hinh-luong.csv"'
        response.write('﻿')
        writer = csv.writer(response)
        writer.writerow([
            'Mã nhân viên',
            'Họ tên',
            'Phòng ban',
            'Lương đóng BHXH',
            'Phụ cấp trách nhiệm',
            'Phụ cấp xăng xe',
            'Phụ cấp ăn ca',
            'Tổng phụ cấp',
        ])
        for obj in queryset:
            employee = obj.nhan_vien
            writer.writerow([
                getattr(employee, 'ma_nhan_vien', ''),
                getattr(employee, 'ho_ten', ''),
                getattr(getattr(employee, 'phong_ban', None), 'ten_phong_ban', ''),
                obj.luong_co_ban_ngay or 0,
                obj.phu_cap_trach_nhiem or 0,
                obj.phu_cap_xang_xe or 0,
                obj.phu_cap_an_uong or 0,
                self._tong_phu_cap(obj),
            ])
        _audit_admin_action(
            request,
            action=AuditLog.Action.EXECUTE,
            model_name='CauHinhLuong',
            note='Export CSV cấu hình lương từ Django Admin.',
            changes={'exported_count': queryset.count(), 'filters': request.GET.dict()},
        )
        return response

    def save_model(self, request, obj, form, change):
        before = None
        if change and obj.pk:
            before = CauHinhLuong.objects.filter(pk=obj.pk).values(
                'luong_co_ban_ngay', 'phu_cap_trach_nhiem', 'phu_cap_xang_xe', 'phu_cap_an_uong'
            ).first()
        super().save_model(request, obj, form, change)
        after = {
            'luong_co_ban_ngay': str(obj.luong_co_ban_ngay or 0),
            'phu_cap_trach_nhiem': str(obj.phu_cap_trach_nhiem or 0),
            'phu_cap_xang_xe': str(obj.phu_cap_xang_xe or 0),
            'phu_cap_an_uong': str(obj.phu_cap_an_uong or 0),
        }
        _audit_admin_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name='CauHinhLuong',
            object_id=obj.pk,
            note='Tạo/cập nhật cấu hình lương qua Django Admin.',
            changes={'before': before or {}, 'after': after},
        )

    def delete_model(self, request, obj):
        snapshot = {
            'nhan_vien': str(obj.nhan_vien),
            'luong_co_ban_ngay': str(obj.luong_co_ban_ngay or 0),
            'phu_cap_trach_nhiem': str(obj.phu_cap_trach_nhiem or 0),
            'phu_cap_xang_xe': str(obj.phu_cap_xang_xe or 0),
            'phu_cap_an_uong': str(obj.phu_cap_an_uong or 0),
        }
        pk = obj.pk
        super().delete_model(request, obj)
        _audit_admin_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name='CauHinhLuong',
            object_id=pk,
            note='Xóa cấu hình lương qua Django Admin.',
            changes={'deleted': snapshot},
        )

    def delete_queryset(self, request, queryset):
        snapshots = list(queryset.select_related('nhan_vien').values_list('pk', 'nhan_vien__ma_nhan_vien', 'nhan_vien__ho_ten'))
        super().delete_queryset(request, queryset)
        _audit_admin_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name='CauHinhLuong',
            note='Xóa hàng loạt cấu hình lương qua Django Admin.',
            changes={'deleted_items': [{'id': pk, 'ma_nhan_vien': code, 'ho_ten': name} for pk, code, name in snapshots]},
        )

    def _tong_phu_cap(self, obj):
        return (obj.phu_cap_trach_nhiem or 0) + (obj.phu_cap_xang_xe or 0) + (obj.phu_cap_an_uong or 0)

    @admin.display(description=_('Nhân viên'), ordering='nhan_vien__ho_ten')
    def nhan_vien_hien_thi(self, obj):
        phong_ban = getattr(getattr(obj.nhan_vien, 'phong_ban', None), 'ten_phong_ban', '')
        return format_html(
            '<b>{}</b><br><small style="color:#64748b;">{} {}</small>',
            obj.nhan_vien.ho_ten,
            obj.nhan_vien.ma_nhan_vien,
            f'· {phong_ban}' if phong_ban else '',
        )

    @admin.display(description=_('Lương BHXH'), ordering='luong_co_ban_ngay')
    def luong_bhxh_vnd(self, obj):
        return format_html('<b style="color:#0f172a;">{}</b>', _format_vnd(obj.luong_co_ban_ngay))

    @admin.display(description=_('P.Cấp Trách Nhiệm'), ordering='phu_cap_trach_nhiem')
    def phu_cap_trach_nhiem_vnd(self, obj):
        return _format_vnd(obj.phu_cap_trach_nhiem)

    @admin.display(description=_('P.Cấp Xăng Xe'), ordering='phu_cap_xang_xe')
    def phu_cap_xang_xe_vnd(self, obj):
        return _format_vnd(obj.phu_cap_xang_xe)

    @admin.display(description=_('P.Cấp Ăn Uống'), ordering='phu_cap_an_uong')
    def phu_cap_an_uong_vnd(self, obj):
        return _format_vnd(obj.phu_cap_an_uong)

    @admin.display(description=_('Tổng phụ cấp'))
    def tong_phu_cap_vnd(self, obj):
        total = self._tong_phu_cap(obj)
        color = UI_COLORS['SUCCESS'] if total else '#64748b'
        return format_html('<b style="color:{};">{}</b>', color, _format_vnd(total))

    @admin.display(description=_('Tình trạng'))
    def trang_thai_cau_hinh(self, obj):
        if not obj.luong_co_ban_ngay:
            return format_html('<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#fee2e2;color:#b91c1c;font-weight:800;font-size:11px;">Thiếu lương BHXH</span>')
        if self._tong_phu_cap(obj) <= 0:
            return format_html('<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#fef3c7;color:#92400e;font-weight:800;font-size:11px;">Chưa có phụ cấp</span>')
        return format_html('<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#dcfce7;color:#047857;font-weight:800;font-size:11px;">Đã cấu hình</span>')

    @admin.display(description=_('Thao tác'))
    def hanh_dong_nhanh(self, obj):
        return format_html(
            '<a href="{}" class="button" style="background:#059669;color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:11px;font-weight:800;">Sửa</a>',
            f'{obj.pk}/change/',
        )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


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
<<<<<<< HEAD
    """Quản trị kỳ lương: đối soát, khóa kỳ, phát hành và truy xuất báo cáo."""
    change_list_template = 'accounting/admin/bangluongthang_change_list.html'
    list_display = [
        'ten_bang_luong',
        'ky_luong_badge',
        'so_phieu_luong',
        'tong_gio_cong_format',
        'hien_thi_tong_chi',
        'trang_thai_badge',
        'nut_xem_bao_cao',
        'nut_doi_soat',
    ]
    list_filter = ['nam', 'thang', 'trang_thai']
    search_fields = ['ten_bang_luong']
    readonly_fields = ['tenant_id', 'created_at', 'tong_chi_tra', 'tong_gio_cong']
    autocomplete_fields = ['nguoi_duyet']
    inlines = [ChiTietLuongInline]
    actions = ['tinh_luong_lai', 'phat_hanh_luong', 'audit_payroll_anomalies']
    list_per_page = 20
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Thông tin kỳ lương', {
            'fields': ('ten_bang_luong', ('thang', 'nam'), 'ngay_chot_cong', 'trang_thai', 'nguoi_duyet'),
        }),
        ('Số liệu đối soát', {
            'fields': ('tong_gio_cong', 'tong_chi_tra'),
            'classes': ('collapse',),
        }),
        ('Thông tin hệ thống', {
            'fields': ('tenant_id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('nguoi_duyet').annotate(
            so_phieu=Count('chi_tiet', distinct=True),
        )

    def changelist_view(self, request, extra_context: Optional[dict[str, Any]] = None):
        queryset = self.get_queryset(request)
        summary = queryset.aggregate(
            total_batches=Count('id'),
            total_pay=Sum('tong_chi_tra'),
            total_hours=Sum('tong_gio_cong'),
        )
        summary.update({
            'draft_count': queryset.filter(trang_thai=BangLuongThang.TrangThai.DRAFT).count(),
            'calculated_count': queryset.filter(trang_thai=BangLuongThang.TrangThai.CALCULATED).count(),
            'reviewed_count': queryset.filter(trang_thai=BangLuongThang.TrangThai.REVIEWED).count(),
            'locked_count': queryset.filter(trang_thai=BangLuongThang.TrangThai.LOCKED).count(),
            'paid_count': queryset.filter(trang_thai=BangLuongThang.TrangThai.PAID).count(),
        })
        extra_context = extra_context or {}
        extra_context['payroll_summary'] = summary
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description='Kỳ lương', ordering='nam')
    def ky_luong_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:999px;background:#eff6ff;color:#1d4ed8;font-weight:800;">{}/{}</span>',
            obj.thang,
            obj.nam,
        )

    @admin.display(description='Nhân sự', ordering='so_phieu')
    def so_phieu_luong(self, obj):
        return format_html('<b>{}</b> phiếu', getattr(obj, 'so_phieu', 0))

    @admin.display(description='Giờ công', ordering='tong_gio_cong')
    def tong_gio_cong_format(self, obj):
        return format_html('<b>{:,.1f}</b> giờ', obj.tong_gio_cong or 0)

    @admin.display(description=_('Tổng ngân sách chi'), ordering='tong_chi_tra')
    def hien_thi_tong_chi(self, obj):
        return format_html('<b style="color:#059669;">{}</b>', _format_vnd(obj.tong_chi_tra))

    @admin.display(description=_('Trạng thái'))
    def trang_thai_badge(self, obj):
        colors = {
            BangLuongThang.TrangThai.PAID: ('#065f46', '#d1fae5', 'Đã thanh toán'),
            BangLuongThang.TrangThai.LOCKED: ('#1e40af', '#dbeafe', 'Đã khóa kỳ'),
            BangLuongThang.TrangThai.REVIEWED: ('#92400e', '#fef3c7', 'Đã đối soát'),
            BangLuongThang.TrangThai.CALCULATED: ('#0369a1', '#e0f2fe', 'Đã tính'),
            BangLuongThang.TrangThai.DRAFT: ('#374151', '#f3f4f6', 'Dự thảo'),
        }
        text_color, bg_color, label = colors.get(obj.trang_thai, ('#374151', '#f3f4f6', obj.trang_thai))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;font-weight:800;font-size:11px;color:{};background:{};">{}</span>',
            text_color,
            bg_color,
            label,
        )

    @admin.display(description=_('Phiếu lương'))
    def nut_xem_bao_cao(self, obj):
        if obj.pk:
            url = f'/accounting/bang-luong/{obj.pk}/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background:#1d4ed8;color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:11px;font-weight:800;">Xem phiếu</a>',
                url,
            )
        return '-'

    @admin.display(description=_('Đối soát'))
    def nut_doi_soat(self, obj):
        if obj.pk:
            url = f'/accounting/doi-soat-khau-tru/{obj.pk}/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background:#059669;color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:11px;font-weight:800;">Đối soát</a>',
                url,
            )
        return '-'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_locked:
            readonly_fields.extend(['ten_bang_luong', 'thang', 'nam', 'ngay_chot_cong', 'trang_thai', 'nguoi_duyet'])
        return tuple(dict.fromkeys(readonly_fields))

    def tinh_luong_lai(self, request, queryset):
        """Thực thi tính toán lại số liệu lương định kỳ."""
        tenant_id = getattr(_current_employee(request), 'tenant_id', None)
        result = RecalculatePayrollBatchUseCase.execute(
            bang_luong_ids=queryset.values_list('id', flat=True),
            tenant_id=tenant_id,
        )
        for warning in result['warning_messages']:
            self.message_user(request, warning, messages.WARNING)
        for error in result['error_messages']:
            self.message_user(request, error, messages.ERROR)
        if result['updated_count'] > 0:
            self.message_user(request, f"Đã cập nhật lại {result['updated_count']} kỳ lương.", messages.SUCCESS)
    tinh_luong_lai.short_description = 'Tính toán lại kỳ lương đã chọn'

    def phat_hanh_luong(self, request, queryset):
        """Chốt sổ lương hàng tháng."""
        tenant_id = getattr(_current_employee(request), 'tenant_id', None)
        result = LockPayrollBatchUseCase.execute(
            bang_luong_ids=queryset.values_list('id', flat=True),
            tenant_id=tenant_id,
        )
        for error in result['error_messages']:
            self.message_user(request, error, messages.ERROR)
        if result['locked_count']:
            self.message_user(request, f"Đã khóa {result['locked_count']} kỳ lương và đồng bộ dữ liệu đối soát.", messages.SUCCESS)
    phat_hanh_luong.short_description = 'Khóa kỳ lương đã đối soát'

    def audit_payroll_anomalies(self, request, queryset):
        """Chạy kiểm toán nhanh để phát hiện bất thường lương trước khi khóa kỳ."""
        tenant_id = getattr(_current_employee(request), 'tenant_id', None)
        checked = 0
        warnings_count = 0
        for batch in queryset:
            result = AuditPayrollUseCase.execute(bang_luong=batch, tenant_id=tenant_id)
            checked += 1
            warnings_count += len(result.get('warnings', [])) if isinstance(result, dict) else 0
        self.message_user(
            request,
            f"Đã kiểm toán {checked} kỳ lương. Phát hiện {warnings_count} cảnh báo cần rà soát.",
            messages.WARNING if warnings_count else messages.SUCCESS,
        )
    audit_payroll_anomalies.short_description = 'Kiểm toán bất thường trước khi khóa kỳ'
=======
    """Quản trị bảng lương tổng hợp hàng tháng của SCMD"""
    list_display = [
        'ten_bang_luong', 
        'thang', 
        'nam', 
        'hien_thi_tong_chi', 
        'trang_thai_badge', 
        'nut_xem_bao_cao',
        'nut_doi_soat'
    ]
    list_filter = ['nam', 'trang_thai', 'thang']
    search_fields = ['ten_bang_luong']
    inlines = [ChiTietLuongInline]
    actions = ['tinh_luong_lai', 'phat_hanh_luong', 'audit_payroll_anomalies']
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

    @admin.display(description=_("Đối soát Quỹ"))
    def nut_doi_soat(self, obj):
        """Nút truy cập báo cáo đối soát khấu trừ"""
        if obj.pk:
            url = f"/accounting/doi-soat-khau-tru/{obj.pk}/"
            return format_html(
                '<a href="{}" target="_blank" class="button" '
                'style="background:#059669; color:white; padding:4px 12px; border-radius:4px; '
                'text-decoration:none; font-size:11px; font-weight:bold;">📊 ĐỐI SOÁT</a>', 
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
            count = 0
            for bl in queryset.filter(trang_thai__in=['NHAP', 'CHO_DUYET']):
                with transaction.atomic():
                    bl.trang_thai = 'DA_PHAT_HANH'
                    bl.save()
                    PayrollService.lock_related_records(bl)
                    count += 1
            self.message_user(request, f"Xác nhận: Đã khóa sổ {count} bảng lương và đồng bộ dữ liệu SSOT.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Lỗi khi thực hiện khóa sổ: {str(e)}", messages.ERROR)

    phat_hanh_luong.short_description = "✅ CHỐT SỔ & PHÁT HÀNH (KHÔNG SỬA)"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 4. CHI TIẾT LƯƠNG CÁ NHÂN
# ==============================================================================
@admin.register(ChiTietLuong)
class ChiTietLuongAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    """Quản lý phiếu lương cá nhân: xem, đối soát, xuất dữ liệu và chặn sửa kỳ đã khóa."""
    change_list_template = 'accounting/admin/chitietluong_change_list.html'
    LOCKED_READONLY_FIELDS = [
        "bang_luong",
        "nhan_vien",
        "tenant_id",
        "tong_gio_lam",
        "so_ngay_nghi",
        "luong_chinh",
        "thuong_chuyen_can",
        "phu_cap_khac",
        "ung_luong",
        "phat_vi_pham",
        "tien_dong_phuc",
        "tien_den_bu",
        "bao_hiem",
        "phi_cong_doan",
        "thuc_lanh",
        "ghi_chu",
        "nguon_du_lieu_snapshot",
        "reconciliation_note",
    ]
    list_display = [
        'nhan_vien_hien_thi',
        'ky_luong_badge',
        'tong_gio_lam_format',
        'tong_thu_nhap_format',
        'tong_khau_tru_format',
        'thuc_lanh_format',
        'trang_thai_ky_badge',
        'hanh_dong_nhanh',
    ]
    list_filter = [
        PayrollDetailOperationalFilter,
        'bang_luong__trang_thai',
        'bang_luong__nam',
        'bang_luong__thang',
        'nhan_vien__phong_ban',
    ]
    search_fields = [
        'nhan_vien__ho_ten',
        'nhan_vien__ma_nhan_vien',
        'bang_luong__ten_bang_luong',
        'ghi_chu',
        'reconciliation_note',
    ]
    autocomplete_fields = ['bang_luong', 'nhan_vien']
    readonly_fields = ['tenant_id', 'thuc_lanh']
    date_hierarchy = 'bang_luong__created_at'
    list_per_page = 25
    save_on_top = True
    ordering = ['-bang_luong__nam', '-bang_luong__thang', 'nhan_vien__ho_ten']

    fieldsets = (
        ('Kỳ lương và nhân sự', {
            'fields': ('bang_luong', 'nhan_vien'),
            'description': 'Phiếu lương cá nhân là dữ liệu đối soát. Nếu kỳ lương đã LOCKED/PAID, hệ thống chỉ cho đọc và phải xử lý bằng adjustment/reconciliation thay vì sửa trực tiếp.',
        }),
        ('Dữ liệu công và thu nhập', {
            'fields': (
                ('tong_gio_lam', 'so_ngay_nghi'),
                ('luong_chinh', 'thuong_chuyen_can', 'phu_cap_khac'),
            ),
        }),
        ('Khấu trừ và nghĩa vụ', {
            'fields': (
                ('ung_luong', 'phat_vi_pham'),
                ('tien_dong_phuc', 'tien_den_bu'),
                ('bao_hiem', 'phi_cong_doan'),
            ),
            'description': 'Các khoản khấu trừ liên quan vi phạm, đồng phục, đền bù và bảo hiểm phải trace được sang dữ liệu nguồn khi đối soát.',
        }),
        ('Kết quả và đối soát', {
            'fields': ('thuc_lanh', 'ghi_chu', 'reconciliation_note', 'nguon_du_lieu_snapshot'),
        }),
        ('Thông tin hệ thống', {
            'fields': ('tenant_id',),
            'classes': ('collapse',),
        }),
    )

    def get_urls(self):
        custom_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv), name='accounting_chitietluong_export_csv'),
        ]
        return custom_urls + super().get_urls()

    def get_queryset(self, request):
        """Tối ưu hóa query tránh N+1 cho nhân viên, phòng ban và kỳ lương."""
        scoped_staff_ids = StaffVisibilityPolicy.visible_staff(request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(nhan_vien_id__in=scoped_staff_ids).select_related(
            'nhan_vien',
            'nhan_vien__phong_ban',
            'bang_luong',
        )

    def changelist_view(self, request, extra_context: Optional[dict[str, Any]] = None):
        queryset = self.get_queryset(request)
        locked_states = [BangLuongThang.TrangThai.LOCKED, BangLuongThang.TrangThai.PAID]
        summary = queryset.aggregate(
            total_payslips=Count('id'),
            total_hours=Sum('tong_gio_lam'),
            total_salary=Sum('luong_chinh'),
            total_bonus=Sum('thuong_chuyen_can'),
            total_allowance=Sum('phu_cap_khac'),
            total_net=Sum('thuc_lanh'),
            total_violations=Sum('phat_vi_pham'),
            total_advances=Sum('ung_luong'),
            total_uniform=Sum('tien_dong_phuc'),
            total_compensation=Sum('tien_den_bu'),
        )
        summary['total_gross'] = (summary.get('total_salary') or 0) + (summary.get('total_bonus') or 0) + (summary.get('total_allowance') or 0)
        summary.update({
            'locked_count': queryset.filter(bang_luong__trang_thai__in=locked_states).count(),
            'editable_count': queryset.exclude(bang_luong__trang_thai__in=locked_states).count(),
            'has_violation_count': queryset.filter(phat_vi_pham__gt=0).count(),
            'has_advance_count': queryset.filter(ung_luong__gt=0).count(),
            'non_positive_net_count': queryset.filter(thuc_lanh__lte=0).count(),
            'missing_snapshot_count': queryset.filter(
                Q(nguon_du_lieu_snapshot__isnull=True) | Q(nguon_du_lieu_snapshot={})
            ).count(),
            'missing_reconciliation_count': queryset.filter(
                Q(reconciliation_note__isnull=True) | Q(reconciliation_note__exact="")
            ).count(),
        })
        query_string = request.GET.urlencode()
        extra_context = extra_context or {}
        extra_context.update({
            'payroll_detail_summary': summary,
            'export_csv_url': f'export-csv/?{query_string}' if query_string else 'export-csv/',
        })
        return super().changelist_view(request, extra_context=extra_context)

    def _filtered_queryset_for_export(self, request):
        request.GET = request.GET.copy()
        request.GET.pop('all', None)
        request.GET.pop('o', None)
        request.GET.pop('p', None)
        return self.get_changelist_instance(request).queryset

    def export_csv(self, request):
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        queryset = self._filtered_queryset_for_export(request)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="scmdpro-chi-tiet-luong.csv"'
        response.write('﻿')
        writer = csv.writer(response)
        writer.writerow([
            'Kỳ lương',
            'Tháng',
            'Năm',
            'Trạng thái kỳ',
            'Mã nhân viên',
            'Họ tên',
            'Phòng ban',
            'Tổng giờ làm',
            'Số ngày nghỉ',
            'Lương chính',
            'Thưởng chuyên cần',
            'Phụ cấp khác',
            'Tạm ứng',
            'Phạt vi phạm',
            'Đồng phục',
            'Đền bù',
            'Bảo hiểm',
            'Phí công đoàn',
            'Thực lĩnh',
            'Ghi chú',
            'Ghi chú đối soát',
        ])
        for obj in queryset:
            employee = obj.nhan_vien
            payroll = obj.bang_luong
            writer.writerow([
                getattr(payroll, 'ten_bang_luong', ''),
                getattr(payroll, 'thang', ''),
                getattr(payroll, 'nam', ''),
                getattr(payroll, 'trang_thai', ''),
                getattr(employee, 'ma_nhan_vien', ''),
                getattr(employee, 'ho_ten', ''),
                getattr(getattr(employee, 'phong_ban', None), 'ten_phong_ban', ''),
                obj.tong_gio_lam or 0,
                obj.so_ngay_nghi or 0,
                obj.luong_chinh or 0,
                obj.thuong_chuyen_can or 0,
                obj.phu_cap_khac or 0,
                obj.ung_luong or 0,
                obj.phat_vi_pham or 0,
                obj.tien_dong_phuc or 0,
                obj.tien_den_bu or 0,
                obj.bao_hiem or 0,
                obj.phi_cong_doan or 0,
                obj.thuc_lanh or 0,
                obj.ghi_chu or '',
                obj.reconciliation_note or '',
            ])
        _audit_admin_action(
            request,
            action=AuditLog.Action.EXECUTE,
            model_name='ChiTietLuong',
            note='Export CSV phiếu lương cá nhân từ Django Admin.',
            changes={'exported_count': queryset.count(), 'filters': request.GET.dict()},
        )
        return response

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.bang_luong and obj.bang_luong.is_locked:
            readonly_fields.extend(self.LOCKED_READONLY_FIELDS)
        return tuple(dict.fromkeys(readonly_fields))

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        if obj.bang_luong and obj.bang_luong.is_locked:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        base_permission = super().has_delete_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return not obj.bang_luong.is_locked

    def save_model(self, request, obj, form, change):
        if obj.bang_luong and obj.bang_luong.is_locked:
            raise ValidationError(
                "Kỳ lương đã LOCKED/PAID. Không được sửa trực tiếp phiếu lương cá nhân qua admin."
            )
        before = None
        if change and obj.pk:
            before = ChiTietLuong.objects.filter(pk=obj.pk).values(
                'tong_gio_lam',
                'so_ngay_nghi',
                'luong_chinh',
                'thuong_chuyen_can',
                'phu_cap_khac',
                'ung_luong',
                'phat_vi_pham',
                'tien_dong_phuc',
                'tien_den_bu',
                'bao_hiem',
                'phi_cong_doan',
                'thuc_lanh',
                'reconciliation_note',
            ).first()
        super().save_model(request, obj, form, change)
        after = ChiTietLuong.objects.filter(pk=obj.pk).values(
            'tong_gio_lam',
            'so_ngay_nghi',
            'luong_chinh',
            'thuong_chuyen_can',
            'phu_cap_khac',
            'ung_luong',
            'phat_vi_pham',
            'tien_dong_phuc',
            'tien_den_bu',
            'bao_hiem',
            'phi_cong_doan',
            'thuc_lanh',
            'reconciliation_note',
        ).first()
        _audit_admin_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name='ChiTietLuong',
            object_id=obj.pk,
            note='Tạo/cập nhật phiếu lương cá nhân qua Django Admin.',
            changes={'before': before, 'after': after},
        )

    def delete_model(self, request, obj):
        if obj.bang_luong and obj.bang_luong.is_locked:
            raise ValidationError("Không được xóa phiếu lương thuộc kỳ đã khóa.")
        object_id = obj.pk
        snapshot = {
            'nhan_vien': str(obj.nhan_vien),
            'bang_luong': str(obj.bang_luong),
            'thuc_lanh': str(obj.thuc_lanh),
        }
        super().delete_model(request, obj)
        _audit_admin_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name='ChiTietLuong',
            object_id=object_id,
            note='Xóa phiếu lương cá nhân qua Django Admin.',
            changes=snapshot,
        )

    def delete_queryset(self, request, queryset):
        locked_count = queryset.filter(
            bang_luong__trang_thai__in=[BangLuongThang.TrangThai.LOCKED, BangLuongThang.TrangThai.PAID]
        ).count()
        if locked_count:
            raise ValidationError("Không được xóa hàng loạt phiếu lương thuộc kỳ đã khóa/đã thanh toán.")
        ids = list(queryset.values_list('id', flat=True))
        count = queryset.count()
        super().delete_queryset(request, queryset)
        _audit_admin_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name='ChiTietLuong',
            note='Xóa hàng loạt phiếu lương cá nhân qua Django Admin.',
            changes={'deleted_count': count, 'ids': ids[:200]},
        )

    @admin.display(description='Nhân sự', ordering='nhan_vien__ho_ten')
    def nhan_vien_hien_thi(self, obj):
        employee = obj.nhan_vien
        code = getattr(employee, 'ma_nhan_vien', '') or 'Chưa có mã'
        department = getattr(getattr(employee, 'phong_ban', None), 'ten_phong_ban', '') or 'Chưa rõ phòng ban'
        return format_html(
            '<div style="font-weight:900;color:#0f172a;">{}</div><div style="font-size:11px;color:#64748b;">{} · {}</div>',
            getattr(employee, 'ho_ten', employee),
            code,
            department,
        )

    @admin.display(description='Kỳ lương', ordering='bang_luong__nam')
    def ky_luong_badge(self, obj):
        payroll = obj.bang_luong
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:999px;background:#eff6ff;color:#1d4ed8;font-weight:800;">{}/{}</span>',
            payroll.thang,
            payroll.nam,
        )

    @admin.display(description='Trạng thái kỳ', ordering='bang_luong__trang_thai')
    def trang_thai_ky_badge(self, obj):
        colors = {
            BangLuongThang.TrangThai.PAID: ('#065f46', '#d1fae5', 'Đã thanh toán'),
            BangLuongThang.TrangThai.LOCKED: ('#1e40af', '#dbeafe', 'Đã khóa kỳ'),
            BangLuongThang.TrangThai.REVIEWED: ('#92400e', '#fef3c7', 'Đã đối soát'),
            BangLuongThang.TrangThai.CALCULATED: ('#0369a1', '#e0f2fe', 'Đã tính'),
            BangLuongThang.TrangThai.DRAFT: ('#374151', '#f3f4f6', 'Dự thảo'),
        }
        text_color, bg_color, label = colors.get(obj.bang_luong.trang_thai, ('#374151', '#f3f4f6', obj.bang_luong.trang_thai))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;font-weight:800;font-size:11px;color:{};background:{};">{}</span>',
            text_color,
            bg_color,
            label,
        )

    @admin.display(description=_('Công làm việc'), ordering='tong_gio_lam')
    def tong_gio_lam_format(self, obj):
        val = obj.tong_gio_lam or 0
        return format_html('<b>{:,.1f}</b> giờ', val)

    @admin.display(description='Tổng thu nhập')
    def tong_thu_nhap_format(self, obj):
        return format_html('<b style="color:#059669;">{}</b>', _format_vnd(obj.tong_thu_nhap))

    @admin.display(description='Tổng khấu trừ')
    def tong_khau_tru_format(self, obj):
        value = obj.tong_khau_tru
        color = '#dc2626' if value else '#64748b'
        return format_html('<b style="color:{};">{}</b>', color, _format_vnd(value))

    @admin.display(description=_('Thực lĩnh'), ordering='thuc_lanh')
    def thuc_lanh_format(self, obj):
        color = UI_COLORS['SUCCESS'] if (obj.thuc_lanh or 0) > 0 else UI_COLORS['DANGER']
        return format_html('<b style="color:{};">{}</b>', color, _format_vnd(obj.thuc_lanh))

    @admin.display(description='Thao tác')
    def hanh_dong_nhanh(self, obj):
        change_url = f'{obj.pk}/change/'
        report_url = f'/accounting/bang-luong/{obj.bang_luong_id}/'
        batch_url = f'../bangluongthang/{obj.bang_luong_id}/change/'
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a href="{}" class="button" style="padding:5px 8px;border-radius:8px;font-size:11px;font-weight:800;">Sửa</a>'
            '<a href="{}" target="_blank" class="button" style="padding:5px 8px;border-radius:8px;font-size:11px;font-weight:800;background:#1d4ed8;color:#fff;">Phiếu</a>'
            '<a href="{}" class="button" style="padding:5px 8px;border-radius:8px;font-size:11px;font-weight:800;background:#059669;color:#fff;">Kỳ</a>'
            '</div>',
            change_url,
            report_url,
            batch_url,
        )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 5. QUẢN LÝ SỔ QUỸ (CASHFLOW)
# ==============================================================================
@admin.register(SoQuy)
class SoQuyAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    """Quản lý sổ quỹ tiền mặt/ngân hàng: lập phiếu, duyệt phiếu và đối soát dòng tiền."""
    change_list_template = 'accounting/admin/soquy_change_list.html'
    list_display = [
        'ma_phieu',
        'loai_phieu_badge',
        'hang_muc_badge',
        'doi_tuong_giao_dich',
        'so_tien_vnd',
        'ngay_lap_format',
        'trang_thai_badge',
        'nguoi_lap',
        'nguoi_duyet',
    ]
    list_filter = ['trang_thai', 'loai_phieu', 'hang_muc', ('ngay_lap', admin.DateFieldListFilter)]
    search_fields = [
        'ma_phieu',
        'dien_giai',
        'nhan_vien__ho_ten',
        'nhan_vien__ma_nhan_vien',
        'hop_dong__so_hop_dong',
        'hop_dong__khach_hang_cu__ten_cong_ty',
    ]
    autocomplete_fields = ['nhan_vien', 'hop_dong', 'nguoi_lap', 'nguoi_duyet']
    date_hierarchy = 'ngay_lap'
    ordering = ['-ngay_lap', '-ma_phieu']
    list_per_page = 25
    actions = ['chuyen_cho_duyet', 'duyet_phieu', 'tu_choi_phieu']
    readonly_fields = ['nguoi_duyet']

    fieldsets = (
        ('Thông tin chứng từ', {
            'fields': ('ma_phieu', ('loai_phieu', 'hang_muc'), 'so_tien', 'ngay_lap', 'trang_thai'),
        }),
        ('Đối tượng liên quan', {
            'fields': ('nhan_vien', 'hop_dong'),
            'description': 'Chọn nhân viên nếu là tạm ứng/lương; chọn hợp đồng nếu là thu phí dịch vụ khách hàng.',
        }),
        ('Nội dung và chứng từ', {
            'fields': ('dien_giai', 'chung_tu_goc'),
        }),
        ('Luồng phê duyệt', {
            'fields': ('nguoi_lap', 'nguoi_duyet'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'nhan_vien',
            'nhan_vien__phong_ban',
            'hop_dong',
            'hop_dong__khach_hang_cu',
            'nguoi_lap',
            'nguoi_duyet',
        )

    def changelist_view(self, request, extra_context: Optional[dict[str, Any]] = None):
        queryset = self.get_queryset(request)
        thu = queryset.filter(loai_phieu='THU', trang_thai='DA_DUYET').aggregate(total=Sum('so_tien'))['total'] or 0
        chi = queryset.filter(loai_phieu='CHI', trang_thai='DA_DUYET').aggregate(total=Sum('so_tien'))['total'] or 0
        pending_amount = queryset.filter(trang_thai='CHO_DUYET').aggregate(total=Sum('so_tien'))['total'] or 0
        summary = {
            'total_count': queryset.count(),
            'pending_count': queryset.filter(trang_thai='CHO_DUYET').count(),
            'draft_count': queryset.filter(trang_thai='NHAP').count(),
            'approved_count': queryset.filter(trang_thai='DA_DUYET').count(),
            'rejected_count': queryset.filter(trang_thai='TU_CHOI').count(),
            'thu': thu,
            'chi': chi,
            'balance': thu - chi,
            'pending_amount': pending_amount,
        }
        extra_context = extra_context or {}
        extra_context['cashbook_summary'] = summary
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if not obj.nguoi_lap:
            obj.nguoi_lap = _current_employee(request)
        if obj.trang_thai == 'DA_DUYET' and not obj.nguoi_duyet:
            obj.nguoi_duyet = _current_employee(request)
        super().save_model(request, obj, form, change)

    @admin.display(description=_('Loại'), ordering='loai_phieu')
    def loai_phieu_badge(self, obj):
        if obj.loai_phieu == 'THU':
            return format_html('<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#dcfce7;color:#047857;font-weight:800;">Thu</span>')
        return format_html('<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#fee2e2;color:#b91c1c;font-weight:800;">Chi</span>')

    @admin.display(description=_('Hạng mục'), ordering='hang_muc')
    def hang_muc_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:#f8fafc;color:#334155;border:1px solid #e2e8f0;font-weight:700;">{}</span>',
            obj.get_hang_muc_display(),
        )

    @admin.display(description=_('Đối tượng'))
    def doi_tuong_giao_dich(self, obj):
        if obj.nhan_vien:
            return format_html('<b>{}</b><br><small style="color:#64748b;">{}</small>', obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien)
        if obj.hop_dong:
            return format_html('<b>{}</b><br><small style="color:#64748b;">Hợp đồng khách hàng</small>', obj.hop_dong.so_hop_dong)
        return format_html('<span style="color:#94a3b8;">Chưa gắn đối tượng</span>')

    @admin.display(description=_('Số tiền'), ordering='so_tien')
    def so_tien_vnd(self, obj):
        is_chi = obj.loai_phieu == 'CHI'
        color = UI_COLORS['DANGER'] if is_chi else UI_COLORS['SUCCESS']
        prefix = '-' if is_chi else '+'
        return format_html('<span style="color:{}; font-weight:900;">{}{}</span>', color, prefix, _format_vnd(obj.so_tien))

    @admin.display(description=_('Ngày lập'), ordering='ngay_lap')
    def ngay_lap_format(self, obj):
        if not obj.ngay_lap:
            return '-'
        return obj.ngay_lap.strftime('%d/%m/%Y %H:%M')

    @admin.display(description=_('Trạng thái'), ordering='trang_thai')
    def trang_thai_badge(self, obj):
        status_colors = {
            'NHAP': ('#334155', '#f1f5f9'),
            'CHO_DUYET': ('#92400e', '#fef3c7'),
            'DA_DUYET': ('#047857', '#dcfce7'),
            'TU_CHOI': ('#b91c1c', '#fee2e2'),
        }
        text_color, bg_color = status_colors.get(obj.trang_thai, ('#334155', '#f1f5f9'))
        return format_html(
            '<span style="display:inline-flex;padding:5px 9px;border-radius:999px;font-weight:800;font-size:11px;color:{};background:{};">{}</span>',
            text_color,
            bg_color,
            obj.get_trang_thai_display(),
        )

    def chuyen_cho_duyet(self, request, queryset):
        updated = _apply_accounting_status_action(request, queryset, model_name='SoQuy', target_status='CHO_DUYET', filter_status='NHAP', note='Admin cashbook submit for approval')
        self.message_user(request, f'Đã chuyển {updated} phiếu sang trạng thái chờ duyệt.', messages.SUCCESS)
    chuyen_cho_duyet.short_description = 'Chuyển phiếu nháp sang chờ duyệt'

    def duyet_phieu(self, request, queryset):
        employee = _current_employee(request)
        updated = _apply_accounting_status_action(request, queryset, model_name='SoQuy', target_status='DA_DUYET', filter_status='CHO_DUYET', note='Admin cashbook approved', update_extra={'nguoi_duyet': employee})
        self.message_user(request, f'Đã duyệt {updated} phiếu thu/chi.', messages.SUCCESS)
    duyet_phieu.short_description = 'Duyệt phiếu thu/chi đã chọn'

    def tu_choi_phieu(self, request, queryset):
        updated = _apply_accounting_status_action(request, queryset, model_name='SoQuy', target_status='TU_CHOI', filter_status='CHO_DUYET', note='Admin cashbook rejected')
        self.message_user(request, f'Đã từ chối {updated} phiếu thu/chi.', messages.WARNING)
    tu_choi_phieu.short_description = 'Từ chối phiếu thu/chi đã chọn'



@admin.register(TamUngLuong)
class TamUngLuongAdmin(admin.ModelAdmin):
    list_display = ("so_phieu", "nhan_vien", "ngay_de_nghi", "so_tien_display", "trang_thai", "bang_luong_du_kien")
    list_filter = ("trang_thai", ("ngay_de_nghi", admin.DateFieldListFilter), "bang_luong_du_kien")
    search_fields = ("so_phieu", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "ly_do")
    autocomplete_fields = ("nhan_vien", "bang_luong_du_kien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "bang_luong_du_kien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = TamUngLuong.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == TamUngLuong.TrangThai.APPROVED and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin payroll advance status save")

    @admin.display(description="Số tiền", ordering="so_tien")
    def so_tien_display(self, obj):
        return _format_vnd(obj.so_tien)


@admin.register(KhoanKhauTruNhanVien)
class KhoanKhauTruNhanVienAdmin(admin.ModelAdmin):
    list_display = ("so_chung_tu", "nhan_vien", "loai_khau_tru", "ngay_ap_dung", "so_tien_display", "trang_thai", "bang_luong_du_kien")
    list_filter = ("trang_thai", "loai_khau_tru", ("ngay_ap_dung", admin.DateFieldListFilter), "bang_luong_du_kien")
    search_fields = ("so_chung_tu", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "ly_do", "tam_ung__so_phieu")
    autocomplete_fields = ("nhan_vien", "tam_ung", "bang_luong_du_kien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "tam_ung", "bang_luong_du_kien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = KhoanKhauTruNhanVien.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == KhoanKhauTruNhanVien.TrangThai.APPROVED and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin employee deduction status save")

    @admin.display(description="Số tiền", ordering="so_tien")
    def so_tien_display(self, obj):
        return _format_vnd(obj.so_tien)


@admin.register(PayrollAdjustment)
class PayrollAdjustmentAdmin(admin.ModelAdmin):
    """Append-only admin surface for retroactive payroll adjustments."""

    list_display = [
        "bang_luong",
        "nhan_vien",
        "so_tien_badge",
        "created_by",
        "created_at",
    ]
    list_filter = ["bang_luong__trang_thai", "created_at"]
    search_fields = [
        "nhan_vien__ho_ten",
        "nhan_vien__ma_nhan_vien",
        "ly_do",
        "bang_luong__ten_bang_luong",
    ]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["bang_luong", "chi_tiet_luong", "nhan_vien"]
    raw_id_fields = ["created_by"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Thông tin điều chỉnh", {
            "fields": (
                "bang_luong",
                "chi_tiet_luong",
                "nhan_vien",
                "so_tien_dieu_chinh",
                "ly_do",
                "metadata",
            )
        }),
        ("Audit", {"fields": ("created_by", "created_at")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly_fields.extend([
                "bang_luong",
                "chi_tiet_luong",
                "nhan_vien",
                "so_tien_dieu_chinh",
                "ly_do",
                "metadata",
                "created_by",
            ])
        return tuple(dict.fromkeys(readonly_fields))

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            raise ValidationError("PayrollAdjustment là append-only. Không được sửa điều chỉnh đã tạo.")
        if obj.created_by_id is None and getattr(request, "user", None) and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        _audit_admin_action(
            request,
            action=AuditLog.Action.CREATE,
            model_name="PayrollAdjustment",
            object_id=obj.pk,
            note=obj.ly_do,
            changes={
                "bang_luong_id": obj.bang_luong_id,
                "chi_tiet_luong_id": obj.chi_tiet_luong_id,
                "nhan_vien_id": obj.nhan_vien_id,
                "so_tien_dieu_chinh": str(obj.so_tien_dieu_chinh),
            },
        )

    @admin.display(description="Số tiền", ordering="so_tien_dieu_chinh")
    def so_tien_badge(self, obj):
        color = UI_COLORS["SUCCESS"] if obj.so_tien_dieu_chinh > 0 else UI_COLORS["DANGER"]
        sign = "+" if obj.so_tien_dieu_chinh > 0 else ""
        return format_html(
            '<span style="font-weight:900;color:{};white-space:nowrap;">{}{}</span>',
            color,
            sign,
            _format_vnd(obj.so_tien_dieu_chinh),
        )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
