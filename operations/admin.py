# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/admin.py
Author: Mr. Anh (CTO)
Created Date: 2025-12-06
Description: Cấu hình Admin Vận hành (Operations).
             LAYOUT: Dạng List (Dọc) cho Form nhập liệu.
             UPGRADE: Tối ưu hóa QuerySet & Nâng cấp UI Badge.
"""

from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, F, Q
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from core.workflow_transition_policy import WorkflowTransitionPolicy
from main.models import AuditLog
from main.audit_utils import record_admin_audit_action
from operations.application.attendance_correction_use_cases import CorrectAttendanceUseCase
from operations.application.incident_transition_policy import IncidentTransitionPolicy
from operations.application.shift_change_permission_policy import ShiftChangePermissionPolicy
from clients.access_policies import SiteVisibilityPolicy
from operations.access_policies import (
    AliveCheckVisibilityPolicy,
    AttendanceVisibilityPolicy,
    IncidentVisibilityPolicy,
    PostVisibilityPolicy,
    ProposalVisibilityPolicy,
    ShiftAssignmentPolicy,
    ShiftVisibilityPolicy,
)
from users.access_policies import StaffVisibilityPolicy
from .models import (
    ViTriChot, CaLamViec, PhanCongCaTruc, LichTuanTraVanHanh, NhiemVuTuanTraCa,
    ShiftChangeRequest, ChamCong, ChamCongAdjustment, BaoCaoSuCo, BaoCaoDeXuat, KiemTraQuanSo
)

# --- HELPER: MÀU SẮC TRẠNG THÁI CAO CẤP ---
STATUS_COLORS = {
    'CHUA_TRUC': '#64748b',      # Slate 500
    'DANG_TRUC': '#3b82f6',      # Blue 500
    'HOAN_THANH': '#10b981',     # Emerald 500
    'LOI': '#ef4444',            # Red 500
}


def _safe_reverse(viewname, *, args=None, kwargs=None, fallback='#'):
    """Reverse URL an toàn cho CTA admin/workspace.

    Admin pages phải không crash nếu một route workspace tạm thời chưa sẵn sàng.
    """
    try:
        return reverse(viewname, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return fallback


def _apply_admin_bulk_update(request, queryset, *, module, model_name, status_field, target_status, note, changes_extra=None, update_extra=None):
    """Per-object bulk update with save() and AuditLog; no queryset bulk update."""
    changed = 0
    update_extra = update_extra or {}
    with transaction.atomic():
        for obj in queryset.select_for_update().order_by("pk"):
            old_status = getattr(obj, status_field)
            if old_status == target_status:
                continue
            setattr(obj, status_field, target_status)
            update_fields = [status_field]
            for field_name, value in update_extra.items():
                setattr(obj, field_name, value)
                update_fields.append(field_name)
            obj.save(update_fields=update_fields)
            record_admin_audit_action(
                request,
                action=AuditLog.Action.UPDATE,
                module=module,
                model_name=model_name,
                object_id=obj.pk,
                note=note,
                changes={
                    status_field: {"old": old_status, "new": target_status},
                    **(changes_extra or {}),
                },
            )
            changed += 1
    return changed


def _admin_badge(label, tone='neutral'):
    palette = {
        'neutral': ('#f1f5f9', '#334155'),
        'info': ('#eff6ff', '#1d4ed8'),
        'success': ('#ecfdf5', '#047857'),
        'warning': ('#fffbeb', '#b45309'),
        'danger': ('#fff1f2', '#be123c'),
    }
    bg, color = palette.get(tone, palette['neutral'])
    return format_html(
        '<span style="display:inline-flex;align-items:center;padding:3px 8px;border-radius:999px;'
        'font-size:11px;font-weight:800;background:{};color:{};white-space:nowrap;">{}</span>',
        bg, color, label
    )

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



@admin.register(LichTuanTraVanHanh)
class LichTuanTraVanHanhAdmin(admin.ModelAdmin):
    list_display = (
        "schedule_scope",
        "tuyen_tuan_tra",
        "schedule_rules",
        "trang_thai",
        "updated_at",
    )
    list_filter = ("trang_thai", "muc_tieu", "vi_tri_chot", "ca_lam_viec", "yeu_cau_gps", "yeu_cau_anh")
    search_fields = (
        "muc_tieu__ten_muc_tieu",
        "vi_tri_chot__ten_vi_tri",
        "ca_lam_viec__ten_ca",
        "tuyen_tuan_tra__ten_loai",
    )
    autocomplete_fields = ("muc_tieu", "vi_tri_chot", "ca_lam_viec", "tuyen_tuan_tra")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Phạm vi lịch tuần tra", {"fields": ("muc_tieu", "vi_tri_chot", "ca_lam_viec", "tuyen_tuan_tra", "trang_thai")}),
        ("Quy tắc thực hiện", {"fields": ("tan_suat_luot_bat_buoc", ("khung_gio_bat_dau", "khung_gio_ket_thuc"), "grace_minutes", ("yeu_cau_gps", "yeu_cau_anh"))}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("muc_tieu", "vi_tri_chot", "ca_lam_viec", "tuyen_tuan_tra")

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        record_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="operations",
            model_name="LichTuanTraVanHanh",
            object_id=obj.pk,
            note="Cập nhật lịch tuần tra vận hành.",
            changes={
                "domain_owner": "operations.guard_patrol",
                "muc_tieu_id": obj.muc_tieu_id,
                "vi_tri_chot_id": obj.vi_tri_chot_id,
                "ca_lam_viec_id": obj.ca_lam_viec_id,
                "tuyen_tuan_tra_id": obj.tuyen_tuan_tra_id,
                "trang_thai": obj.trang_thai,
            },
        )

    @admin.display(description="Phạm vi")
    def schedule_scope(self, obj):
        post = obj.vi_tri_chot.ten_vi_tri if obj.vi_tri_chot_id else "Mọi chốt"
        shift = obj.ca_lam_viec.ten_ca if obj.ca_lam_viec_id else "Mọi ca"
        return format_html(
            '<div style="line-height:1.35;"><strong>{}</strong><div style="font-size:12px;color:#64748b;">{} · {}</div></div>',
            obj.muc_tieu.ten_muc_tieu if obj.muc_tieu_id else "Chưa rõ mục tiêu",
            post,
            shift,
        )

    @admin.display(description="Quy tắc")
    def schedule_rules(self, obj):
        flags = []
        flags.append(_admin_badge(f"{obj.tan_suat_luot_bat_buoc} lượt/ca", "info"))
        if obj.yeu_cau_gps:
            flags.append(_admin_badge("Bắt buộc GPS", "warning"))
        if obj.yeu_cau_anh:
            flags.append(_admin_badge("Bắt buộc ảnh", "warning"))
        return format_html_join(" ", "{}", ((flag,) for flag in flags))


@admin.register(NhiemVuTuanTraCa)
class NhiemVuTuanTraCaAdmin(admin.ModelAdmin):
    list_display = ("task_shift", "tuyen_tuan_tra", "progress_badge", "trang_thai", "grace_deadline")
    list_filter = ("trang_thai", "phan_cong_ca_truc__ngay_truc", "tuyen_tuan_tra", "lich_tuan_tra")
    search_fields = (
        "phan_cong_ca_truc__nhan_vien__ho_ten",
        "phan_cong_ca_truc__nhan_vien__ma_nhan_vien",
        "phan_cong_ca_truc__vi_tri_chot__ten_vi_tri",
        "phan_cong_ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu",
        "tuyen_tuan_tra__ten_loai",
    )
    autocomplete_fields = ("lich_tuan_tra", "phan_cong_ca_truc", "tuyen_tuan_tra", "luot_tuan_tra")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "lich_tuan_tra",
            "phan_cong_ca_truc",
            "phan_cong_ca_truc__nhan_vien",
            "phan_cong_ca_truc__vi_tri_chot",
            "phan_cong_ca_truc__vi_tri_chot__muc_tieu",
            "phan_cong_ca_truc__ca_lam_viec",
            "tuyen_tuan_tra",
            "luot_tuan_tra",
        )

    def has_add_permission(self, request):
        # Nhiệm vụ được sinh từ lịch + phân công ca để tránh nhập tay sai operational truth.
        return False

    @admin.display(description="Ca / nhân sự")
    def task_shift(self, obj):
        shift = obj.phan_cong_ca_truc
        return format_html(
            '<div style="line-height:1.35;"><strong>{}</strong><div style="font-size:12px;color:#64748b;">{} · {} · {}</div></div>',
            shift.nhan_vien.ho_ten if shift and shift.nhan_vien_id else "Chưa rõ nhân sự",
            shift.vi_tri_chot.ten_vi_tri if shift and shift.vi_tri_chot_id else "Chưa rõ chốt",
            shift.ca_lam_viec.ten_ca if shift and shift.ca_lam_viec_id else "Chưa rõ ca",
            shift.ngay_truc.strftime("%d/%m/%Y") if shift and shift.ngay_truc else "Chưa rõ ngày",
        )

    @admin.display(description="Tiến độ")
    def progress_badge(self, obj):
        tone = "success" if obj.trang_thai == NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID else "warning" if obj.so_diem_canh_bao else "info"
        return _admin_badge(f"{obj.so_diem_da_quet}/{obj.so_diem_bat_buoc} điểm · cảnh báo {obj.so_diem_canh_bao}", tone)

# --- 1. CẤU HÌNH VỊ TRÍ & CA TRỰC ---
class ViTriChotQualityFilter(admin.SimpleListFilter):
    title = _('Chất lượng chốt trực')
    parameter_name = 'post_quality'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Có ca hôm nay')),
            ('no_today', _('Chưa có ca hôm nay')),
            ('never', _('Chưa từng phân công')),
            ('missing_gps', _('Mục tiêu thiếu GPS')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == 'today':
            return queryset.filter(cac_phan_cong__ngay_truc=today).distinct()
        if self.value() == 'no_today':
            return queryset.exclude(cac_phan_cong__ngay_truc=today).distinct()
        if self.value() == 'never':
            return queryset.filter(cac_phan_cong__isnull=True).distinct()
        if self.value() == 'missing_gps':
            return queryset.filter(Q(muc_tieu__vi_do__isnull=True) | Q(muc_tieu__kinh_do__isnull=True)).distinct()
        return queryset


@admin.register(ViTriChot)
class ViTriChotAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/vitrichot/change_list.html'
    list_display = ('post_profile', 'target_profile', 'address_display', 'post_status')
    list_display_links = ('post_profile',)
    list_filter = (ViTriChotQualityFilter, 'muc_tieu')
    search_fields = ('ten_vi_tri', 'muc_tieu__ten_muc_tieu', 'muc_tieu__dia_chi')
    autocomplete_fields = ['muc_tieu']
    list_per_page = 50

    def get_queryset(self, request):
        today = timezone.localdate()
        scoped_ids = PostVisibilityPolicy.visible_posts(request.user).values_list("pk", flat=True)
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=scoped_ids)
            .select_related('muc_tieu')
            .annotate(
                assignments_total=Count('cac_phan_cong', distinct=True),
                assignments_today=Count(
                    'cac_phan_cong',
                    filter=Q(cac_phan_cong__ngay_truc=today),
                    distinct=True,
                ),
            )
        )

    @admin.display(description='Tên vị trí trực', ordering='ten_vi_tri')
    def post_profile(self, obj):
        return format_html(
            '<div class="scmd-admin-cell"><strong>{}</strong><span>Chốt trực tại mục tiêu</span></div>',
            obj.ten_vi_tri,
        )

    @admin.display(description='Mục tiêu', ordering='muc_tieu__ten_muc_tieu')
    def target_profile(self, obj):
        if not obj.muc_tieu:
            return _admin_badge('Chưa gán mục tiêu', 'warning')
        gps_ready = obj.muc_tieu.vi_do is not None and obj.muc_tieu.kinh_do is not None
        gps_badge = _admin_badge('Đủ GPS', 'success') if gps_ready else _admin_badge('Thiếu GPS', 'warning')
        return format_html(
            '<div class="scmd-admin-cell"><strong>{}</strong><span>{}</span></div>',
            obj.muc_tieu.ten_muc_tieu,
            gps_badge,
        )

    @admin.display(description='Địa chỉ')
    def address_display(self, obj):
        if not obj.muc_tieu or not obj.muc_tieu.dia_chi:
            return format_html('<span class="scmd-admin-muted">Chưa có địa chỉ</span>')
        return format_html('<span class="scmd-admin-muted">{}</span>', obj.muc_tieu.dia_chi)

    @admin.display(description='Tình trạng vận hành')
    def post_status(self, obj):
        today_count = getattr(obj, 'assignments_today', 0) or 0
        total_count = getattr(obj, 'assignments_total', 0) or 0
        if today_count:
            primary = _admin_badge(f'Hôm nay: {today_count}', 'success')
        else:
            primary = _admin_badge('Chưa có ca hôm nay', 'warning')
        if total_count:
            secondary = format_html('<span class="scmd-admin-muted">Tổng phân công: {}</span>', total_count)
        else:
            secondary = format_html('<span class="scmd-admin-muted">Chưa từng phân công</span>')
        return format_html('<div class="scmd-admin-cell">{}<span>{}</span></div>', primary, secondary)

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total=Count('pk', distinct=True),
            targets=Count('muc_tieu', distinct=True),
            today_scheduled=Count('pk', filter=Q(cac_phan_cong__ngay_truc=today), distinct=True),
            no_assignments=Count('pk', filter=Q(cac_phan_cong__isnull=True), distinct=True),
            missing_gps=Count(
                'pk',
                filter=Q(muc_tieu__vi_do__isnull=True) | Q(muc_tieu__kinh_do__isnull=True),
                distinct=True,
            ),
        )
        total = stats.get('total') or 0
        today_scheduled = stats.get('today_scheduled') or 0
        context = {
            'scmd_post_stats': {
                'total': total,
                'targets': stats.get('targets') or 0,
                'today_scheduled': today_scheduled,
                'no_today_schedule': max(total - today_scheduled, 0),
                'no_assignments': stats.get('no_assignments') or 0,
                'missing_gps': stats.get('missing_gps') or 0,
            },
            'scmd_post_links': {
                'add_post': _safe_reverse('admin:operations_vitrichot_add'),
                'target_list': _safe_reverse('admin:clients_muctieu_changelist'),
                'shift_list': _safe_reverse('admin:operations_phancongcatruc_changelist'),
                'schedule': _safe_reverse('operations:xep_lich'),
                'operations_dashboard': _safe_reverse('operations:dashboard_vanhanh'),
            },
            'scmd_today': today,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return PostVisibilityPolicy.visible_posts(request.user).filter(pk=obj.pk).exists()

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return PostVisibilityPolicy.visible_posts(request.user).filter(pk=obj.pk).exists()

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "muc_tieu":
            kwargs["queryset"] = SiteVisibilityPolicy.visible_sites(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CaLamViecQualityFilter(admin.SimpleListFilter):
    title = _('Chất lượng cấu hình ca')
    parameter_name = 'ca_quality'

    def lookups(self, request, model_admin):
        return (
            ('night', _('Ca đêm / vắt ngày')),
            ('day', _('Ca trong ngày')),
            ('today', _('Có phân công hôm nay')),
            ('no_today', _('Chưa có phân công hôm nay')),
            ('never', _('Chưa từng phân công')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == 'night':
            return queryset.filter(gio_ket_thuc__lt=F('gio_bat_dau'))
        if self.value() == 'day':
            return queryset.filter(gio_ket_thuc__gte=F('gio_bat_dau'))
        if self.value() == 'today':
            return queryset.filter(cac_phan_cong__ngay_truc=today).distinct()
        if self.value() == 'no_today':
            return queryset.exclude(cac_phan_cong__ngay_truc=today).distinct()
        if self.value() == 'never':
            return queryset.filter(cac_phan_cong__isnull=True)
        return queryset


@admin.register(CaLamViec)
class CaLamViecAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/calamviec/change_list.html'
    list_display = ('shift_profile', 'time_window_display', 'duration_display', 'usage_summary', 'row_actions')
    list_filter = (CaLamViecQualityFilter,)
    search_fields = ('ten_ca',)
    ordering = ('gio_bat_dau',)
    list_per_page = 50

    def get_queryset(self, request):
        today = timezone.localdate()
        return (
            super().get_queryset(request)
            .annotate(
                assignments_total=Count('cac_phan_cong', distinct=True),
                assignments_today=Count(
                    'cac_phan_cong',
                    filter=Q(cac_phan_cong__ngay_truc=today),
                    distinct=True,
                ),
            )
        )

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total=Count('id'),
            night_count=Count('id', filter=Q(gio_ket_thuc__lt=F('gio_bat_dau'))),
            assigned_today=Count('id', filter=Q(cac_phan_cong__ngay_truc=today), distinct=True),
            never_assigned=Count('id', filter=Q(cac_phan_cong__isnull=True)),
            total_assignments=Count('cac_phan_cong')
        )
        day_count = stats['total'] - stats['night_count']
        context = {
            'scmd_shift_stats': {
                'total': stats['total'],
                'day_count': day_count,
                'night_count': stats['night_count'],
                'assigned_today': stats['assigned_today'],
                'not_assigned_today': max(stats['total'] - stats['assigned_today'], 0),
                'never_assigned': stats['never_assigned'],
                'total_assignments': stats['total_assignments'],
            },
            'scmd_shift_links': {
                'add': _safe_reverse('admin:operations_calamviec_add'),
                'posts': _safe_reverse('admin:operations_vitrichot_changelist'),
                'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
                'add_assignment': _safe_reverse('admin:operations_phancongcatruc_add'),
                'schedule': _safe_reverse('operations:xep_lich'),
                'operations_dashboard': _safe_reverse('operations:dashboard_vanhanh'),
            },
            'scmd_today': today,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    @admin.display(description='Ca làm việc', ordering='ten_ca')
    def shift_profile(self, obj):
        tone = 'warning' if obj.is_night_shift else 'info'
        kind = 'Ca đêm' if obj.is_night_shift else 'Ca ngày'
        return format_html(
            '<div class="scmd-admin-cell scmd-shift-cell"><strong>{}</strong>'
            '<span><span class="scmd-admin-pill scmd-admin-pill-{}">{}</span></span></div>',
            obj.ten_ca,
            tone,
            kind,
        )
    
    @admin.display(description='Khung giờ', ordering='gio_bat_dau')
    def time_window_display(self, obj):
        return format_html(
            '<div class="scmd-admin-cell scmd-shift-cell"><strong>{} → {}</strong>'
            '<span>{}</span></div>',
            obj.gio_bat_dau.strftime('%H:%M') if obj.gio_bat_dau else '--:--',
            obj.gio_ket_thuc.strftime('%H:%M') if obj.gio_ket_thuc else '--:--',
            'Qua ngày hôm sau' if obj.is_night_shift else 'Trong cùng ngày',
        )
    
    @admin.display(description='Thời lượng')
    def duration_display(self, obj):
        if not obj.gio_bat_dau or not obj.gio_ket_thuc:
            return format_html('<span class="scmd-admin-pill scmd-admin-pill-danger">Thiếu giờ</span>')
        start = obj.gio_bat_dau.hour * 60 + obj.gio_bat_dau.minute
        end = obj.gio_ket_thuc.hour * 60 + obj.gio_ket_thuc.minute
        minutes = end - start
        if minutes <= 0:
            minutes += 24 * 60
        hours = minutes / 60
        hours_text = f'{hours:.1f}'.rstrip('0').rstrip('.')
        return format_html('<span class="scmd-admin-pill scmd-admin-pill-info">{} giờ</span>', hours_text)
    
    @admin.display(description='Sử dụng')
    def usage_summary(self, obj):
        today_count = getattr(obj, 'assignments_today', 0) or 0
        total_count = getattr(obj, 'assignments_total', 0) or 0
        tone = 'success' if today_count else 'muted'
        return format_html(
            '<div class="scmd-admin-cell scmd-shift-cell">'
            '<span><span class="scmd-admin-pill scmd-admin-pill-{}">Hôm nay: {}</span></span>'
            '<span>Tổng phân công: {}</span>'
            '</div>',
            tone,
            today_count,
            total_count,
        )
    
    @admin.display(description='Thao tác')
    def row_actions(self, obj):
        change_url = _safe_reverse('admin:operations_calamviec_change', args=[obj.pk])
        assignment_url = f"{_safe_reverse('admin:operations_phancongcatruc_changelist')}?ca_lam_viec__id__exact={obj.pk}"
        add_assignment_url = f"{_safe_reverse('admin:operations_phancongcatruc_add')}?ca_lam_viec={obj.pk}"
        links = [
            (change_url, 'Sửa'),
            (assignment_url, 'Ca trực'),
            (add_assignment_url, 'Thêm ca'),
        ]
        return format_html(
            '<div class="scmd-shift-row-actions">{}</div>',
            format_html_join(
                '',
                '<a class="scmd-shift-row-action" href="{}">{}</a>',
                links,
            ),
        )
    
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
        ('🕒 Thông tin check-in/out', {
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

class ChamCongAdminForm(forms.ModelForm):
    adjustment_reason = forms.CharField(
        required=False,
        label="Lý do điều chỉnh",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Bắt buộc khi sửa dữ liệu chấm công nhạy cảm.",
    )

    class Meta:
        model = ChamCong
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk and self.has_changed():
            tracked_fields = {
                "thoi_gian_check_in",
                "thoi_gian_check_out",
                "location_check_in",
                "location_check_out",
                "anh_check_in",
                "anh_check_out",
                "thuc_lam_gio",
                "ghi_chu",
            }
            if tracked_fields.intersection(set(self.changed_data)) and not cleaned_data.get("adjustment_reason"):
                raise ValidationError("Phải nhập lý do điều chỉnh khi sửa dữ liệu chấm công.")
        return cleaned_data


# --- 3. QUẢN LÝ SỰ CỐ ---
class BaoCaoSuCoAdminForm(forms.ModelForm):
    transition_reason = forms.CharField(
        required=False,
        label="Lý do chuyển trạng thái",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Bắt buộc khi chuyển trạng thái hoặc reopen hồ sơ sự cố đã đóng.",
    )

    class Meta:
        model = BaoCaoSuCo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Legacy incidents may have an empty detail field from older data paths.
        # Reopening a closed record must not force operators to rewrite that
        # historical field when it was not changed. New incidents still use the
        # model/admin contract.
        if self.instance and self.instance.pk and not (self.instance.mo_ta_chi_tiet or "").strip():
            field = self.fields.get("mo_ta_chi_tiet")
            if field is not None:
                field.required = False

    @staticmethod
    def _normalise_form_value(value):
        """Normalize form/model values before comparing locked incident fields.

        Admin forms may round-trip DB values through widgets with different
        Python representations: aware datetimes can lose microseconds, FK
        objects become primary keys, Decimal values may arrive as strings, and
        empty optional fields can be posted as ``""``. Closed-incident reopen
        protection must block only real business-field edits, not widget
        serialization noise.
        """
        from datetime import date, datetime
        from decimal import Decimal, InvalidOperation

        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            try:
                return Decimal(value)
            except (InvalidOperation, ValueError):
                return value
        if hasattr(value, "pk"):
            return value.pk
        if hasattr(value, "name") and hasattr(value, "storage"):
            return value.name or None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, datetime):
            # Admin datetime widgets round-trip second precision strings without
            # timezone metadata. Compare closed-incident fields by the displayed
            # wall-clock value so a pure POST/parse cycle is not treated as a
            # business edit.
            return value.replace(microsecond=0, tzinfo=None).isoformat(sep=" ")
        if isinstance(value, date):
            return value.isoformat()
        return value

    def _effectively_changed_model_fields(self, previous_obj, cleaned_data):
        """Return real protected-field changes for closed incident records.

        Do not rely on ``self.changed_data`` alone: for legacy records Django
        can mark fields as changed because widgets normalize ``None``/``""`` or
        trim datetimes to seconds. Compare only locked primary incident fields
        plus status, and normalize both sides before deciding that a real edit
        happened.
        """
        protected_fields = set(IncidentTransitionPolicy.get_locked_fields_for_closed_incident())
        fields_to_check = protected_fields | {"trang_thai"}
        changed_fields = []
        for field_name in fields_to_check:
            if field_name not in cleaned_data:
                continue
            old_value = getattr(previous_obj, field_name, None)
            new_value = cleaned_data.get(field_name)
            if self._normalise_form_value(old_value) != self._normalise_form_value(new_value):
                changed_fields.append(field_name)
        return changed_fields

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance or not self.instance.pk:
            return cleaned_data

        # Lấy trạng thái và dữ liệu gốc từ DB để chống race condition hoặc form manipulation.
        previous_obj = self.instance.__class__.objects.filter(pk=self.instance.pk).first()
        if previous_obj is None:
            return cleaned_data

        previous_status = previous_obj.trang_thai
        new_status = cleaned_data.get("trang_thai", previous_status)
        model_changed_fields = self._effectively_changed_model_fields(previous_obj, cleaned_data)
        transition_reason = cleaned_data.get("transition_reason", "").strip()

        if (
            previous_status
            and IncidentTransitionPolicy.requires_reason(previous_status, new_status)
            and not transition_reason
        ):
            raise ValidationError("Phải nhập lý do khi chuyển trạng thái sự cố.")

        try:
            IncidentTransitionPolicy.validate_transition(previous_status, new_status)
            IncidentTransitionPolicy.validate_closed_incident_edit(
                previous_status=previous_status,
                new_status=new_status,
                changed_fields=model_changed_fields,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))

        return cleaned_data



class PhanCongOperationalFilter(admin.SimpleListFilter):
    title = _('Tình trạng phân công')
    parameter_name = 'assignment_quality'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Hôm nay')),
            ('tomorrow', _('Ngày mai')),
            ('future', _('Sắp tới')),
            ('past_unchecked', _('Đã qua chưa check-in')),
            ('missing_checkin_today', _('Hôm nay chưa check-in')),
            ('working', _('Đang trực')),
            ('done', _('Hoàn thành')),
            ('missing_post', _('Thiếu chốt')),
            ('target_missing_gps', _('Mục tiêu thiếu GPS')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        if self.value() == 'today':
            return queryset.filter(ngay_truc=today)
        if self.value() == 'tomorrow':
            return queryset.filter(ngay_truc=tomorrow)
        if self.value() == 'future':
            return queryset.filter(ngay_truc__gt=today)
        if self.value() == 'past_unchecked':
            return queryset.filter(ngay_truc__lt=today, chamcong__thoi_gian_check_in__isnull=True)
        if self.value() == 'missing_checkin_today':
            return queryset.filter(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=True)
        if self.value() == 'working':
            return queryset.filter(chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=True)
        if self.value() == 'done':
            return queryset.filter(chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=False)
        if self.value() == 'missing_post':
            return queryset.filter(vi_tri_chot__isnull=True)
        if self.value() == 'target_missing_gps':
            return queryset.filter(Q(vi_tri_chot__muc_tieu__vi_do__isnull=True) | Q(vi_tri_chot__muc_tieu__kinh_do__isnull=True))
        return queryset


@admin.register(PhanCongCaTruc)
class PhanCongCaTrucAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/phancongcatruc/change_list.html'
    list_display = (
        'assignment_staff',
        'assignment_site',
        'assignment_schedule',
        'attendance_status',
        'attendance_times',
        'row_actions',
    )
    list_filter = (
        PhanCongOperationalFilter,
        ('ngay_truc', admin.DateFieldListFilter),
        TrangThaiPhanCongFilter,
        'ca_lam_viec',
        'vi_tri_chot__muc_tieu',
    )
    search_fields = (
        'nhan_vien__ho_ten',
        'nhan_vien__ma_nhan_vien',
        'nhan_vien__so_dien_thoai',
        'vi_tri_chot__ten_vi_tri',
        'vi_tri_chot__muc_tieu__ten_muc_tieu',
        'vi_tri_chot__muc_tieu__dia_chi',
        'vi_tri_chot__muc_tieu__hop_dong__so_hop_dong',
    )
    date_hierarchy = 'ngay_truc'
    inlines = [ChamCongInline]
    autocomplete_fields = ['nhan_vien', 'vi_tri_chot', 'ca_lam_viec']
    save_on_top = True
    list_per_page = 50
    ordering = ('-ngay_truc', 'ca_lam_viec__gio_bat_dau', 'vi_tri_chot__muc_tieu__ten_muc_tieu')

    fieldsets = (
        ("📝 THÔNG TIN PHÂN CÔNG", {
            'fields': (
                ('ngay_truc', 'ca_lam_viec'),
                ('nhan_vien', 'vi_tri_chot'),
            )
        }),
    )

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(ngay_truc=today)),
            tomorrow=Count('id', filter=Q(ngay_truc=tomorrow)),
            future=Count('id', filter=Q(ngay_truc__gt=today)),
            missing_checkin_today=Count('id', filter=Q(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=True)),
            working=Count('id', filter=Q(chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=True)),
            done_today=Count('id', filter=Q(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=False)),
            past_unchecked=Count('id', filter=Q(ngay_truc__lt=today, chamcong__thoi_gian_check_in__isnull=True)),
        )
        context = {
            'scmd_assignment_stats': {
                'total': stats['total'],
                'today': stats['today'],
                'tomorrow': stats['tomorrow'],
                'future': stats['future'],
                'missing_checkin_today': stats['missing_checkin_today'],
                'working': stats['working'],
                'done_today': stats['done_today'],
                'past_unchecked': stats['past_unchecked'],
            },
            'scmd_assignment_links': {
                'add': _safe_reverse('admin:operations_phancongcatruc_add'),
                'schedule': _safe_reverse('operations:xep_lich'),
                'posts': _safe_reverse('admin:operations_vitrichot_changelist'),
                'shifts': _safe_reverse('admin:operations_calamviec_changelist'),
                'attendance': _safe_reverse('admin:operations_chamcong_changelist'),
                'operations_dashboard': _safe_reverse('operations:dashboard_vanhanh'),
            },
            'scmd_today': today,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    @admin.display(description='Nhân sự', ordering='nhan_vien__ho_ten')
    def assignment_staff(self, obj):
        if not obj.nhan_vien:
            return _admin_badge('Thiếu nhân sự', 'danger')
        staff_change = _safe_reverse('admin:users_nhanvien_change', args=[obj.nhan_vien_id])
        phone = getattr(obj.nhan_vien, 'so_dien_thoai', '') or 'Chưa có SĐT'
        code = obj.nhan_vien.ma_nhan_vien or f'ID {obj.nhan_vien_id}'
        return format_html(
            '<div style="min-width:190px;line-height:1.28;">'
            '<a href="{}" style="font-weight:900;color:#0f2544;text-decoration:none;">{}</a>'
            '<div style="margin-top:3px;color:#64748b;font-size:12px;">{} · {}</div>'
            '</div>',
            staff_change,
            obj.nhan_vien.ho_ten,
            code,
            phone,
        )

    @admin.display(description='Mục tiêu / chốt', ordering='vi_tri_chot__muc_tieu__ten_muc_tieu')
    def assignment_site(self, obj):
        if not obj.vi_tri_chot:
            return _admin_badge('Thiếu chốt', 'danger')
        target = obj.vi_tri_chot.muc_tieu
        target_name = target.ten_muc_tieu if target else 'Chưa gắn mục tiêu'
        post_name = obj.vi_tri_chot.ten_vi_tri
        post_change = _safe_reverse('admin:operations_vitrichot_change', args=[obj.vi_tri_chot_id])
        target_change = _safe_reverse('admin:clients_muctieu_change', args=[target.pk]) if target else '#'
        gps_ok = bool(target and target.vi_do and target.kinh_do)
        gps_badge = _admin_badge('GPS OK', 'success') if gps_ok else _admin_badge('Thiếu GPS', 'warning')
        return format_html(
            '<div style="min-width:230px;line-height:1.3;">'
            '<a href="{}" style="font-weight:900;color:#0f2544;text-decoration:none;">{}</a>'
            '<div style="margin-top:3px;"><a href="{}" style="color:#2563eb;font-size:12px;text-decoration:none;font-weight:800;">{}</a></div>'
            '<div style="margin-top:5px;">{}</div>'
            '</div>',
            target_change,
            target_name,
            post_change,
            post_name,
            gps_badge,
        )

    @admin.display(description='Lịch trực', ordering='ngay_truc')
    def assignment_schedule(self, obj):
        day_text = obj.ngay_truc.strftime('%d/%m/%Y') if obj.ngay_truc else '--/--/----'
        weekday = obj.ngay_truc.strftime('%A') if obj.ngay_truc else ''
        ca = obj.ca_lam_viec.ten_ca if obj.ca_lam_viec else 'Chưa chọn ca'
        if obj.ca_lam_viec:
            window = f"{obj.ca_lam_viec.gio_bat_dau:%H:%M} → {obj.ca_lam_viec.gio_ket_thuc:%H:%M}"
        else:
            window = '--:-- → --:--'
        tone = 'warning' if obj.ngay_truc == timezone.localdate() else 'neutral'
        return format_html(
            '<div style="min-width:145px;line-height:1.3;">'
            '<div style="color:var(--scmd-text);font-weight:900;">{}</div>'
            '<div style="margin-top:4px;">{}</div>'
            '<div style="font-size:12px;color:#64748b;margin-top:4px;">{}</div>'
            '</div>',
            day_text,
            _admin_badge(ca, tone),
            window,
        )

    @admin.display(description='Trạng thái')
    def attendance_status(self, obj):
        try:
            cc = obj.chamcong
        except ChamCong.DoesNotExist:
            cc = None
        if cc and cc.thoi_gian_check_in and cc.thoi_gian_check_out:
            return _admin_badge('Hoàn thành', 'success')
        if cc and cc.thoi_gian_check_in:
            return _admin_badge('Đang trực', 'info')
        if obj.ngay_truc and obj.ngay_truc < timezone.localdate():
            return _admin_badge('Quá hạn chưa in', 'danger')
        if obj.ngay_truc == timezone.localdate():
            return _admin_badge('Chờ check-in', 'warning')
        return _admin_badge('Đã phân công', 'neutral')

    @admin.display(description='Giờ thực tế')
    def attendance_times(self, obj):
        try:
            cc = obj.chamcong
        except ChamCong.DoesNotExist:
            cc = None
        in_time = cc.thoi_gian_check_in.strftime('%H:%M') if cc and cc.thoi_gian_check_in else '--:--'
        out_time = cc.thoi_gian_check_out.strftime('%H:%M') if cc and cc.thoi_gian_check_out else '--:--'
        gps = _admin_badge('GPS hợp lệ', 'success') if cc and cc.vi_tri_hop_le else _admin_badge('Chưa xác thực', 'warning')
        return format_html(
            '<div style="min-width:95px;font-size:12px;line-height:1.45;color:#334155;">'
            '<strong>In:</strong> {}<br><strong>Out:</strong> {}<div style="margin-top:4px;">{}</div>'
            '</div>',
            in_time,
            out_time,
            gps,
        )

    @admin.display(description='Thao tác')
    def row_actions(self, obj):
        change_url = _safe_reverse('admin:operations_phancongcatruc_change', args=[obj.pk])
        attendance_url = _safe_reverse('admin:operations_chamcong_changelist')
        add_attendance_url = _safe_reverse('admin:operations_chamcong_add')
        schedule_base = _safe_reverse('operations:xep_lich')
        if schedule_base != '#' and obj.ngay_truc:
            schedule_url = f"{schedule_base}?date={obj.ngay_truc:%Y-%m-%d}&muc_tieu={obj.vi_tri_chot.muc_tieu_id if obj.vi_tri_chot else ''}"
        else:
            schedule_url = schedule_base
        try:
            has_attendance = bool(obj.chamcong)
        except ChamCong.DoesNotExist:
            has_attendance = False
        attendance_link = f'{attendance_url}?ca_truc__id__exact={obj.pk}' if has_attendance and attendance_url != '#' else f'{add_attendance_url}?ca_truc={obj.pk}'
        attendance_label = 'Chấm công' if has_attendance else 'Thêm công'
        return format_html(
            '<div style="display:flex;gap:5px;flex-wrap:wrap;min-width:150px;">'
            '<a class="button" style="padding:4px 8px;border-radius:8px;font-size:11px;font-weight:800;" href="{}">Sửa</a>'
            '<a class="button" style="padding:4px 8px;border-radius:8px;font-size:11px;font-weight:800;background:#0f2544;color:#fff;border-color:#0f2544;" href="{}">{}</a>'
            '<a class="button" style="padding:4px 8px;border-radius:8px;font-size:11px;font-weight:800;" href="{}">Lịch</a>'
            '</div>',
            change_url,
            attendance_link,
            attendance_label,
            schedule_url,
        )

    # --- Backward-compatible display methods kept for older templates/surfaces. ---
    nhan_vien_info = assignment_staff
    muc_tieu_info = assignment_site
    thoi_gian_truc_vn = assignment_schedule
    status_badge = attendance_status
    checkin_thuc_te = attendance_times

    def save_model(self, request, obj, form, change):
        if change:
            result = ShiftAssignmentPolicy.can_update_shift(request.user, obj)
        else:
            site = obj.vi_tri_chot.muc_tieu if obj.vi_tri_chot_id else None
            result = ShiftAssignmentPolicy.can_assign_shift(request.user, obj.nhan_vien, site, obj.ngay_truc)
        if not result.allowed:
            raise PermissionDenied(result.message)
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        result = ShiftAssignmentPolicy.can_delete_shift(request.user, obj)
        if not result.allowed:
            raise PermissionDenied(result.message)
        super().delete_model(request, obj)

    def get_queryset(self, request):
        scoped_ids = ShiftVisibilityPolicy.visible_shifts(request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=scoped_ids).select_related(
            'nhan_vien',
            'vi_tri_chot',
            'vi_tri_chot__muc_tieu',
            'vi_tri_chot__muc_tieu__hop_dong',
            'ca_lam_viec',
            'chamcong',
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return ShiftVisibilityPolicy.visible_shifts(request.user).filter(pk=obj.pk).exists()

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        if obj.is_payroll_locked:
            return False
        return ShiftAssignmentPolicy.can_update_shift(request.user, obj).allowed

    def has_delete_permission(self, request, obj=None):
        base_permission = super().has_delete_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        if obj.is_payroll_locked:
            return False
        return ShiftAssignmentPolicy.can_delete_shift(request.user, obj).allowed

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "nhan_vien":
            kwargs["queryset"] = StaffVisibilityPolicy.visible_staff(request.user)
        elif db_field.name == "vi_tri_chot":
            kwargs["queryset"] = PostVisibilityPolicy.visible_posts(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ChamCongOperationalFilter(admin.SimpleListFilter):
    title = _('Tình trạng chấm công')
    parameter_name = 'attendance_ops'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Hôm nay')),
            ('working', _('Đang trực')),
            ('completed_today', _('Hoàn thành hôm nay')),
            ('missing_checkout', _('Thiếu check-out')),
            ('no_checkin', _('Chưa check-in')),
            ('invalid_gps', _('GPS không hợp lệ')),
            ('no_photo_in', _('Thiếu ảnh vào')),
            ('no_photo_out', _('Thiếu ảnh ra')),
            ('late_or_early', _('Đi muộn / về sớm')),
            ('has_penalty', _('Có tiền phạt')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == 'today':
            return queryset.filter(ca_truc__ngay_truc=today)
        if self.value() == 'working':
            return queryset.filter(thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=True)
        if self.value() == 'completed_today':
            return queryset.filter(ca_truc__ngay_truc=today, thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=False)
        if self.value() == 'missing_checkout':
            return queryset.filter(thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=True)
        if self.value() == 'no_checkin':
            return queryset.filter(thoi_gian_check_in__isnull=True)
        if self.value() == 'invalid_gps':
            return queryset.filter(vi_tri_hop_le=False)
        if self.value() == 'no_photo_in':
            return queryset.filter(anh_check_in='') | queryset.filter(anh_check_in__isnull=True)
        if self.value() == 'no_photo_out':
            return queryset.filter(thoi_gian_check_out__isnull=False).filter(Q(anh_check_out='') | Q(anh_check_out__isnull=True))
        if self.value() == 'late_or_early':
            return queryset.filter(Q(di_muon_phut__gt=0) | Q(ve_som_phut__gt=0))
        if self.value() == 'has_penalty':
            return queryset.filter(phat_vi_pham__gt=0)
        return queryset



@admin.register(ShiftChangeRequest)
class ShiftChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("ma_yeu_cau", "requester_summary", "loai_yeu_cau", "trang_thai", "ngay_mong_muon", "created_at")
    list_filter = ("trang_thai", "loai_yeu_cau", ("ngay_mong_muon", admin.DateFieldListFilter), ("created_at", admin.DateFieldListFilter))
    search_fields = ("ma_yeu_cau", "nguoi_yeu_cau__ma_nhan_vien", "nguoi_yeu_cau__ho_ten", "nhan_vien_thay_the__ho_ten", "ly_do")
    autocomplete_fields = ("nguoi_yeu_cau", "nhan_vien_thay_the", "phan_cong_goc", "ca_mong_muon", "vi_tri_mong_muon", "nguoi_duyet")
    list_select_related = ("nguoi_yeu_cau", "nhan_vien_thay_the", "phan_cong_goc", "ca_mong_muon", "vi_tri_mong_muon", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = ShiftChangeRequest.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == ShiftChangeRequest.TrangThai.APPROVED and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
            if obj.trang_thai == ShiftChangeRequest.TrangThai.APPROVED:
                ShiftChangePermissionPolicy.enforce_approve(request.user, obj)
            if obj.trang_thai == ShiftChangeRequest.TrangThai.APPLIED:
                raise ValidationError(_("Không đánh dấu APPLIED trực tiếp trong admin; phải dùng ApplyShiftChangeRequestUseCase để cập nhật lịch trực và audit."))
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin shift change request status save")

    @admin.display(description=_("Người yêu cầu"), ordering="nguoi_yeu_cau__ho_ten")
    def requester_summary(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.nguoi_yeu_cau.ho_ten, obj.nguoi_yeu_cau.ma_nhan_vien)


@admin.register(ChamCong)
class ChamCongAdmin(admin.ModelAdmin):
    form = ChamCongAdminForm
    change_list_template = 'admin/operations/chamcong/change_list.html'
    list_display = (
        'attendance_staff',
        'attendance_site',
        'attendance_shift',
        'attendance_times',
        'attendance_quality',
        'attendance_evidence',
        'row_actions',
    )
    list_filter = (
        ChamCongOperationalFilter,
        'vi_tri_hop_le',
        ('thoi_gian_check_in', admin.DateFieldListFilter),
        'ca_truc__vi_tri_chot__muc_tieu',
    )
    search_fields = (
        'ca_truc__nhan_vien__ho_ten',
        'ca_truc__nhan_vien__ma_nhan_vien',
        'ca_truc__nhan_vien__so_dien_thoai',
        'ca_truc__vi_tri_chot__ten_vi_tri',
        'ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu',
        'ca_truc__vi_tri_chot__muc_tieu__dia_chi',
        'ca_truc__vi_tri_chot__muc_tieu__hop_dong__so_hop_dong',
    )
    autocomplete_fields = ['ca_truc']
    date_hierarchy = 'thoi_gian_check_in'
    save_on_top = True

    fieldsets = (
        ('📋 THÔNG TIN CA TRỰC', {
            'fields': ('ca_truc',)
        }),
        ('📥 Check-in', {
            'fields': (
                ('thoi_gian_check_in', 'lat_check_in', 'long_check_in'),
                ('anh_check_in', 'preview_in')
            )
        }),
        ('📤 Check-out', {
            'fields': (
                ('thoi_gian_check_out', 'lat_check_out', 'long_check_out'),
                ('anh_check_out', 'preview_out')
            )
        }),
        ('🛡️ Kiểm tra hợp lệ', {
            'fields': (
                'vi_tri_hop_le',
                'khoang_cach_check_in',
                ('di_muon_phut', 've_som_phut', 'thuc_lam_gio'),
                'phat_vi_pham',
                'ghi_chu'
            )
        }),
        ('🔐 Kiểm toán chỉnh sửa', {
            'fields': ('adjustment_reason',),
            'description': 'Bắt buộc nhập lý do khi sửa giờ công, GPS, ảnh hoặc ghi chú chấm công.',
        }),
    )
    readonly_fields = ('preview_in', 'preview_out')

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(ca_truc__ngay_truc=today)),
            working=Count('id', filter=Q(thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=True)),
            completed_today=Count('id', filter=Q(ca_truc__ngay_truc=today, thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=False)),
            invalid_gps=Count('id', filter=Q(vi_tri_hop_le=False)),
            missing_checkout=Count('id', filter=Q(thoi_gian_check_in__isnull=False, thoi_gian_check_out__isnull=True)),
            late_or_early=Count('id', filter=Q(di_muon_phut__gt=0) | Q(ve_som_phut__gt=0)),
            no_photo=Count('id', filter=Q(anh_check_in='') | Q(anh_check_in__isnull=True)),
        )
        links = {
            'add': _safe_reverse('admin:operations_chamcong_add'),
            'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
            'schedule': _safe_reverse('operations:xep_lich'),
            'reports': _safe_reverse('reports:tong_hop_cham_cong'),
            'operations': _safe_reverse('operations:dashboard_vanhanh'),
            'adjustments': _safe_reverse('admin:operations_chamcongadjustment_changelist'),
        }
        context = {
            'scmd_attendance_stats': stats,
            'scmd_attendance_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    @admin.display(description='Nhân sự', ordering='ca_truc__nhan_vien__ho_ten')
    def attendance_staff(self, obj):
        nv = getattr(obj.ca_truc, 'nhan_vien', None)
        if not nv:
            return _admin_badge('Thiếu nhân sự', 'danger')
        phone = getattr(nv, 'so_dien_thoai', None) or 'Chưa có SĐT'
        return format_html(
            '<div style="min-width:160px;line-height:1.35;">'
            '<strong style="color:#0f172a;font-size:13px;">{}</strong><br>'
            '<span style="color:#64748b;font-size:11px;">{} · {}</span>'
            '</div>',
            nv.ho_ten,
            nv.ma_nhan_vien,
            phone,
        )

    @admin.display(description='Mục tiêu / chốt')
    def attendance_site(self, obj):
        chot = getattr(obj.ca_truc, 'vi_tri_chot', None)
        muc_tieu = getattr(chot, 'muc_tieu', None) if chot else None
        if not muc_tieu:
            return _admin_badge('Thiếu mục tiêu', 'danger')
        return format_html(
            '<div style="min-width:190px;line-height:1.35;">'
            '<strong style="color:#1d4ed8;font-size:12px;">{}</strong><br>'
            '<span style="color:#475569;font-size:11px;">Chốt: {}</span>'
            '</div>',
            muc_tieu.ten_muc_tieu,
            chot.ten_vi_tri if chot else 'Chưa gắn chốt',
        )

    @admin.display(description='Ca trực', ordering='ca_truc__ngay_truc')
    def attendance_shift(self, obj):
        ca = getattr(obj.ca_truc, 'ca_lam_viec', None)
        ngay = obj.ca_truc.ngay_truc.strftime('%d/%m/%Y') if obj.ca_truc and obj.ca_truc.ngay_truc else '-'
        ca_label = ca.ten_ca if ca else 'Chưa có ca'
        return format_html(
            '<div style="min-width:120px;text-align:center;line-height:1.4;">'
            '<strong style="color:#0f172a;">{}</strong><br>'
            '<span style="display:inline-flex;margin-top:2px;padding:2px 8px;border-radius:999px;'
            'background:#f1f5f9;color:#475569;font-size:11px;font-weight:800;">{}</span>'
            '</div>',
            ngay,
            ca_label,
        )

    @admin.display(description='Giờ công')
    def attendance_times(self, obj):
        check_in = obj.thoi_gian_check_in.strftime('%H:%M') if obj.thoi_gian_check_in else '--:--'
        check_out = obj.thoi_gian_check_out.strftime('%H:%M') if obj.thoi_gian_check_out else '--:--'
        hours = f'{obj.thuc_lam_gio:.2f}h' if obj.thuc_lam_gio else '0h'
        tone = 'success' if obj.thoi_gian_check_in and obj.thoi_gian_check_out else 'warning' if obj.thoi_gian_check_in else 'neutral'
        return format_html(
            '<div style="min-width:115px;font-size:12px;line-height:1.45;">'
            '<span>Vào: <strong style="color:#047857;">{}</strong></span><br>'
            '<span>Ra: <strong style="color:#0f172a;">{}</strong></span><br>'
            '{}'
            '</div>',
            check_in,
            check_out,
            _admin_badge(hours, tone),
        )

    @admin.display(description='Đối soát')
    def attendance_quality(self, obj):
        chips = []
        chips.append(('GPS đúng' if obj.vi_tri_hop_le else 'Sai GPS', 'success' if obj.vi_tri_hop_le else 'danger'))
        if obj.khoang_cach_check_in is not None:
            distance = obj.khoang_cach_check_in or 0
            distance_label = f'{distance / 1000:.2f} km' if distance > 1000 else f'{int(distance)} m'
            chips.append((distance_label, 'neutral' if distance <= 200 else 'warning'))
        if obj.di_muon_phut:
            chips.append((f'Muộn {obj.di_muon_phut}p', 'warning'))
        if obj.ve_som_phut:
            chips.append((f'Về sớm {obj.ve_som_phut}p', 'warning'))
        if obj.phat_vi_pham:
            penalty = f'{obj.phat_vi_pham:,.0f}đ'
            chips.append((penalty, 'danger'))
        return format_html(
            '<div style="display:flex;gap:4px;flex-wrap:wrap;min-width:130px;">{}</div>',
            format_html_join('', '{}', ((_admin_badge(label, tone),) for label, tone in chips))
        )

    @admin.display(description='Bằng chứng')
    def attendance_evidence(self, obj):
        def thumb(image, label):
            if not image:
                return _admin_badge(f'Thiếu {label}', 'warning')
            return format_html(
                '<a href="{}" target="_blank" style="display:inline-flex;align-items:center;gap:5px;'
                'padding:4px 7px;border-radius:8px;background:#eff6ff;color:#1d4ed8;font-size:11px;'
                'font-weight:800;text-decoration:none;">Ảnh {}</a>',
                image.url,
                label,
            )
        return format_html(
            '<div style="display:flex;gap:5px;flex-wrap:wrap;min-width:110px;">{}{}</div>',
            thumb(obj.anh_check_in, 'vào'),
            thumb(obj.anh_check_out, 'ra') if obj.thoi_gian_check_out else _admin_badge('Chưa ra', 'neutral'),
        )

    @admin.display(description='Thao tác')
    def row_actions(self, obj):
        change_url = _safe_reverse('admin:operations_chamcong_change', args=[obj.pk])
        assignment_url = _safe_reverse('admin:operations_phancongcatruc_change', args=[obj.ca_truc_id]) if obj.ca_truc_id else '#'
        map_url = '#'
        if obj.lat_check_in and obj.long_check_in:
            map_url = f'https://www.google.com/maps?q={obj.lat_check_in},{obj.long_check_in}'
        buttons = [
            ('Sửa', change_url, 'default'),
            ('Ca trực', assignment_url, 'default'),
        ]
        if map_url != '#':
            buttons.append(('Bản đồ', map_url, 'primary'))
        rendered = []
        for label, url, tone in buttons:
            style = 'background:#0f2544;color:#fff;border-color:#0f2544;' if tone == 'primary' else ''
            if label == 'Bản đồ':
                rendered.append(format_html(
                    '<a class="button" target="_blank" style="padding:4px 8px;border-radius:8px;font-size:11px;font-weight:800;{}" href="{}">{}</a>',
                    style,
                    url,
                    label,
                ))
            else:
                rendered.append(format_html(
                    '<a class="button" style="padding:4px 8px;border-radius:8px;font-size:11px;font-weight:800;{}" href="{}">{}</a>',
                    style,
                    url,
                    label,
                ))
        return format_html(
            '<div style="display:flex;gap:5px;flex-wrap:wrap;min-width:140px;">{}</div>',
            format_html_join('', '{}', ((item,) for item in rendered))
        )

    # --- Backward-compatible display methods kept for older templates/surfaces. ---
    get_nhan_vien = attendance_staff
    get_muc_tieu = attendance_site
    thoi_gian_check_in_vn = attendance_times
    thoi_gian_check_out_vn = attendance_times
    show_thumbnail_in = attendance_evidence
    show_thumbnail_out = attendance_evidence
    gps_status = attendance_quality
    khoang_cach_display = attendance_quality

    def preview_in(self, obj):
        if obj.anh_check_in:
            return format_html('<img src="{}" style="max-height:300px; border-radius:8px;">', obj.anh_check_in.url)
        return ""

    def preview_out(self, obj):
        if obj.anh_check_out:
            return format_html('<img src="{}" style="max-height:300px; border-radius:8px;">', obj.anh_check_out.url)
        return ""

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ca_truc',
            'ca_truc__nhan_vien',
            'ca_truc__vi_tri_chot',
            'ca_truc__vi_tri_chot__muc_tieu',
            'ca_truc__vi_tri_chot__muc_tieu__hop_dong',
            'ca_truc__ca_lam_viec',
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return AttendanceVisibilityPolicy.visible_attendance(request.user).filter(pk=obj.pk).exists()

    def save_model(self, request, obj, form, change):
        if change and form.changed_data:
            persisted = CorrectAttendanceUseCase.execute(
                cham_cong_id=obj.pk,
                candidate=obj,
                changed_fields=form.changed_data,
                reason=form.cleaned_data.get("adjustment_reason", ""),
                actor_user=request.user,
            )
            obj.pk = persisted.pk
            return

        if change:
            previous_obj = self.get_queryset(request).get(pk=obj.pk)
            previous_state = {
                "thoi_gian_check_in": previous_obj.thoi_gian_check_in.isoformat() if previous_obj.thoi_gian_check_in else None,
                "thoi_gian_check_out": previous_obj.thoi_gian_check_out.isoformat() if previous_obj.thoi_gian_check_out else None,
                "thuc_lam_gio": previous_obj.thuc_lam_gio,
                "ghi_chu": previous_obj.ghi_chu,
                "location_check_in": previous_obj.location_check_in.wkt if previous_obj.location_check_in else None,
                "location_check_out": previous_obj.location_check_out.wkt if previous_obj.location_check_out else None,
            }
            if previous_obj.is_payroll_locked:
                raise ValidationError("Kỳ lương đã LOCKED/PAID. Không được sửa trực tiếp chấm công qua admin.")

        super().save_model(request, obj, form, change)

        if change and form.changed_data:
            current_state = {
                "thoi_gian_check_in": obj.thoi_gian_check_in.isoformat() if obj.thoi_gian_check_in else None,
                "thoi_gian_check_out": obj.thoi_gian_check_out.isoformat() if obj.thoi_gian_check_out else None,
                "thuc_lam_gio": obj.thuc_lam_gio,
                "ghi_chu": obj.ghi_chu,
                "location_check_in": obj.location_check_in.wkt if obj.location_check_in else None,
                "location_check_out": obj.location_check_out.wkt if obj.location_check_out else None,
            }
            actor = getattr(request.user, "nhan_vien", None)
            payroll_period = obj.get_related_payroll_period()
            reason = form.cleaned_data.get("adjustment_reason", "").strip()
            ChamCongAdjustment.objects.create(
                cham_cong=obj,
                bang_luong=payroll_period,
                nguoi_dieu_chinh=actor,
                ly_do=reason,
                truoc_dieu_chinh=previous_state or {},
                sau_dieu_chinh=current_state,
            )
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                module="operations",
                model_name="ChamCong",
                object_id=str(obj.pk),
                tenant_id=obj.tenant_id,
                note=f"Điều chỉnh chấm công qua admin: {reason}",
                changes={
                    "changed_fields": form.changed_data,
                    "payroll_period_id": payroll_period.pk if payroll_period else None,
                    "before": previous_state,
                    "after": current_state,
                },
            )


class BaoCaoSuCoOperationalFilter(admin.SimpleListFilter):
    """Bộ lọc tác nghiệp cho hồ sơ sự cố trong admin."""
    title = _('Tình trạng xử lý')
    parameter_name = 'incident_ops'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Phát sinh hôm nay')),
            ('open', _('Đang mở / chưa hoàn tất')),
            ('high_risk', _('Mức cao / nguy hiểm')),
            ('waiting_compensation', _('Chờ đền bù')),
            ('payroll_deduction', _('Có khoản trừ lương')),
            ('missing_handler', _('Chưa có cán bộ thụ lý')),
            ('missing_target', _('Chưa gắn mục tiêu')),
            ('missing_shift', _('Chưa gắn ca trực')),
            ('missing_evidence', _('Thiếu bằng chứng file/ảnh')),
            ('settlement_missing', _('Có đền bù nhưng chưa chốt quyết toán')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        open_statuses = ['CHO_XU_LY', 'DANG_XU_LY', 'DA_XU_LY', 'CHO_DEN_BU']
        value = self.value()
        if value == 'today':
            return queryset.filter(thoi_gian_phat_hien__date=today)
        if value == 'open':
            return queryset.filter(trang_thai__in=open_statuses)
        if value == 'high_risk':
            return queryset.filter(muc_do__in=['CAO', 'NGUY_HIEM'])
        if value == 'waiting_compensation':
            return queryset.filter(trang_thai='CHO_DEN_BU')
        if value == 'payroll_deduction':
            return queryset.filter(phai_thu_nhan_vien__gt=0)
        if value == 'missing_handler':
            return queryset.filter(nguoi_xu_ly__isnull=True)
        if value == 'missing_target':
            return queryset.filter(muc_tieu__isnull=True)
        if value == 'missing_shift':
            return queryset.filter(ca_truc__isnull=True)
        if value == 'missing_evidence':
            return queryset.filter(hinh_anh_1__isnull=True, hinh_anh_2__isnull=True, file_ghi_am__isnull=True)
        if value == 'settlement_missing':
            return queryset.filter(
                Q(tong_thiet_hai__gt=0) | Q(phai_thu_nhan_vien__gt=0),
                thoi_gian_quyet_toan__isnull=True,
            )
        return queryset


@admin.register(BaoCaoSuCo)
class BaoCaoSuCoAdmin(admin.ModelAdmin):
    form = BaoCaoSuCoAdminForm
    change_list_template = 'admin/operations/baocaosuco/change_list.html'
    list_display = (
        'incident_summary',
        'incident_target_context',
        'incident_reporter_context',
        'incident_lifecycle_badge',
        'incident_finance_reconciliation',
        'incident_evidence_badge',
        'incident_row_actions',
    )
    list_filter = (
        BaoCaoSuCoOperationalFilter,
        'muc_do',
        'trang_thai',
        ('thoi_gian_phat_hien', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'muc_tieu',
        'nguoi_xu_ly',
    )
    search_fields = (
        'ma_su_co',
        'tieu_de',
        'mo_ta_chi_tiet',
        'nhan_vien_bao_cao__ho_ten',
        'nhan_vien_bao_cao__ma_nhan_vien',
        'nhan_vien_bao_cao__so_dien_thoai',
        'muc_tieu__ten_muc_tieu',
        'muc_tieu__dia_chi',
        'muc_tieu__hop_dong__so_hop_dong',
        'nhan_vien_co_loi__ho_ten',
        'nguoi_xu_ly__ho_ten',
        'ghi_chu_quan_ly',
    )
    readonly_fields = ('ma_su_co', 'created_at', 'updated_at')
    autocomplete_fields = ['nhan_vien_bao_cao', 'muc_tieu', 'ca_truc', 'nguoi_xu_ly', 'nhan_vien_co_loi']
    date_hierarchy = 'thoi_gian_phat_hien'
    list_per_page = 50

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
                ('nguoi_xu_ly', 'thoi_gian_quyet_toan'),
                'ghi_chu_quan_ly'
            ),
            'classes': ('collapse',)
        }),
        ('🔐 QUẢN TRỊ VÒNG ĐỜI', {
            'fields': ('transition_reason',),
            'description': 'Hồ sơ HOAN_TAT/HUY chỉ được reopen về trạng thái đang xử lý và bắt buộc nhập lý do.',
        })
    )

    def get_queryset(self, request):
        scoped_ids = IncidentVisibilityPolicy.visible_incidents(request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=scoped_ids).select_related(
            'nhan_vien_bao_cao',
            'muc_tieu',
            'muc_tieu__hop_dong',
            'muc_tieu__hop_dong__khach_hang_cu',
            'ca_truc',
            'ca_truc__ca_lam_viec',
            'ca_truc__vi_tri_chot',
            'nhan_vien_co_loi',
            'nguoi_xu_ly',
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return IncidentVisibilityPolicy.visible_incidents(request.user).filter(pk=obj.pk).exists()

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return IncidentVisibilityPolicy.visible_incidents(request.user).filter(pk=obj.pk).exists()

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in {"nhan_vien_bao_cao", "nguoi_xu_ly", "nhan_vien_co_loi"}:
            kwargs["queryset"] = StaffVisibilityPolicy.visible_staff(request.user)
        elif db_field.name == "muc_tieu":
            kwargs["queryset"] = SiteVisibilityPolicy.visible_sites(request.user)
        elif db_field.name == "ca_truc":
            kwargs["queryset"] = ShiftVisibilityPolicy.visible_shifts(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        qs = self.get_queryset(request)
        open_statuses = ['CHO_XU_LY', 'DANG_XU_LY', 'DA_XU_LY', 'CHO_DEN_BU']
        stats = qs.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(thoi_gian_phat_hien__date=today)),
            open_cases=Count('id', filter=Q(trang_thai__in=open_statuses)),
            high_risk=Count('id', filter=Q(muc_do__in=['CAO', 'NGUY_HIEM'])),
            waiting_compensation=Count('id', filter=Q(trang_thai='CHO_DEN_BU')),
            payroll_deduction=Count('id', filter=Q(phai_thu_nhan_vien__gt=0)),
            missing_handler=Count('id', filter=Q(nguoi_xu_ly__isnull=True)),
            missing_evidence=Count('id', filter=Q(hinh_anh_1__isnull=True, hinh_anh_2__isnull=True, file_ghi_am__isnull=True)),
        )
        links = {
            'add': _safe_reverse('admin:operations_baocaosuco_add'),
            'reports': _safe_reverse('reports:su_co'),
            'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
            'attendance': _safe_reverse('admin:operations_chamcong_changelist'),
            'dashboard': _safe_reverse('operations:dashboard_vanhanh'),
        }
        context = {
            **(extra_context or {}),
            'scmd_incident_stats': {
                'total': stats['total'],
                'today': stats['today'],
                'open': stats['open_cases'],
                'high_risk': stats['high_risk'],
                'waiting_compensation': stats['waiting_compensation'],
                'payroll_deduction': stats['payroll_deduction'],
                'missing_handler': stats['missing_handler'],
                'missing_evidence': stats['missing_evidence'],
            },
            'scmd_incident_links': links,
        }
        return super().changelist_view(request, extra_context=context)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and IncidentTransitionPolicy.is_closed(obj.trang_thai):
            readonly_fields.extend(
                sorted(IncidentTransitionPolicy.get_locked_fields_for_closed_incident())
            )
        return tuple(dict.fromkeys(readonly_fields))

    @admin.display(description='Sự cố', ordering='thoi_gian_phat_hien')
    def incident_summary(self, obj):
        detected = obj.thoi_gian_phat_hien.strftime('%d/%m/%Y %H:%M') if obj.thoi_gian_phat_hien else 'Chưa rõ thời điểm'
        return format_html(
            '<div style="min-width:14rem;">'
            '<div style="color:var(--scmd-text);font-weight:900;line-height:1.25;">{}</div>'
            '<div style="font-size:12px;color:#475569;margin-top:3px;">{} · {}</div>'
            '<div style="font-size:12px;color:#64748b;margin-top:4px;max-width:360px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{}</div>'
            '</div>',
            obj.tieu_de or 'Sự cố chưa có tiêu đề',
            obj.ma_su_co or 'Chưa có mã',
            detected,
            obj.mo_ta_chi_tiet or 'Chưa nhập diễn biến chi tiết',
        )

    @admin.display(description='Mục tiêu / ca trực', ordering='muc_tieu__ten_muc_tieu')
    def incident_target_context(self, obj):
        target_name = obj.muc_tieu.ten_muc_tieu if obj.muc_tieu else 'Chưa gắn mục tiêu'
        contract_no = '-'
        if obj.muc_tieu and obj.muc_tieu.hop_dong:
            contract_no = obj.muc_tieu.hop_dong.so_hop_dong or '-'
        shift_text = 'Chưa gắn ca trực'
        if obj.ca_truc:
            shift_name = obj.ca_truc.ca_lam_viec.ten_ca if obj.ca_truc.ca_lam_viec else 'Ca trực'
            shift_date = obj.ca_truc.ngay_truc.strftime('%d/%m/%Y') if obj.ca_truc.ngay_truc else '-'
            shift_text = f'{shift_name} · {shift_date}'
        return format_html(
            '<div style="min-width:190px;">'
            '<div style="font-weight:850;color:#0f172a;">{}</div>'
            '<div style="font-size:12px;color:#64748b;margin-top:3px;">HĐ: {}</div>'
            '<div style="font-size:12px;color:#64748b;margin-top:3px;">{}</div>'
            '</div>',
            target_name,
            contract_no,
            shift_text,
        )

    @admin.display(description='Người báo / thụ lý', ordering='nhan_vien_bao_cao__ho_ten')
    def incident_reporter_context(self, obj):
        reporter = obj.nhan_vien_bao_cao.ho_ten if obj.nhan_vien_bao_cao else 'Chưa rõ người báo'
        reporter_code = obj.nhan_vien_bao_cao.ma_nhan_vien if obj.nhan_vien_bao_cao else '-'
        handler = obj.nguoi_xu_ly.ho_ten if obj.nguoi_xu_ly else 'Chưa phân công thụ lý'
        return format_html(
            '<div style="min-width:170px;">'
            '<div style="font-weight:850;color:#0f172a;">{}</div>'
            '<div style="font-size:12px;color:#64748b;margin-top:3px;">Mã NV: {}</div>'
            '<div style="font-size:12px;color:#334155;margin-top:5px;">Thụ lý: <strong>{}</strong></div>'
            '</div>',
            reporter,
            reporter_code or '-',
            handler,
        )

    @admin.display(description='Vòng đời', ordering='trang_thai')
    def incident_lifecycle_badge(self, obj):
        severity_colors = {
            'THAP': ('#f8fafc', '#475569'),
            'TB': ('#eff6ff', '#1d4ed8'),
            'CAO': ('#fffbeb', '#b45309'),
            'NGUY_HIEM': ('#fff1f2', '#be123c'),
        }
        status_colors = {
            'CHO_XU_LY': ('#fffbeb', '#b45309'),
            'DANG_XU_LY': ('#eff6ff', '#1d4ed8'),
            'DA_XU_LY': ('#ecfdf5', '#047857'),
            'CHO_DEN_BU': ('#fff7ed', '#c2410c'),
            'HOAN_TAT': ('#ecfdf5', '#047857'),
            'HUY': ('#f1f5f9', '#64748b'),
        }
        sev_bg, sev_fg = severity_colors.get(obj.muc_do, ('#f8fafc', '#475569'))
        st_bg, st_fg = status_colors.get(obj.trang_thai, ('#f8fafc', '#475569'))
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:5px;min-width:120px;">'
            '<span style="display:inline-flex;width:max-content;padding:4px 8px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:900;">{}</span>'
            '<span style="display:inline-flex;width:max-content;padding:4px 8px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:900;">{}</span>'
            '</div>',
            sev_bg,
            sev_fg,
            obj.get_muc_do_display(),
            st_bg,
            st_fg,
            obj.get_trang_thai_display(),
        )

    @admin.display(description='Đối soát thiệt hại', ordering='tong_thiet_hai')
    def incident_finance_reconciliation(self, obj):
        total = f"{obj.tong_thiet_hai or 0:,.0f}"
        company = f"{obj.cong_ty_chi_tra or 0:,.0f}"
        employee = f"{obj.phai_thu_nhan_vien or 0:,.0f}"
        settlement = obj.thoi_gian_quyet_toan.strftime('%d/%m/%Y') if obj.thoi_gian_quyet_toan else 'Chưa chốt'
        tone = '#be123c' if (obj.phai_thu_nhan_vien or 0) > 0 else '#047857'
        return format_html(
            '<div style="min-width:150px;font-size:12px;color:#334155;line-height:1.45;">'
            '<div>Tổng: <strong>{} đ</strong></div>'
            '<div>Công ty: <strong>{} đ</strong></div>'
            '<div>NV: <strong style="color:{};">{} đ</strong></div>'
            '<div style="color:#64748b;">Quyết toán: {}</div>'
            '</div>',
            total,
            company,
            tone,
            employee,
            settlement,
        )

    @admin.display(description='Bằng chứng')
    def incident_evidence_badge(self, obj):
        evidence_count = sum(bool(v) for v in [obj.hinh_anh_1, obj.hinh_anh_2, obj.file_ghi_am])
        bg = '#ecfdf5' if evidence_count else '#fff1f2'
        fg = '#047857' if evidence_count else '#be123c'
        label = f'{evidence_count} tệp' if evidence_count else 'Thiếu'
        return format_html(
            '<span style="display:inline-flex;padding:5px 9px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:900;white-space:nowrap;">{}</span>',
            bg,
            fg,
            label,
        )

    @admin.display(description='Thao tác')
    def incident_row_actions(self, obj):
        change_url = _safe_reverse('admin:operations_baocaosuco_change', args=[obj.pk])
        report_url = _safe_reverse('reports:export_incident_pdf', args=[obj.pk])
        assignment_url = '#'
        if obj.ca_truc_id:
            assignment_url = _safe_reverse('admin:operations_phancongcatruc_change', args=[obj.ca_truc_id])
        actions = [
            ('Sửa', change_url),
            ('PDF', report_url),
        ]
        if assignment_url != '#':
            actions.append(('Ca trực', assignment_url))
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;min-width:130px;">{}</div>',
            format_html_join(
                '',
                '<a href="{}" style="display:inline-flex;padding:5px 8px;border-radius:8px;border:1px solid #cbd5e1;color:#0f2544;text-decoration:none;font-size:11px;font-weight:850;">{}</a>',
                ((url, label) for label, url in actions),
            )
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

    def save_model(self, request, obj, form, change):
        previous_state = None
        previous_status = None
        changed_model_fields = [
            field_name for field_name in form.changed_data
            if field_name != "transition_reason"
        ]

        if change:
            previous_obj = self.get_queryset(request).get(pk=obj.pk)
            previous_status = previous_obj.trang_thai
            previous_state = {
                "trang_thai": previous_obj.trang_thai,
                "tieu_de": previous_obj.tieu_de,
                "muc_do": previous_obj.muc_do,
                "tong_thiet_hai": previous_obj.tong_thiet_hai,
                "cong_ty_chi_tra": previous_obj.cong_ty_chi_tra,
                "nhan_vien_co_loi_id": previous_obj.nhan_vien_co_loi_id,
                "phai_thu_nhan_vien": previous_obj.phai_thu_nhan_vien,
                "nguoi_xu_ly_id": previous_obj.nguoi_xu_ly_id,
            }

        super().save_model(request, obj, form, change)

        current_state = {
            "trang_thai": obj.trang_thai,
            "tieu_de": obj.tieu_de,
            "muc_do": obj.muc_do,
            "tong_thiet_hai": obj.tong_thiet_hai,
            "cong_ty_chi_tra": obj.cong_ty_chi_tra,
            "nhan_vien_co_loi_id": obj.nhan_vien_co_loi_id,
            "phai_thu_nhan_vien": obj.phai_thu_nhan_vien,
            "nguoi_xu_ly_id": obj.nguoi_xu_ly_id,
        }

        if not change:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.CREATE,
                module="operations",
                model_name="BaoCaoSuCo",
                object_id=str(obj.pk),
                tenant_id=obj.tenant_id,
                note="Tạo hồ sơ sự cố qua admin.",
                changes={"after": current_state},
            )
            return

        if not changed_model_fields:
            return

        transition_reason = form.cleaned_data.get("transition_reason", "").strip()
        status_changed = previous_status != obj.trang_thai
        if status_changed and IncidentTransitionPolicy.is_reopen(previous_status, obj.trang_thai):
            note = f"Reopen hồ sơ sự cố: {transition_reason}"
        elif status_changed:
            note = f"Chuyển trạng thái sự cố từ {previous_status} sang {obj.trang_thai}: {transition_reason}"
        else:
            note = "Cập nhật hồ sơ sự cố qua admin."

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="operations",
            model_name="BaoCaoSuCo",
            object_id=str(obj.pk),
            tenant_id=obj.tenant_id,
            note=note,
            changes={
                "changed_fields": changed_model_fields,
                "transition_reason": transition_reason or None,
                "before": previous_state,
                "after": current_state,
            },
        )


class BaoCaoDeXuatOperationalFilter(admin.SimpleListFilter):
    title = _('Tình trạng xử lý')
    parameter_name = 'dexuat_status'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Gửi hôm nay')),
            ('waiting_commander', _('Chờ chỉ huy mục tiêu')),
            ('waiting_ops', _('Chờ phòng nghiệp vụ')),
            ('need_office', _('Cần chuyển văn phòng điện tử')),
            ('done', _('Đã xử lý xong')),
            ('missing_target', _('Chưa gắn mục tiêu')),
            ('missing_evidence', _('Thiếu đính kèm')),
            ('no_commander_note', _('Chưa có ý kiến chỉ huy')),
            ('no_ops_owner', _('Chưa có người nghiệp vụ thụ lý')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        value = self.value()
        if value == 'today':
            return queryset.filter(ngay_gui__date=today)
        if value == 'waiting_commander':
            return queryset.filter(trang_thai=BaoCaoDeXuat.TrangThai.CHO_CHI_HUY)
        if value == 'waiting_ops':
            return queryset.filter(trang_thai=BaoCaoDeXuat.TrangThai.CHO_NGHIEP_VU)
        if value == 'need_office':
            return queryset.filter(trang_thai=BaoCaoDeXuat.TrangThai.CHUYEN_VAN_PHONG)
        if value == 'done':
            return queryset.filter(trang_thai__in=[BaoCaoDeXuat.TrangThai.DA_DUYET, BaoCaoDeXuat.TrangThai.TU_CHOI])
        if value == 'missing_target':
            return queryset.filter(muc_tieu__isnull=True)
        if value == 'missing_evidence':
            return queryset.filter(Q(hinh_anh__isnull=True) | Q(hinh_anh=''))
        if value == 'no_commander_note':
            return queryset.filter(Q(y_kien_chi_huy__isnull=True) | Q(y_kien_chi_huy=''))
        if value == 'no_ops_owner':
            return queryset.filter(nguoi_duyet_nghiep_vu__isnull=True)
        return queryset


@admin.register(BaoCaoDeXuat)
class BaoCaoDeXuatAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/baocaodexuat/change_list.html'
    list_display = (
        'proposal_summary',
        'guard_and_site_summary',
        'approval_flow_summary',
        'status_summary',
        'evidence_summary',
        'proposal_actions',
    )
    list_filter = (BaoCaoDeXuatOperationalFilter, 'trang_thai', 'loai_de_xuat', 'ngay_gui')
    search_fields = (
        'tieu_de',
        'noi_dung',
        'nhan_vien__ho_ten',
        'nhan_vien__ma_nhan_vien',
        'nhan_vien__sdt_chinh',
        'muc_tieu__ten_muc_tieu',
        'muc_tieu__dia_chi',
        'muc_tieu__hop_dong__so_hop_dong',
        'y_kien_chi_huy',
        'y_kien_nghiep_vu',
    )
    readonly_fields = ['tenant_id', 'ngay_gui']
    autocomplete_fields = ['nhan_vien', 'muc_tieu', 'chi_huy_duyet', 'nguoi_duyet_nghiep_vu']
    list_select_related = (
        'nhan_vien',
        'nhan_vien__phong_ban',
        'nhan_vien__chuc_danh',
        'muc_tieu',
        'muc_tieu__hop_dong',
        'muc_tieu__hop_dong__khach_hang_cu',
        'chi_huy_duyet',
        'nguoi_duyet_nghiep_vu',
    )
    actions = (
        'action_forward_to_operations',
        'action_approve_by_operations',
        'action_reject_by_operations',
        'action_escalate_to_office',
    )
    list_per_page = 50
    date_hierarchy = 'ngay_gui'
    ordering = ('-ngay_gui',)

    fieldsets = (
        ('💡 THÔNG TIN ĐỀ XUẤT TỪ HIỆN TRƯỜNG', {
            'fields': (
                'tenant_id',
                ('nhan_vien', 'muc_tieu'),
                ('loai_de_xuat', 'tieu_de'),
                'noi_dung', 'hinh_anh', 'ngay_gui'
            )
        }),
        ('👮 DUYỆT CẤP CHỈ HUY MỤC TIÊU', {
            'fields': (
                'chi_huy_duyet',
                'y_kien_chi_huy',
                'thoi_gian_chi_huy_duyet'
            ),
            'classes': ('collapse',),
        }),
        ('🛡️ PHÒNG NGHIỆP VỤ XỬ LÝ', {
            'description': _('Nếu vượt thẩm quyền phòng nghiệp vụ, chuyển trạng thái sang “Vượt thẩm quyền - Chuyển Văn phòng”, sau đó lập tờ trình/công việc tại Văn phòng điện tử.'),
            'fields': (
                'trang_thai',
                'nguoi_duyet_nghiep_vu',
                'y_kien_nghiep_vu',
                'thoi_gian_nghiep_vu_duyet'
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'nhan_vien',
            'nhan_vien__phong_ban',
            'nhan_vien__chuc_danh',
            'muc_tieu',
            'muc_tieu__hop_dong',
            'muc_tieu__hop_dong__khach_hang_cu',
            'chi_huy_duyet',
            'nguoi_duyet_nghiep_vu',
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return ProposalVisibilityPolicy.visible_proposals(request.user).filter(pk=obj.pk).exists()

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        stats = qs.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(ngay_gui__date=today)),
            waiting_commander=Count('id', filter=Q(trang_thai=BaoCaoDeXuat.TrangThai.CHO_CHI_HUY)),
            waiting_ops=Count('id', filter=Q(trang_thai=BaoCaoDeXuat.TrangThai.CHO_NGHIEP_VU)),
            need_office=Count('id', filter=Q(trang_thai=BaoCaoDeXuat.TrangThai.CHUYEN_VAN_PHONG)),
            approved=Count('id', filter=Q(trang_thai=BaoCaoDeXuat.TrangThai.DA_DUYET)),
            rejected=Count('id', filter=Q(trang_thai=BaoCaoDeXuat.TrangThai.TU_CHOI)),
            missing_evidence=Count('id', filter=Q(hinh_anh__isnull=True) | Q(hinh_anh='')),
        )
        links = {
            'add': _safe_reverse('admin:operations_baocaodexuat_add'),
            'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
            'incidents': _safe_reverse('admin:operations_baocaosuco_changelist'),
            'workflow_create': _safe_reverse('workflow:proposal_create'),
            'workflow_list': _safe_reverse('workflow:proposal_list'),
            'dashboard': _safe_reverse('operations:dashboard_vanhanh'),
        }
        context = {
            'scmd_field_proposal_stats': stats,
            'scmd_field_proposal_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    @admin.display(description='Đề xuất')
    def proposal_summary(self, obj):
        type_label = obj.get_loai_de_xuat_display()
        sent_at = timezone.localtime(obj.ngay_gui).strftime('%d/%m/%Y %H:%M') if obj.ngay_gui else '—'
        return format_html(
            '<div style="min-width:220px;line-height:1.35;">'
            '<div style="color:var(--scmd-text);font-weight:900;">{}</div>'
            '<div style="margin-top:4px;display:flex;gap:6px;flex-wrap:wrap;">{} {}</div>'
            '<div style="margin-top:5px;color:#64748b;font-size:12px;">Gửi: {}</div>'
            '</div>',
            obj.tieu_de,
            _admin_badge(type_label, 'info'),
            _admin_badge('Có đính kèm', 'success') if obj.hinh_anh else _admin_badge('Thiếu đính kèm', 'warning'),
            sent_at,
        )

    @admin.display(description='Nhân viên / mục tiêu')
    def guard_and_site_summary(self, obj):
        employee = obj.nhan_vien
        site = obj.muc_tieu
        emp_code = getattr(employee, 'ma_nhan_vien', '') or '—'
        emp_phone = getattr(employee, 'sdt_chinh', '') or 'Chưa có SĐT'
        site_name = site.ten_muc_tieu if site else 'Chưa gắn mục tiêu'
        contract = '—'
        if site and getattr(site, 'hop_dong', None):
            contract = getattr(site.hop_dong, 'so_hop_dong', None) or str(site.hop_dong)
        return format_html(
            '<div style="min-width:220px;line-height:1.35;">'
            '<div><strong>{}</strong> <span style="color:#64748b;">({})</span></div>'
            '<div style="color:#64748b;font-size:12px;">{}</div>'
            '<div style="margin-top:6px;font-weight:800;color:#0f172a;">{}</div>'
            '<div style="color:#64748b;font-size:12px;">HĐ: {}</div>'
            '</div>',
            employee.ho_ten if employee else 'Chưa rõ nhân viên',
            emp_code,
            emp_phone,
            site_name,
            contract,
        )

    @admin.display(description='Luồng xử lý')
    def approval_flow_summary(self, obj):
        commander = obj.chi_huy_duyet.ho_ten if obj.chi_huy_duyet else 'Chưa có chỉ huy duyệt'
        ops = obj.nguoi_duyet_nghiep_vu.ho_ten if obj.nguoi_duyet_nghiep_vu else 'Chưa có nghiệp vụ thụ lý'
        commander_tone = 'success' if obj.chi_huy_duyet else 'warning'
        ops_tone = 'success' if obj.nguoi_duyet_nghiep_vu else 'warning'
        return format_html(
            '<div style="min-width:210px;line-height:1.45;">'
            '<div>{} <span style="color:#475569;">{}</span></div>'
            '<div style="margin-top:4px;">{} <span style="color:#475569;">{}</span></div>'
            '</div>',
            _admin_badge('Chỉ huy', commander_tone), commander,
            _admin_badge('Nghiệp vụ', ops_tone), ops,
        )

    @admin.display(description='Trạng thái')
    def status_summary(self, obj):
        tone = {
            BaoCaoDeXuat.TrangThai.CHO_CHI_HUY: 'warning',
            BaoCaoDeXuat.TrangThai.CHO_NGHIEP_VU: 'info',
            BaoCaoDeXuat.TrangThai.DA_DUYET: 'success',
            BaoCaoDeXuat.TrangThai.TU_CHOI: 'danger',
            BaoCaoDeXuat.TrangThai.CHUYEN_VAN_PHONG: 'warning',
        }.get(obj.trang_thai, 'neutral')
        return _admin_badge(obj.get_trang_thai_display(), tone)

    @admin.display(description='Bằng chứng')
    def evidence_summary(self, obj):
        if not obj.hinh_anh:
            return _admin_badge('Chưa có file', 'warning')
        try:
            return format_html('<a href="{}" target="_blank" class="button" style="white-space:nowrap;">Mở file</a>', obj.hinh_anh.url)
        except Exception:
            return _admin_badge('File không sẵn sàng', 'danger')

    @admin.display(description='Thao tác')
    def proposal_actions(self, obj):
        change_url = _safe_reverse('admin:operations_baocaodexuat_change', args=[obj.pk])
        assignment_url = _safe_reverse('admin:operations_phancongcatruc_changelist')
        workflow_url = _safe_reverse('workflow:proposal_create') if obj.trang_thai == BaoCaoDeXuat.TrangThai.CHUYEN_VAN_PHONG else None
        buttons = [
            format_html('<a href="{}" class="button" style="margin-right:4px;">Sửa</a>', change_url),
            format_html('<a href="{}" class="button" style="margin-right:4px;">Ca trực</a>', assignment_url),
        ]
        if workflow_url:
            buttons.append(format_html('<a href="{}" class="button" style="margin-right:4px;">Tờ trình</a>', workflow_url))
        return format_html_join('', '{}', ((button,) for button in buttons))

    @admin.action(description='Chuyển sang Phòng nghiệp vụ xử lý')
    def action_forward_to_operations(self, request, queryset):
        actor = getattr(request.user, 'nhan_vien', None)
        update_extra = {'thoi_gian_chi_huy_duyet': timezone.now()}
        if actor:
            update_extra['chi_huy_duyet_id'] = actor.pk
        updated = _apply_admin_bulk_update(
            request, queryset.filter(trang_thai=BaoCaoDeXuat.TrangThai.CHO_CHI_HUY),
            module='operations', model_name='BaoCaoDeXuat', status_field='trang_thai',
            target_status=BaoCaoDeXuat.TrangThai.CHO_NGHIEP_VU,
            note='Admin proposal forward to operations', update_extra=update_extra,
        )
        self.message_user(request, f'Đã chuyển {updated} đề xuất sang Phòng nghiệp vụ.', messages.SUCCESS)

    @admin.action(description='Phòng nghiệp vụ chấp thuận đề xuất')
    def action_approve_by_operations(self, request, queryset):
        actor = getattr(request.user, 'nhan_vien', None)
        update_extra = {'thoi_gian_nghiep_vu_duyet': timezone.now()}
        if actor:
            update_extra['nguoi_duyet_nghiep_vu_id'] = actor.pk
        updated = _apply_admin_bulk_update(
            request, queryset.exclude(trang_thai__in=[BaoCaoDeXuat.TrangThai.DA_DUYET, BaoCaoDeXuat.TrangThai.TU_CHOI]),
            module='operations', model_name='BaoCaoDeXuat', status_field='trang_thai',
            target_status=BaoCaoDeXuat.TrangThai.DA_DUYET,
            note='Admin proposal approve by operations', update_extra=update_extra,
        )
        self.message_user(request, f'Đã chấp thuận {updated} đề xuất.', messages.SUCCESS)

    @admin.action(description='Phòng nghiệp vụ từ chối đề xuất')
    def action_reject_by_operations(self, request, queryset):
        actor = getattr(request.user, 'nhan_vien', None)
        update_extra = {'thoi_gian_nghiep_vu_duyet': timezone.now()}
        if actor:
            update_extra['nguoi_duyet_nghiep_vu_id'] = actor.pk
        updated = _apply_admin_bulk_update(
            request, queryset.exclude(trang_thai__in=[BaoCaoDeXuat.TrangThai.DA_DUYET, BaoCaoDeXuat.TrangThai.TU_CHOI]),
            module='operations', model_name='BaoCaoDeXuat', status_field='trang_thai',
            target_status=BaoCaoDeXuat.TrangThai.TU_CHOI,
            note='Admin proposal reject by operations', update_extra=update_extra,
        )
        self.message_user(request, f'Đã từ chối {updated} đề xuất.', messages.WARNING)

    @admin.action(description='Đánh dấu vượt thẩm quyền - cần trình Văn phòng điện tử')
    def action_escalate_to_office(self, request, queryset):
        actor = getattr(request.user, 'nhan_vien', None)
        update_extra = {'thoi_gian_nghiep_vu_duyet': timezone.now()}
        if actor:
            update_extra['nguoi_duyet_nghiep_vu_id'] = actor.pk
        updated = _apply_admin_bulk_update(
            request, queryset.exclude(trang_thai__in=[BaoCaoDeXuat.TrangThai.DA_DUYET, BaoCaoDeXuat.TrangThai.TU_CHOI]),
            module='operations', model_name='BaoCaoDeXuat', status_field='trang_thai',
            target_status=BaoCaoDeXuat.TrangThai.CHUYEN_VAN_PHONG,
            note='Admin proposal escalate to office', update_extra=update_extra,
        )
        self.message_user(request, f'Đã đánh dấu {updated} đề xuất cần trình qua Văn phòng điện tử.', messages.INFO)

class KiemTraQuanSoOperationalFilter(admin.SimpleListFilter):
    title = _('Tình trạng alive check')
    parameter_name = 'alive_status'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Phát lệnh hôm nay')),
            ('pending', _('Đang chờ phản hồi')),
            ('overdue', _('Quá hạn chưa phản hồi')),
            ('ok', _('Đã xác nhận')),
            ('missed', _('Bỏ lỡ / sai vị trí')),
            ('late', _('Phản hồi muộn')),
            ('no_photo', _('Thiếu ảnh xác thực')),
            ('has_device', _('Có mã thiết bị')),
            ('no_device', _('Thiếu mã thiết bị')),
            ('target_no_gps', _('Mục tiêu thiếu GPS')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        overdue_at = timezone.now() - timedelta(minutes=15)
        if self.value() == 'today':
            return queryset.filter(thoi_gian_gui_yeu_cau__date=today)
        if self.value() == 'pending':
            return queryset.filter(trang_thai='PENDING')
        if self.value() == 'overdue':
            return queryset.filter(trang_thai='PENDING', thoi_gian_gui_yeu_cau__lte=overdue_at)
        if self.value() == 'ok':
            return queryset.filter(trang_thai='OK')
        if self.value() == 'missed':
            return queryset.filter(trang_thai='MISSED')
        if self.value() == 'late':
            return queryset.filter(trang_thai='LATE')
        if self.value() == 'no_photo':
            return queryset.filter(Q(anh_xac_thuc__isnull=True) | Q(anh_xac_thuc='')).exclude(trang_thai='PENDING')
        if self.value() == 'has_device':
            return queryset.exclude(device_id_xac_thuc__isnull=True).exclude(device_id_xac_thuc='')
        if self.value() == 'no_device':
            return queryset.filter(Q(device_id_xac_thuc__isnull=True) | Q(device_id_xac_thuc='')).exclude(trang_thai='PENDING')
        if self.value() == 'target_no_gps':
            return queryset.filter(
                Q(ca_truc__vi_tri_chot__muc_tieu__vi_do__isnull=True)
                | Q(ca_truc__vi_tri_chot__muc_tieu__kinh_do__isnull=True)
            )
        return queryset


@admin.register(KiemTraQuanSo)
class KiemTraQuanSoAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/kiemtraquanso/change_list.html'
    list_display = (
        'employee_shift_summary',
        'target_summary',
        'request_response_summary',
        'verification_summary',
        'trang_thai_badge',
        'alive_actions',
    )
    list_filter = (KiemTraQuanSoOperationalFilter, 'trang_thai', 'thoi_gian_gui_yeu_cau')
    search_fields = (
        'ca_truc__nhan_vien__ma_nhan_vien',
        'ca_truc__nhan_vien__ho_ten',
        'ca_truc__nhan_vien__sdt_chinh',
        'ca_truc__vi_tri_chot__ten_vi_tri',
        'ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu',
        'ca_truc__vi_tri_chot__muc_tieu__dia_chi',
        'ca_truc__vi_tri_chot__muc_tieu__hop_dong__so_hop_dong',
        'device_id_xac_thuc',
        'toa_do_xac_thuc',
    )
    autocomplete_fields = ['ca_truc']
    readonly_fields = (
        'tenant_id',
        'thoi_gian_gui_yeu_cau',
        'thoi_gian_phan_hoi',
        'anh_xac_thuc',
        'toa_do_xac_thuc',
        'device_id_xac_thuc',
        'created_at',
        'alive_detail_summary',
    )
    fields = (
        'alive_detail_summary',
        'ca_truc',
        ('thoi_gian_gui_yeu_cau', 'thoi_gian_phan_hoi'),
        ('trang_thai', 'device_id_xac_thuc'),
        'toa_do_xac_thuc',
        'anh_xac_thuc',
        'tenant_id',
        'created_at',
    )
    list_per_page = 50
    actions = ('action_mark_missed',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ca_truc__nhan_vien',
            'ca_truc__nhan_vien__phong_ban',
            'ca_truc__nhan_vien__chuc_danh',
            'ca_truc__ca_lam_viec',
            'ca_truc__vi_tri_chot',
            'ca_truc__vi_tri_chot__muc_tieu',
            'ca_truc__vi_tri_chot__muc_tieu__hop_dong',
            'ca_truc__vi_tri_chot__muc_tieu__hop_dong__khach_hang_cu',
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return AliveCheckVisibilityPolicy.visible_alive_checks(request.user).filter(pk=obj.pk).exists()

    def changelist_view(self, request, extra_context=None):
        queryset = self.get_queryset(request)
        today = timezone.localdate()
        overdue_at = timezone.now() - timedelta(minutes=15)
        pending_qs = queryset.filter(trang_thai='PENDING')
        extra_context = extra_context or {}
        stats = queryset.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(thoi_gian_gui_yeu_cau__date=today)),
            pending=Count('id', filter=Q(trang_thai='PENDING')),
            overdue=Count('id', filter=Q(trang_thai='PENDING', thoi_gian_gui_yeu_cau__lte=overdue_at)),
            ok=Count('id', filter=Q(trang_thai='OK')),
            missed=Count('id', filter=Q(trang_thai='MISSED')),
            late=Count('id', filter=Q(trang_thai='LATE')),
            no_evidence=Count('id', filter=Q(anh_xac_thuc__isnull=True) | Q(anh_xac_thuc='')),
        )
        extra_context.update({
            'scmd_alive_stats': stats,
            'scmd_alive_links': {
                'add': _safe_reverse('admin:operations_kiemtraquanso_add'),
                'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
                'attendance': _safe_reverse('admin:operations_chamcong_changelist'),
                'violations_api': _safe_reverse('operations:api_alive_check_violations'),
                'dashboard': _safe_reverse('operations:dashboard_vanhanh'),
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request, obj)
        # Alive Check là dữ liệu kiểm toán hiện trường; chỉ cho xem chi tiết, không sửa tay.
        return False

    def has_delete_permission(self, request, obj=None):
        # Không xóa lịch sử kiểm tra quân số để giữ bằng chứng đối soát.
        return False

    @admin.display(description='Nhân sự / ca trực', ordering='ca_truc__nhan_vien__ho_ten')
    def employee_shift_summary(self, obj):
        ca = obj.ca_truc
        nv = getattr(ca, 'nhan_vien', None)
        shift = getattr(ca, 'ca_lam_viec', None)
        if not nv:
            return _admin_badge('Thiếu nhân sự', 'danger')
        return format_html(
            '<div style="min-width:230px;line-height:1.45;">'
            '<div style="color:var(--scmd-text);font-weight:900;">{} <span style="color:#64748b;font-weight:700;">{}</span></div>'
            '<div style="color:#475569;font-size:12px;">{} · {}</div>'
            '<div style="margin-top:4px;">{} {}</div>'
            '</div>',
            nv.ho_ten,
            nv.ma_nhan_vien or '',
            getattr(shift, 'ten_ca', 'Chưa có ca'),
            ca.ngay_truc.strftime('%d/%m/%Y') if getattr(ca, 'ngay_truc', None) else 'Chưa có ngày',
            _admin_badge('SĐT', 'neutral'),
            nv.sdt_chinh or 'Chưa có',
        )

    @admin.display(description='Mục tiêu / chốt', ordering='ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu')
    def target_summary(self, obj):
        post = getattr(obj.ca_truc, 'vi_tri_chot', None)
        target = getattr(post, 'muc_tieu', None) if post else None
        if not target:
            return _admin_badge('Thiếu mục tiêu', 'danger')
        gps_ok = bool(getattr(target, 'vi_do', None) and getattr(target, 'kinh_do', None))
        return format_html(
            '<div style="min-width:240px;line-height:1.45;">'
            '<div style="color:var(--scmd-text);font-weight:900;">{}</div>'
            '<div style="color:#475569;font-size:12px;">{}</div>'
            '<div style="margin-top:4px;">{} {}</div>'
            '</div>',
            target.ten_muc_tieu,
            getattr(post, 'ten_vi_tri', 'Chưa có chốt'),
            _admin_badge('GPS', 'success' if gps_ok else 'danger'),
            'Đã cấu hình' if gps_ok else 'Thiếu tọa độ',
        )

    @admin.display(description='Phát lệnh / phản hồi', ordering='thoi_gian_gui_yeu_cau')
    def request_response_summary(self, obj):
        request_at = obj.thoi_gian_gui_yeu_cau.strftime('%d/%m/%Y %H:%M') if obj.thoi_gian_gui_yeu_cau else '—'
        response_at = obj.thoi_gian_phan_hoi.strftime('%d/%m/%Y %H:%M') if obj.thoi_gian_phan_hoi else 'Chưa phản hồi'
        overdue = obj.trang_thai == 'PENDING' and obj.thoi_gian_gui_yeu_cau and obj.thoi_gian_gui_yeu_cau <= timezone.now() - timedelta(minutes=15)
        return format_html(
            '<div style="min-width:205px;line-height:1.45;">'
            '<div>{} <span style="color:#475569;">{}</span></div>'
            '<div style="margin-top:4px;">{} <span style="color:#475569;">{}</span></div>'
            '<div style="margin-top:4px;">{}</div>'
            '</div>',
            _admin_badge('Gửi', 'info'), request_at,
            _admin_badge('Phản hồi', 'success' if obj.thoi_gian_phan_hoi else 'warning'), response_at,
            _admin_badge('Quá hạn', 'danger') if overdue else _admin_badge('Trong kiểm soát', 'neutral'),
        )

    @admin.display(description='Xác thực')
    def verification_summary(self, obj):
        has_photo = bool(obj.anh_xac_thuc)
        has_device = bool(obj.device_id_xac_thuc)
        has_location = bool(obj.toa_do_xac_thuc)
        return format_html(
            '<div style="min-width:190px;line-height:1.65;">{}<br>{}<br>{}</div>',
            _admin_badge('Ảnh', 'success' if has_photo else 'warning'),
            _admin_badge('Thiết bị', 'success' if has_device else 'warning'),
            _admin_badge('Tọa độ', 'success' if has_location else 'warning'),
        )

    @admin.display(description='Trạng thái')
    def trang_thai_badge(self, obj):
        tone = {
            'PENDING': 'warning',
            'OK': 'success',
            'MISSED': 'danger',
            'LATE': 'warning',
        }.get(obj.trang_thai, 'neutral')
        return _admin_badge(obj.get_trang_thai_display(), tone)

    @admin.display(description='Thao tác')
    def alive_actions(self, obj):
        change_url = _safe_reverse('admin:operations_kiemtraquanso_change', args=[obj.pk])
        assignment_url = _safe_reverse('admin:operations_phancongcatruc_change', args=[obj.ca_truc_id]) if obj.ca_truc_id else _safe_reverse('admin:operations_phancongcatruc_changelist')
        buttons = [
            format_html('<a href="{}" class="button" style="margin-right:4px;">Xem</a>', change_url),
            format_html('<a href="{}" class="button" style="margin-right:4px;">Ca trực</a>', assignment_url),
        ]
        if obj.anh_xac_thuc:
            try:
                buttons.append(format_html('<a href="{}" target="_blank" class="button" style="margin-right:4px;">Ảnh</a>', obj.anh_xac_thuc.url))
            except Exception:
                pass
        if obj.toa_do_xac_thuc:
            coords = str(obj.toa_do_xac_thuc).split('|')[0]
            if ',' in coords:
                buttons.append(format_html('<a href="https://www.google.com/maps?q={}" target="_blank" class="button" style="margin-right:4px;">Bản đồ</a>', coords))
        return format_html_join('', '{}', ((button,) for button in buttons))

    @admin.display(description='Chi tiết Alive Check')
    def alive_detail_summary(self, obj):
        return format_html(
            '<div style="padding:12px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc;line-height:1.6;">'
            '<strong>Luồng nghiệp vụ:</strong> quản lý phát lệnh kiểm tra quân số → nhân viên bảo vệ phản hồi trên mobile → hệ thống lưu ảnh/tọa độ/thiết bị → phòng nghiệp vụ đối soát nếu bỏ lỡ hoặc sai vị trí.<br>'
            '<strong>Khuyến nghị:</strong> không sửa tay dữ liệu Alive Check; nếu có tranh chấp, đối chiếu với ca trực, chấm công, GPS và ảnh xác thực.'
            '</div>'
        )

    @admin.action(description='Đánh dấu bỏ lỡ cho các yêu cầu đang chờ')
    def action_mark_missed(self, request, queryset):
        updated = _apply_admin_bulk_update(
            request, queryset.filter(trang_thai='PENDING'),
            module='operations', model_name='KiemTraQuanSo', status_field='trang_thai',
            target_status='MISSED', note='Admin alive check marked missed',
        )
        self.message_user(request, f'Đã đánh dấu {updated} yêu cầu đang chờ thành bỏ lỡ.', messages.WARNING)


class ChamCongAdjustmentOperationalFilter(admin.SimpleListFilter):
    title = _('Tình trạng đối soát')
    parameter_name = 'adjustment_status'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Điều chỉnh hôm nay')),
            ('month', _('Điều chỉnh tháng này')),
            ('payroll_locked', _('Liên quan kỳ lương đã khóa/trả')),
            ('no_payroll', _('Chưa gắn kỳ lương')),
            ('has_actor', _('Có người điều chỉnh')),
            ('no_actor', _('Thiếu người điều chỉnh')),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        if self.value() == 'month':
            return queryset.filter(created_at__date__gte=today.replace(day=1))
        if self.value() == 'payroll_locked':
            return queryset.filter(bang_luong__trang_thai__in=['LOCKED', 'PAID'])
        if self.value() == 'no_payroll':
            return queryset.filter(bang_luong__isnull=True)
        if self.value() == 'has_actor':
            return queryset.filter(nguoi_dieu_chinh__isnull=False)
        if self.value() == 'no_actor':
            return queryset.filter(nguoi_dieu_chinh__isnull=True)
        return queryset


@admin.register(ChamCongAdjustment)
class ChamCongAdjustmentAdmin(admin.ModelAdmin):
    change_list_template = 'admin/operations/chamcongadjustment/change_list.html'
    list_display = (
        'adjustment_staff',
        'adjustment_shift',
        'changed_fields_badge',
        'payroll_status_badge',
        'actor_time',
        'row_actions',
    )
    list_filter = (
        ChamCongAdjustmentOperationalFilter,
        ('created_at', admin.DateFieldListFilter),
        'bang_luong__trang_thai',
    )
    search_fields = (
        'cham_cong__ca_truc__nhan_vien__ho_ten',
        'cham_cong__ca_truc__nhan_vien__ma_nhan_vien',
        'cham_cong__ca_truc__nhan_vien__so_dien_thoai',
        'cham_cong__ca_truc__vi_tri_chot__ten_vi_tri',
        'cham_cong__ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu',
        'cham_cong__ca_truc__vi_tri_chot__muc_tieu__hop_dong__so_hop_dong',
        'nguoi_dieu_chinh__ho_ten',
        'ly_do',
    )
    readonly_fields = (
        'tenant_id',
        'cham_cong',
        'bang_luong',
        'nguoi_dieu_chinh',
        'ly_do',
        'changed_fields_detail',
        'truoc_dieu_chinh',
        'sau_dieu_chinh',
        'created_at',
    )
    fieldsets = (
        ('Thông tin điều chỉnh', {
            'fields': (
                ('cham_cong', 'bang_luong'),
                ('nguoi_dieu_chinh', 'created_at'),
                'ly_do',
            )
        }),
        ('Đối chiếu dữ liệu trước/sau', {
            'fields': ('changed_fields_detail', 'truoc_dieu_chinh', 'sau_dieu_chinh'),
        }),
        ('Hệ thống', {
            'fields': ('tenant_id',),
            'classes': ('collapse',),
        }),
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50

    def get_queryset(self, request):
        # Adjustment visibility follows attendance visibility SSOT (Rule 14)
        scoped_ids = AttendanceVisibilityPolicy.visible_attendance(request.user).values_list("pk", flat=True)
        return (
            super().get_queryset(request).filter(cham_cong_id__in=scoped_ids)
            .select_related(
                'cham_cong',
                'cham_cong__ca_truc',
                'cham_cong__ca_truc__nhan_vien',
                'cham_cong__ca_truc__ca_lam_viec',
                'cham_cong__ca_truc__vi_tri_chot',
                'cham_cong__ca_truc__vi_tri_chot__muc_tieu',
                'cham_cong__ca_truc__vi_tri_chot__muc_tieu__hop_dong',
                'bang_luong',
                'nguoi_dieu_chinh',
            )
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        queryset = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        extra_context = extra_context or {}
        stats = queryset.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(created_at__date=today)),
            month=Count('id', filter=Q(created_at__date__gte=month_start)),
            locked_payroll=Count('id', filter=Q(bang_luong__trang_thai__in=['LOCKED', 'PAID'])),
            no_payroll=Count('id', filter=Q(bang_luong__isnull=True)),
            no_actor=Count('id', filter=Q(nguoi_dieu_chinh__isnull=True)),
        )
        extra_context.update({
            'scmd_adjustment_stats': stats,
            'scmd_adjustment_links': {
                'attendance': _safe_reverse('admin:operations_chamcong_changelist'),
                'assignments': _safe_reverse('admin:operations_phancongcatruc_changelist'),
                'payroll': _safe_reverse('admin:accounting_bangluongthang_changelist'),
                'reports': _safe_reverse('reports:tong_hop_cham_cong'),
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def _changed_field_names(self, obj):
        before = obj.truoc_dieu_chinh or {}
        after = obj.sau_dieu_chinh or {}
        keys = sorted(set(before.keys()) | set(after.keys()))
        return [key for key in keys if before.get(key) != after.get(key)]

    def _short_value(self, value):
        if value in (None, ''):
            return '—'
        text = str(value)
        return text if len(text) <= 42 else text[:39] + '…'

    @admin.display(description='Nhân sự')
    def adjustment_staff(self, obj):
        ca_truc = getattr(obj.cham_cong, 'ca_truc', None)
        nv = getattr(ca_truc, 'nhan_vien', None)
        if not nv:
            return _admin_badge('Thiếu nhân sự', 'danger')
        return format_html(
            '<div style="line-height:1.35;"><strong style="color:#0f172a;">{}</strong>'
            '<div style="font-size:12px;color:#64748b;">{} · {}</div></div>',
            nv.ho_ten,
            nv.ma_nhan_vien or 'Chưa có mã',
            nv.so_dien_thoai or 'Chưa có SĐT',
        )

    @admin.display(description='Ca / mục tiêu')
    def adjustment_shift(self, obj):
        ca_truc = getattr(obj.cham_cong, 'ca_truc', None)
        if not ca_truc:
            return _admin_badge('Thiếu ca trực', 'danger')
        vi_tri = getattr(ca_truc, 'vi_tri_chot', None)
        muc_tieu = getattr(vi_tri, 'muc_tieu', None) if vi_tri else None
        ca = getattr(ca_truc, 'ca_lam_viec', None)
        return format_html(
            '<div style="line-height:1.35;"><strong>{}</strong>'
            '<div style="font-size:12px;color:#64748b;">{} · {}</div>'
            '<div style="font-size:12px;color:#64748b;">{}</div></div>',
            muc_tieu.ten_muc_tieu if muc_tieu else 'Chưa rõ mục tiêu',
            vi_tri.ten_vi_tri if vi_tri else 'Chưa rõ chốt',
            ca.ten_ca if ca else 'Chưa rõ ca',
            ca_truc.ngay_truc.strftime('%d/%m/%Y') if ca_truc.ngay_truc else 'Chưa rõ ngày',
        )

    @admin.display(description='Trường thay đổi')
    def changed_fields_badge(self, obj):
        fields = self._changed_field_names(obj)
        if not fields:
            return _admin_badge('Không phát hiện diff', 'warning')
        labels = {
            'thoi_gian_check_in': 'Check-in',
            'thoi_gian_check_out': 'Check-out',
            'thuc_lam_gio': 'Giờ công',
            'ghi_chu': 'Ghi chú',
            'location_check_in': 'GPS vào',
            'location_check_out': 'GPS ra',
        }
        visible = [labels.get(field, field) for field in fields[:4]]
        if len(fields) > 4:
            visible.append(f'+{len(fields) - 4}')
        return format_html_join('', '{}', ((_admin_badge(item, 'info'),) for item in visible))

    @admin.display(description='Kỳ lương')
    def payroll_status_badge(self, obj):
        if not obj.bang_luong:
            return _admin_badge('Chưa gắn kỳ', 'warning')
        status = obj.bang_luong.trang_thai
        tone = 'danger' if status in ('LOCKED', 'PAID') else 'success' if status == 'REVIEWED' else 'info'
        return format_html(
            '<div style="line-height:1.35;">{}<div style="font-size:12px;color:#64748b;margin-top:3px;">Tháng {}/{}</div></div>',
            _admin_badge(obj.bang_luong.get_trang_thai_display(), tone),
            obj.bang_luong.thang,
            obj.bang_luong.nam,
        )

    @admin.display(description='Người / thời điểm')
    def actor_time(self, obj):
        actor = obj.nguoi_dieu_chinh.ho_ten if obj.nguoi_dieu_chinh else 'Không rõ người sửa'
        return format_html(
            '<div style="line-height:1.35;"><strong>{}</strong>'
            '<div style="font-size:12px;color:#64748b;">{}</div>'
            '<div style="font-size:12px;color:#64748b;">{}</div></div>',
            actor,
            obj.created_at.strftime('%d/%m/%Y %H:%M') if obj.created_at else '—',
            self._short_value(obj.ly_do),
        )

    @admin.display(description='Thao tác')
    def row_actions(self, obj):
        view_url = _safe_reverse('admin:operations_chamcongadjustment_change', args=[obj.pk])
        attendance_url = _safe_reverse('admin:operations_chamcong_change', args=[obj.cham_cong_id]) if obj.cham_cong_id else '#'
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a href="{}" style="padding:5px 8px;border-radius:8px;background:#0f2544;color:#fff;text-decoration:none;font-size:12px;font-weight:800;">Xem</a>'
            '<a href="{}" style="padding:5px 8px;border-radius:8px;background:#fff;border:1px solid #cbd5e1;color:#0f2544;text-decoration:none;font-size:12px;font-weight:800;">Chấm công</a>'
            '</div>',
            view_url,
            attendance_url,
        )

    @admin.display(description='Chi tiết thay đổi')
    def changed_fields_detail(self, obj):
        fields = self._changed_field_names(obj)
        if not fields:
            return format_html('<span style="color:#64748b;">Không phát hiện khác biệt giữa dữ liệu trước và sau.</span>')
        rows = []
        before = obj.truoc_dieu_chinh or {}
        after = obj.sau_dieu_chinh or {}
        labels = {
            'thoi_gian_check_in': 'Thời gian check-in',
            'thoi_gian_check_out': 'Thời gian check-out',
            'thuc_lam_gio': 'Giờ công thực tế',
            'ghi_chu': 'Ghi chú',
            'location_check_in': 'Vị trí check-in',
            'location_check_out': 'Vị trí check-out',
        }
        for field in fields:
            rows.append((
                labels.get(field, field),
                self._short_value(before.get(field)),
                self._short_value(after.get(field)),
            ))
        return format_html(
            '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            '<thead><tr>'
            '<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;">Trường</th>'
            '<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;">Trước</th>'
            '<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;">Sau</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html_join('', '<tr><td style="padding:8px;border-bottom:1px solid #f1f5f9;font-weight:700;">{}</td><td style="padding:8px;border-bottom:1px solid #f1f5f9;">{}</td><td style="padding:8px;border-bottom:1px solid #f1f5f9;">{}</td></tr>', rows)
        )
