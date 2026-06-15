# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: clients/admin.py
Author: Mr. Anh
Updated Date: 2026-03-21
Description: Cấu hình Admin Phân hệ Khách hàng (CRM) - Vertical Layout.
             UPGRADE: Tối ưu hiệu năng Query & Giao diện Trạng thái chuyên nghiệp.
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.forms import TextInput, NumberInput, Textarea
from django.utils.html import format_html, format_html_join
from django.urls import reverse, NoReverseMatch
from core.workflow_transition_policy import WorkflowTransitionPolicy
from .models import (
    KhachHangTiemNang, CoHoiKinhDoanh, HopDong, MucTieu, MucTieuDonGiaHistory,
    PhuLucHopDongDichVu, BienBanNghiemThu, HoaDon, CongNo,
    ThanhToanKhachHang, PhanBoThanhToanHoaDon,
)
from clients.access_policies import SiteVisibilityPolicy
from users.access_policies import StaffVisibilityPolicy
from main.models import AuditLog
from main.audit_utils import record_admin_audit_action
from clients.application.customer_payment_permission_policy import CustomerPaymentPermissionPolicy
from clients.application.customer_payment_use_cases import RecalculateReceivableStatusUseCase

# --- CONFIG MÀU SẮC ĐỒNG BỘ HỆ THỐNG SCMD ---
UI_COLORS = {
    'MOI': '#3b82f6',           # Blue
    'TIEM_NANG': '#f59e0b',     # Amber
    'CHOT_HOP_DONG': '#10b981', # Green
    'HUY': '#ef4444',           # Red
    'LIENHE': '#0284c7',        # Sky
    'BAOGIA': '#7c3aed',        # Purple
    'THUONGLUONG': '#d97706',   # Amber/Orange
    'THANHCONG': '#10b981',     # Green
    'THATBAI': '#ef4444',       # Red
    'HIEU_LUC': '#10b981',      # Emerald
    'SAP_HET_HAN': '#eab308',   # Yellow
    'DA_THANH_LY': '#64748b',   # Slate
}

def format_html_status(text, status_code):
    """Định dạng badge trạng thái theo chuẩn SCMD Pro."""
    color = UI_COLORS.get(status_code, '#475569')
    return format_html(
        '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; '
        'font-weight: 800; font-size: 10px; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.12); '
        'display: inline-block; min-width: 80px; text-align: center;">{}</span>',
        color, text
    )


def _safe_reverse(viewname, *, args=None, fallback="#"):
    """Reverse URL cho CTA trong admin, fallback an toàn nếu route chưa tồn tại."""
    try:
        return reverse(viewname, args=args)
    except NoReverseMatch:
        return fallback


def _assert_payment_allocation_immutable(existing, candidate):
    """Block direct admin mutation of allocated customer payment source fields."""
    if not existing or not existing.cac_phan_bo.exists():
        return
    immutable_fields = ThanhToanKhachHang.IMMUTABLE_AFTER_ALLOCATION_FIELDS
    changed = []
    for field_name in immutable_fields:
        old_value = getattr(existing, field_name)
        new_value = getattr(candidate, field_name)
        if field_name == "file_chung_tu":
            old_value = getattr(old_value, "name", str(old_value or ""))
            new_value = getattr(new_value, "name", str(new_value or ""))
        if old_value != new_value:
            changed.append(field_name)
    if changed:
        raise ValidationError("Không được sửa chứng từ thanh toán đã phát sinh phân bổ. Cần chứng từ đảo/điều chỉnh riêng.")


def _assert_allocation_source_immutable(existing, candidate):
    """Block direct admin mutation of allocation source fields after creation."""
    if not existing:
        return
    changed = [
        field_name
        for field_name in PhanBoThanhToanHoaDon.IMMUTABLE_SOURCE_FIELDS
        if getattr(existing, field_name) != getattr(candidate, field_name)
    ]
    if changed:
        raise ValidationError("Không được sửa phân bổ thanh toán đã tạo. Cần chứng từ đảo/điều chỉnh riêng.")


def _apply_client_status_action(request, queryset, *, model_name, target_status, note):
    changed = 0
    with transaction.atomic():
        for obj in queryset.select_for_update().order_by("pk"):
            old_status = obj.trang_thai
            if old_status == target_status:
                continue
            obj.trang_thai = target_status
            obj.save(update_fields=["trang_thai"])
            record_admin_audit_action(
                request,
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name=model_name,
                object_id=obj.pk,
                note=note,
                changes={"trang_thai": {"old": old_status, "new": target_status}},
            )
            changed += 1
    return changed

def _admin_change_url(obj, viewname):
    return _safe_reverse(viewname, args=[obj.pk]) if obj and obj.pk else "#"


class LeadDataQualityFilter(admin.SimpleListFilter):
    title = "Chất lượng dữ liệu"
    parameter_name = "lead_quality"

    def lookups(self, request, model_admin):
        return (
            ("missing_contact", "Thiếu người liên hệ"),
            ("missing_phone", "Thiếu SĐT"),
            ("missing_email", "Thiếu email"),
            ("no_opportunity", "Chưa có cơ hội"),
            ("has_opportunity", "Đã có cơ hội"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing_contact":
            return queryset.filter(Q(nguoi_lien_he__isnull=True) | Q(nguoi_lien_he=""))
        if value == "missing_phone":
            return queryset.filter(Q(sdt__isnull=True) | Q(sdt=""))
        if value == "missing_email":
            return queryset.filter(Q(email__isnull=True) | Q(email=""))
        if value == "no_opportunity":
            return queryset.annotate(_lead_filter_opp_count=Count("cac_co_hoi_kinh_doanh", distinct=True)).filter(_lead_filter_opp_count=0)
        if value == "has_opportunity":
            return queryset.annotate(_lead_filter_opp_count=Count("cac_co_hoi_kinh_doanh", distinct=True)).filter(_lead_filter_opp_count__gt=0)
        return queryset


class CoHoiQualityFilter(admin.SimpleListFilter):
    title = "Chất lượng pipeline"
    parameter_name = "opportunity_quality"

    def lookups(self, request, model_admin):
        return (
            ("missing_owner", "Chưa có sales phụ trách"),
            ("zero_value", "Chưa nhập giá trị"),
            ("won_no_contract", "Đã thắng chưa có hợp đồng"),
            ("open_pipeline", "Pipeline đang mở"),
            ("closed_pipeline", "Đã đóng"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing_owner":
            return queryset.filter(nguoi_phu_trach__isnull=True)
        if value == "zero_value":
            return queryset.filter(Q(gia_tri_uoc_tinh__isnull=True) | Q(gia_tri_uoc_tinh=0))
        if value == "won_no_contract":
            return queryset.filter(trang_thai=CoHoiKinhDoanh.TrangThai.THANH_CONG, hop_dong__isnull=True)
        if value == "open_pipeline":
            return queryset.exclude(trang_thai__in=[CoHoiKinhDoanh.TrangThai.THANH_CONG, CoHoiKinhDoanh.TrangThai.THAT_BAI])
        if value == "closed_pipeline":
            return queryset.filter(trang_thai__in=[CoHoiKinhDoanh.TrangThai.THANH_CONG, CoHoiKinhDoanh.TrangThai.THAT_BAI])
        return queryset

class HopDongQualityFilter(admin.SimpleListFilter):
    title = "Chất lượng hợp đồng"
    parameter_name = "contract_quality"

    def lookups(self, request, model_admin):
        return (
            ("expiring_30", "Sắp hết hạn 30 ngày"),
            ("expired", "Đã quá hạn theo ngày"),
            ("missing_customer", "Thiếu khách hàng"),
            ("missing_file", "Thiếu file hợp đồng"),
            ("missing_opportunity", "Không gắn cơ hội"),
            ("no_targets", "Chưa có mục tiêu"),
            ("has_targets", "Đã có mục tiêu"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()
        next_30 = today + timezone.timedelta(days=30)
        if value == "expiring_30":
            return queryset.filter(ngay_het_han__gte=today, ngay_het_han__lte=next_30).exclude(trang_thai="DA_THANH_LY")
        if value == "expired":
            return queryset.filter(ngay_het_han__lt=today).exclude(trang_thai="DA_THANH_LY")
        if value == "missing_customer":
            return queryset.filter(khach_hang_cu__isnull=True)
        if value == "missing_file":
            return queryset.filter(Q(file_hop_dong__isnull=True) | Q(file_hop_dong=""))
        if value == "missing_opportunity":
            return queryset.filter(co_hoi__isnull=True)
        if value == "no_targets":
            return queryset.annotate(_contract_target_count=Count("cac_muc_tieu", distinct=True)).filter(_contract_target_count=0)
        if value == "has_targets":
            return queryset.annotate(_contract_target_count=Count("cac_muc_tieu", distinct=True)).filter(_contract_target_count__gt=0)
        return queryset

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
    """Admin lead/khách hàng tiềm năng cho bộ phận kinh doanh.

    Mục tiêu: danh sách gọn, dễ lọc, CTA thật, không nhồi quá nhiều thông tin
    vào một dòng khiến người dùng cuối khó thao tác.
    """
    change_list_template = "admin/clients/khachhangtiemnang/change_list.html"
    list_display = [
        'lead_identity',
        'contact_summary',
        'show_trang_thai',
        'source_display',
        'pipeline_summary',
        'ngay_tao_vn',
        'row_actions',
    ]
    list_filter = [
        'trang_thai',
        'nguon',
        LeadDataQualityFilter,
        ('ngay_tao', admin.DateFieldListFilter),
    ]
    search_fields = [
        'ten_cong_ty',
        'sdt',
        'email',
        'nguoi_lien_he',
        'cac_co_hoi_kinh_doanh__ten_co_hoi',
    ]
    inlines = [CoHoiInline]
    save_on_top = True
    list_per_page = 50
    readonly_fields = ['ngay_tao']
    search_help_text = "Tìm theo tên khách hàng, người liên hệ, SĐT, email hoặc tên cơ hội."
    actions = ['mark_as_nurturing', 'mark_as_quoted', 'mark_as_lost']

    fieldsets = (
        ("Thông tin khách hàng", {
            'description': "Thông tin pháp lý và định danh tổ chức khách hàng.",
            'fields': (
                'ten_cong_ty',
                'trang_thai',
                'nguon',
                'dia_chi',
                'ngay_tao'
            )
        }),
        ("Đầu mối liên hệ", {
            'description': "Người phụ trách liên hệ trực tiếp tại đơn vị khách hàng.",
            'fields': (
                'nguoi_lien_he',
                'sdt',
                'email',
            )
        }),
        ("Ghi chú chăm sóc", {
            'fields': (
                'ghi_chu',
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_opportunity_count=Count('cac_co_hoi_kinh_doanh', distinct=True))

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        total = qs.count()
        stats = {
            'total': total,
            'new': qs.filter(trang_thai='MOI').count(),
            'nurturing': qs.filter(trang_thai__in=['TIEM_NANG', 'BAO_GIA']).count(),
            'quoted': qs.filter(trang_thai='BAO_GIA').count(),
            'won': qs.filter(trang_thai='CHOT_HOP_DONG').count(),
            'lost': qs.filter(trang_thai='HUY').count(),
            'missing_contact': qs.filter(Q(nguoi_lien_he__isnull=True) | Q(nguoi_lien_he='')).count(),
            'missing_phone': qs.filter(Q(sdt__isnull=True) | Q(sdt='')).count(),
        }
        links = {
            'add_lead': _safe_reverse('admin:clients_khachhangtiemnang_add'),
            'opportunity_list': _safe_reverse('admin:clients_cohoikinhdoanh_changelist'),
            'add_opportunity': _safe_reverse('admin:clients_cohoikinhdoanh_add'),
            'contract_list': _safe_reverse('admin:clients_hopdong_changelist'),
            'crm_dashboard': _safe_reverse('clients:dashboard_crm'),
            'pipeline': _safe_reverse('clients:pipeline'),
        }
        context = {
            'scmd_lead_stats': stats,
            'scmd_lead_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def lead_identity(self, obj):
        url = _admin_change_url(obj, 'admin:clients_khachhangtiemnang_change')
        address = obj.dia_chi or 'Chưa có địa chỉ'
        return format_html(
            '<div class="scmd-lead-cell"><a class="scmd-lead-main" href="{}">{}</a><span>{}</span></div>',
            url,
            obj.ten_cong_ty,
            address,
        )
    lead_identity.short_description = "Khách hàng"
    lead_identity.admin_order_field = 'ten_cong_ty'

    def contact_summary(self, obj):
        rows = []
        if obj.nguoi_lien_he:
            rows.append(format_html('<strong>{}</strong>', obj.nguoi_lien_he))
        else:
            rows.append(format_html('<span class="scmd-lead-warning">Thiếu người liên hệ</span>'))
        if obj.sdt:
            rows.append(format_html('<a href="tel:{}">{}</a>', obj.sdt, obj.sdt))
        else:
            rows.append(format_html('<span class="scmd-lead-warning">Thiếu SĐT</span>'))
        if obj.email:
            rows.append(format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email))
        return format_html('<div class="scmd-lead-cell">{}</div>', format_html_join('', '<span>{}</span>', ((row,) for row in rows)))
    contact_summary.short_description = "Liên hệ"

    def source_display(self, obj):
        return format_html('<span class="scmd-lead-pill">{}</span>', obj.get_nguon_display() if obj.nguon else 'Chưa rõ')
    source_display.short_description = "Nguồn"
    source_display.admin_order_field = 'nguon'

    def pipeline_summary(self, obj):
        count = getattr(obj, '_opportunity_count', None)
        if count is None:
            count = obj.cac_co_hoi_kinh_doanh.count()
        opportunity_url = _safe_reverse('admin:clients_cohoikinhdoanh_changelist')
        query = f'?khach_hang_tiem_nang__id__exact={obj.pk}'
        if count:
            return format_html('<a class="scmd-lead-pill scmd-lead-pill-info" href="{}{}">{} cơ hội</a>', opportunity_url, query, count)
        add_url = _safe_reverse('admin:clients_cohoikinhdoanh_add')
        return format_html('<a class="scmd-lead-pill scmd-lead-pill-muted" href="{}?khach_hang_tiem_nang={}">Tạo cơ hội</a>', add_url, obj.pk)
    pipeline_summary.short_description = "Pipeline"

    def row_actions(self, obj):
        change_url = _admin_change_url(obj, 'admin:clients_khachhangtiemnang_change')
        add_opp_url = _safe_reverse('admin:clients_cohoikinhdoanh_add')
        return format_html(
            '<div class="scmd-admin-actions"><a class="button scmd-admin-mini-button" href="{}">Sửa</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}?khach_hang_tiem_nang={}">Cơ hội</a></div>',
            change_url,
            add_opp_url,
            obj.pk,
        )
    row_actions.short_description = "Thao tác"

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
    show_trang_thai.admin_order_field = 'trang_thai'

    def mark_as_nurturing(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='KhachHangTiemNang', target_status='TIEM_NANG', note='Admin lead status to TIEM_NANG')
        self.message_user(request, f"Đã chuyển {updated} khách hàng sang trạng thái Đang chăm sóc.")
    mark_as_nurturing.short_description = "Chuyển sang Đang chăm sóc"

    def mark_as_quoted(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='KhachHangTiemNang', target_status='BAO_GIA', note='Admin lead status to BAO_GIA')
        self.message_user(request, f"Đã chuyển {updated} khách hàng sang trạng thái Đã gửi báo giá.")
    mark_as_quoted.short_description = "Chuyển sang Đã gửi báo giá"

    def mark_as_lost(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='KhachHangTiemNang', target_status='HUY', note='Admin lead status to HUY')
        self.message_user(request, f"Đã đánh dấu {updated} khách hàng là Thất bại/Hủy.")
    mark_as_lost.short_description = "Đánh dấu Thất bại/Hủy"

# --- 2. CƠ HỘI KINH DOANH ---
@admin.register(CoHoiKinhDoanh)
class CoHoiKinhDoanhAdmin(admin.ModelAdmin):
    """Admin pipeline/cơ hội kinh doanh.

    Mục tiêu: danh sách cơ hội phải giúp sales/admin nhận biết nhanh giai đoạn,
    giá trị pipeline, chủ sở hữu, khách hàng gốc và bước tiếp theo. Không nhồi
    quá nhiều cột vào bảng để tránh cải lùi UX của Django Admin.
    """
    change_list_template = "admin/clients/cohoikinhdoanh/change_list.html"
    list_display = [
        'opportunity_identity',
        'customer_summary',
        'show_gia_tri',
        'show_trang_thai',
        'owner_summary',
        'ngay_tao_vn',
        'row_actions',
    ]
    list_filter = [
        'trang_thai',
        'nguoi_phu_trach',
        CoHoiQualityFilter,
        ('ngay_tao', admin.DateFieldListFilter),
    ]
    search_fields = [
        'ten_co_hoi',
        'khach_hang_tiem_nang__ten_cong_ty',
        'khach_hang_tiem_nang__nguoi_lien_he',
        'khach_hang_tiem_nang__sdt',
        'nguoi_phu_trach__ho_ten',
        'nguoi_phu_trach__ma_nv',
    ]
    autocomplete_fields = ['khach_hang_tiem_nang', 'nguoi_phu_trach']
    save_on_top = True
    readonly_fields = ['ngay_tao']
    list_per_page = 50
    search_help_text = "Tìm theo tên cơ hội, khách hàng, người liên hệ, SĐT, mã/tên sales phụ trách."
    actions = [
        'mark_as_contacting',
        'mark_as_quoted',
        'mark_as_negotiating',
        'mark_as_won',
        'mark_as_lost',
    ]

    fieldsets = (
        ("Thông tin cơ hội", {
            'description': "Cơ hội kinh doanh là bước trung gian từ lead sang hợp đồng/mục tiêu bảo vệ.",
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


    def save_model(self, request, obj, form, change):
        obj._audit_user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('khach_hang_tiem_nang', 'nguoi_phu_trach')
            .annotate(_contract_count=Count('hop_dong', distinct=True))
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        total = qs.count()
        open_qs = qs.exclude(trang_thai__in=[CoHoiKinhDoanh.TrangThai.THANH_CONG, CoHoiKinhDoanh.TrangThai.THAT_BAI])
        won_no_contract = qs.filter(trang_thai=CoHoiKinhDoanh.TrangThai.THANH_CONG, hop_dong__isnull=True).count()
        stats = {
            'total': total,
            'open': open_qs.count(),
            'quoted': qs.filter(trang_thai=CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA).count(),
            'negotiating': qs.filter(trang_thai=CoHoiKinhDoanh.TrangThai.THUONG_LUONG).count(),
            'won': qs.filter(trang_thai=CoHoiKinhDoanh.TrangThai.THANH_CONG).count(),
            'lost': qs.filter(trang_thai=CoHoiKinhDoanh.TrangThai.THAT_BAI).count(),
            'missing_owner': qs.filter(nguoi_phu_trach__isnull=True).count(),
            'won_no_contract': won_no_contract,
            'pipeline_value': open_qs.aggregate(total=Sum('gia_tri_uoc_tinh'))['total'] or 0,
        }
        links = {
            'add_opportunity': _safe_reverse('admin:clients_cohoikinhdoanh_add'),
            'lead_list': _safe_reverse('admin:clients_khachhangtiemnang_changelist'),
            'add_lead': _safe_reverse('admin:clients_khachhangtiemnang_add'),
            'contract_list': _safe_reverse('admin:clients_hopdong_changelist'),
            'add_contract': _safe_reverse('admin:clients_hopdong_add'),
            'crm_dashboard': _safe_reverse('clients:dashboard_crm'),
            'pipeline': _safe_reverse('clients:pipeline'),
        }
        context = {
            'scmd_opportunity_stats': stats,
            'scmd_opportunity_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def opportunity_identity(self, obj):
        url = _admin_change_url(obj, 'admin:clients_cohoikinhdoanh_change')
        return format_html(
            '<div class="scmd-opp-cell"><a class="scmd-opp-main" href="{}">{}</a><span>{}</span></div>',
            url,
            obj.ten_co_hoi,
            f"Tạo ngày {self.ngay_tao_vn(obj)}" if obj.ngay_tao else "Chưa rõ ngày tạo",
        )
    opportunity_identity.short_description = "Cơ hội"
    opportunity_identity.admin_order_field = 'ten_co_hoi'

    def customer_summary(self, obj):
        customer = obj.khach_hang_tiem_nang
        if not customer:
            return format_html('<span class="scmd-opp-warning">Chưa gắn khách hàng</span>')
        url = _admin_change_url(customer, 'admin:clients_khachhangtiemnang_change')
        contact_bits = []
        if customer.nguoi_lien_he:
            contact_bits.append(customer.nguoi_lien_he)
        if customer.sdt:
            contact_bits.append(customer.sdt)
        contact_text = " · ".join(contact_bits) if contact_bits else "Thiếu đầu mối liên hệ"
        return format_html(
            '<div class="scmd-opp-cell"><a class="scmd-opp-main" href="{}">{}</a><span>{}</span></div>',
            url,
            customer.ten_cong_ty,
            contact_text,
        )
    customer_summary.short_description = "Khách hàng"
    customer_summary.admin_order_field = 'khach_hang_tiem_nang__ten_cong_ty'

    def owner_summary(self, obj):
        owner = obj.nguoi_phu_trach
        if not owner:
            return format_html('<span class="scmd-opp-pill scmd-opp-pill-warning">Chưa phân công</span>')
        label = getattr(owner, 'ho_ten', None) or str(owner)
        code = getattr(owner, 'ma_nv', '') or ''
        return format_html('<div class="scmd-opp-cell"><strong>{}</strong><span>{}</span></div>', label, code)
    owner_summary.short_description = "Sales phụ trách"
    owner_summary.admin_order_field = 'nguoi_phu_trach__ho_ten'

    def show_gia_tri(self, obj):
        val = obj.gia_tri_uoc_tinh or 0
        if val <= 0:
            return format_html('<span class="scmd-opp-pill scmd-opp-pill-warning">Chưa nhập</span>')
        return format_html('<span class="scmd-opp-money">{} ₫</span>', f'{val:,.0f}')
    show_gia_tri.short_description = "Giá trị"
    show_gia_tri.admin_order_field = 'gia_tri_uoc_tinh'

    def show_trang_thai(self, obj):
        if not obj.trang_thai:
            return "-"
        return format_html_status(obj.get_trang_thai_display(), obj.trang_thai)
    show_trang_thai.short_description = "Giai đoạn"
    show_trang_thai.admin_order_field = 'trang_thai'

    def row_actions(self, obj):
        change_url = _admin_change_url(obj, 'admin:clients_cohoikinhdoanh_change')
        contract_add_url = _safe_reverse('admin:clients_hopdong_add')
        customer_url = _admin_change_url(obj.khach_hang_tiem_nang, 'admin:clients_khachhangtiemnang_change') if obj.khach_hang_tiem_nang_id else '#'
        contract_cta = ''
        if obj.trang_thai == CoHoiKinhDoanh.TrangThai.THANH_CONG:
            contract_cta = format_html('<a class="button scmd-admin-mini-button scmd-admin-mini-button-success" href="{}?co_hoi={}">Hợp đồng</a>', contract_add_url, obj.pk)
        return format_html(
            '<div class="scmd-admin-actions"><a class="button scmd-admin-mini-button" href="{}">Sửa</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}">Lead</a>{}</div>',
            change_url,
            customer_url,
            contract_cta,
        )
    row_actions.short_description = "Thao tác"

    def ngay_tao_vn(self, obj):
        return obj.ngay_tao.strftime('%d/%m/%Y') if obj.ngay_tao else "-"
    ngay_tao_vn.short_description = "Ngày tạo"
    ngay_tao_vn.admin_order_field = 'ngay_tao'

    def mark_as_contacting(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='CoHoiKinhDoanh', target_status=CoHoiKinhDoanh.TrangThai.LIEN_HE, note='Admin opportunity status to LIEN_HE')
        self.message_user(request, f"Đã chuyển {updated} cơ hội sang Đang liên hệ.")
    mark_as_contacting.short_description = "Chuyển sang Đang liên hệ"

    def mark_as_quoted(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='CoHoiKinhDoanh', target_status=CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA, note='Admin opportunity status to GUI_BAO_GIA')
        self.message_user(request, f"Đã chuyển {updated} cơ hội sang Đã báo giá.")
    mark_as_quoted.short_description = "Chuyển sang Đã báo giá"

    def mark_as_negotiating(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='CoHoiKinhDoanh', target_status=CoHoiKinhDoanh.TrangThai.THUONG_LUONG, note='Admin opportunity status to THUONG_LUONG')
        self.message_user(request, f"Đã chuyển {updated} cơ hội sang Đang thương thảo.")
    mark_as_negotiating.short_description = "Chuyển sang Đang thương thảo"

    def mark_as_won(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='CoHoiKinhDoanh', target_status=CoHoiKinhDoanh.TrangThai.THANH_CONG, note='Admin opportunity status to THANH_CONG')
        self.message_user(request, f"Đã đánh dấu {updated} cơ hội là Chốt hợp đồng/Thắng.")
    mark_as_won.short_description = "Đánh dấu Chốt hợp đồng"

    def mark_as_lost(self, request, queryset):
        updated = _apply_client_status_action(request, queryset, model_name='CoHoiKinhDoanh', target_status=CoHoiKinhDoanh.TrangThai.THAT_BAI, note='Admin opportunity status to THAT_BAI')
        self.message_user(request, f"Đã đánh dấu {updated} cơ hội là Thất bại/Thua.")
    mark_as_lost.short_description = "Đánh dấu Thất bại"

# --- 3. HỢP ĐỒNG ---
class MucTieuInline(admin.StackedInline):
    model = MucTieu
    extra = 0
    classes = ['collapse']
    verbose_name = "Mục tiêu bảo vệ"
    verbose_name_plural = "📍 DANH SÁCH MỤC TIÊU THUỘC HỢP ĐỒNG"

class MucTieuDonGiaHistoryInline(admin.TabularInline):
    model = MucTieuDonGiaHistory
    extra = 0
    fields = ['ngay_hieu_luc', 'luong_khoan_bao_ve', 'so_gio_mot_ngay', 'ghi_chu', 'created_at']
    readonly_fields = ['created_at']



class PhuLucHopDongDichVuInline(admin.TabularInline):
    model = PhuLucHopDongDichVu
    extra = 0
    fields = ("so_phu_luc", "loai_phu_luc", "ngay_hieu_luc", "ngay_het_han", "trang_thai", "gia_tri_dieu_chinh")


class BienBanNghiemThuInline(admin.TabularInline):
    model = BienBanNghiemThu
    extra = 0
    fields = ("so_bien_ban", "tu_ngay", "den_ngay", "ngay_lap", "tong_gia_tri_nghiem_thu", "trang_thai")


class HoaDonInline(admin.TabularInline):
    model = HoaDon
    extra = 0
    fields = ("so_hoa_don", "ngay_phat_hanh", "ngay_den_han", "tong_tien", "trang_thai")


@admin.register(HopDong)
class HopDongAdmin(admin.ModelAdmin):
    """Admin hợp đồng dịch vụ bảo vệ.

    Mục tiêu: hỗ trợ admin/kế hoạch kinh doanh rà soát nhanh hợp đồng hiệu lực,
    hợp đồng sắp hết hạn, hồ sơ thiếu file, hợp đồng chưa có mục tiêu triển khai
    và liên kết ngược sang lead/pipeline/mục tiêu mà không phá chức năng admin gốc.
    """
    change_list_template = "admin/clients/hopdong/change_list.html"
    list_display = [
        'contract_identity',
        'customer_summary',
        'contract_value',
        'contract_period',
        'target_summary',
        'show_trang_thai',
        'row_actions',
    ]
    list_filter = [
        'trang_thai',
        HopDongQualityFilter,
        ('ngay_het_han', admin.DateFieldListFilter),
        ('ngay_hieu_luc', admin.DateFieldListFilter),
    ]
    search_fields = [
        'so_hop_dong',
        'khach_hang_cu__ten_cong_ty',
        'khach_hang_cu__nguoi_lien_he',
        'khach_hang_cu__sdt',
        'co_hoi__ten_co_hoi',
        'cac_muc_tieu__ten_muc_tieu',
    ]
    inlines = [MucTieuInline, PhuLucHopDongDichVuInline, BienBanNghiemThuInline, HoaDonInline]
    autocomplete_fields = ['khach_hang_cu', 'co_hoi']
    save_on_top = True
    list_per_page = 50
    search_help_text = "Tìm theo số hợp đồng, khách hàng, người liên hệ, SĐT, cơ hội hoặc mục tiêu."
    actions = ['mark_as_active', 'mark_as_expiring', 'mark_as_closed']

    fieldsets = (
        ("Thông tin hợp đồng", {
            'description': "Hợp đồng là điểm chuyển từ CRM sang vận hành mục tiêu, ca trực, đối soát và lương.",
            'fields': (
                'so_hop_dong',
                'trang_thai',
                'khach_hang_cu',
                'co_hoi',
                'gia_tri',
                'file_hop_dong'
            )
        }),
        ("Thời hạn và hiệu lực", {
            'fields': (
                'ngay_ky',
                'ngay_hieu_luc',
                'ngay_het_han'
            )
        }),
    )


    def save_model(self, request, obj, form, change):
        obj._audit_user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('khach_hang_cu', 'co_hoi')
            .annotate(_target_count=Count('cac_muc_tieu', distinct=True))
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        next_30 = today + timezone.timedelta(days=30)
        active_qs = qs.filter(trang_thai='HIEU_LUC')
        expiring_qs = qs.filter(ngay_het_han__gte=today, ngay_het_han__lte=next_30).exclude(trang_thai='DA_THANH_LY')
        stats = {
            'total': qs.count(),
            'active': active_qs.count(),
            'expiring_30': expiring_qs.count(),
            'expired_by_date': qs.filter(ngay_het_han__lt=today).exclude(trang_thai='DA_THANH_LY').count(),
            'closed': qs.filter(trang_thai='DA_THANH_LY').count(),
            'missing_file': qs.filter(Q(file_hop_dong__isnull=True) | Q(file_hop_dong='')).count(),
            'no_targets': qs.annotate(_stats_target_count=Count('cac_muc_tieu', distinct=True)).filter(_stats_target_count=0).count(),
            'monthly_value': active_qs.aggregate(total=Sum('gia_tri'))['total'] or 0,
        }
        links = {
            'add_contract': _safe_reverse('admin:clients_hopdong_add'),
            'lead_list': _safe_reverse('admin:clients_khachhangtiemnang_changelist'),
            'opportunity_list': _safe_reverse('admin:clients_cohoikinhdoanh_changelist'),
            'target_list': _safe_reverse('admin:clients_muctieu_changelist'),
            'add_target': _safe_reverse('admin:clients_muctieu_add'),
            'crm_dashboard': _safe_reverse('clients:dashboard_crm'),
            'pipeline': _safe_reverse('clients:pipeline'),
        }
        context = {
            'scmd_contract_stats': stats,
            'scmd_contract_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def contract_identity(self, obj):
        url = _admin_change_url(obj, 'admin:clients_hopdong_change')
        file_badge = ''
        if not obj.file_hop_dong:
            file_badge = '<span class="scmd-contract-warning">Thiếu file</span>'
        return format_html(
            '<div class="scmd-contract-cell"><a class="scmd-contract-main" href="{}">{}</a><span>Ngày ký: {}</span>{}</div>',
            url,
            obj.so_hop_dong,
            self.ngay_ky_vn(obj),
            format_html(file_badge) if file_badge else '',
        )
    contract_identity.short_description = "Hợp đồng"
    contract_identity.admin_order_field = 'so_hop_dong'

    def customer_summary(self, obj):
        customer = obj.khach_hang_cu
        if not customer:
            return format_html('<span class="scmd-contract-warning">Chưa gắn khách hàng</span>')
        url = _admin_change_url(customer, 'admin:clients_khachhangtiemnang_change')
        bits = []
        if customer.nguoi_lien_he:
            bits.append(customer.nguoi_lien_he)
        if customer.sdt:
            bits.append(customer.sdt)
        sub = ' · '.join(bits) if bits else 'Thiếu đầu mối liên hệ'
        return format_html(
            '<div class="scmd-contract-cell"><a class="scmd-contract-main" href="{}">{}</a><span>{}</span></div>',
            url,
            customer.ten_cong_ty,
            sub,
        )
    customer_summary.short_description = "Khách hàng"
    customer_summary.admin_order_field = 'khach_hang_cu__ten_cong_ty'

    def contract_value(self, obj):
        val = obj.gia_tri or 0
        if val <= 0:
            return format_html('<span class="scmd-contract-pill scmd-contract-pill-warning">Chưa nhập</span>')
        return format_html('<span class="scmd-contract-money">{} ₫/tháng</span>', f'{val:,.0f}')
    contract_value.short_description = "Giá trị"
    contract_value.admin_order_field = 'gia_tri'

    def contract_period(self, obj):
        today = timezone.localdate()
        end = obj.ngay_het_han
        if not end:
            return format_html('<span class="scmd-contract-warning">Thiếu ngày hết hạn</span>')
        remaining_days = (end - today).days
        if remaining_days < 0 and obj.trang_thai != 'DA_THANH_LY':
            status = format_html('<span class="scmd-contract-warning">Quá hạn {} ngày</span>', abs(remaining_days))
        elif remaining_days <= 30 and obj.trang_thai != 'DA_THANH_LY':
            status = format_html('<span class="scmd-contract-pill scmd-contract-pill-warning">Còn {} ngày</span>', remaining_days)
        else:
            status = format_html('<span class="scmd-contract-pill">Còn {} ngày</span>', remaining_days)
        return format_html(
            '<div class="scmd-contract-cell"><strong>{} → {}</strong>{}</div>',
            self.ngay_hieu_luc_vn(obj),
            self.ngay_het_han_vn(obj),
            status,
        )
    contract_period.short_description = "Thời hạn"
    contract_period.admin_order_field = 'ngay_het_han'

    def target_summary(self, obj):
        count = getattr(obj, '_target_count', None)
        if count is None:
            count = obj.cac_muc_tieu.count()
        target_url = _safe_reverse('admin:clients_muctieu_changelist')
        if count == 0:
            return format_html('<a class="scmd-contract-pill scmd-contract-pill-warning" href="{}?hop_dong__id__exact={}">Chưa có mục tiêu</a>', target_url, obj.pk)
        return format_html('<a class="scmd-contract-pill scmd-contract-pill-info" href="{}?hop_dong__id__exact={}">{} mục tiêu</a>', target_url, obj.pk, count)
    target_summary.short_description = "Mục tiêu"

    def row_actions(self, obj):
        change_url = _admin_change_url(obj, 'admin:clients_hopdong_change')
        target_url = _safe_reverse('admin:clients_muctieu_changelist')
        add_target_url = _safe_reverse('admin:clients_muctieu_add')
        customer_url = _admin_change_url(obj.khach_hang_cu, 'admin:clients_khachhangtiemnang_change') if obj.khach_hang_cu_id else '#'
        file_link = ''
        if obj.file_hop_dong:
            file_link = format_html('<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}" target="_blank" rel="noopener">File</a>', obj.file_hop_dong.url)
        return format_html(
            '<div class="scmd-admin-actions">'
            '<a class="button scmd-admin-mini-button" href="{}">Sửa</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}?hop_dong__id__exact={}">Mục tiêu</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-success" href="{}?hop_dong={}">Thêm MT</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}">Khách hàng</a>{}'
            '</div>',
            change_url,
            target_url,
            obj.pk,
            add_target_url,
            obj.pk,
            customer_url,
            file_link,
        )
    row_actions.short_description = "Thao tác"

    def khach_hang_info(self, obj):
        return obj.khach_hang_cu.ten_cong_ty if obj.khach_hang_cu else "---"
    khach_hang_info.short_description = "Tên khách hàng"

    def show_trang_thai(self, obj):
        if not obj.trang_thai:
            return "-"
        return format_html_status(obj.get_trang_thai_display(), obj.trang_thai)
    show_trang_thai.short_description = "Trạng thái"
    show_trang_thai.admin_order_field = 'trang_thai'

    def ngay_ky_vn(self, obj):
        return obj.ngay_ky.strftime('%d/%m/%Y') if obj.ngay_ky else "-"
    ngay_ky_vn.short_description = "Ngày ký"
    ngay_ky_vn.admin_order_field = 'ngay_ky'

    def ngay_hieu_luc_vn(self, obj):
        return obj.ngay_hieu_luc.strftime('%d/%m/%Y') if obj.ngay_hieu_luc else "-"
    ngay_hieu_luc_vn.short_description = "Ngày hiệu lực"
    ngay_hieu_luc_vn.admin_order_field = 'ngay_hieu_luc'

    def ngay_het_han_vn(self, obj):
        return obj.ngay_het_han.strftime('%d/%m/%Y') if obj.ngay_het_han else "-"
    ngay_het_han_vn.short_description = "Ngày hết hạn"
    ngay_het_han_vn.admin_order_field = 'ngay_het_han'

    def _bulk_mark_status(self, request, queryset, target_status, success_label):
        """Apply contract status changes through model save(), not queryset bulk update.

        Contract status is guarded by ``ContractTransitionPolicy`` and audited in
        ``HopDong.save()``. Bulk admin actions must therefore never bypass
        ``save()`` with direct ``queryset bulk update`` calls.
        """
        updated = 0
        failed = 0
        with transaction.atomic():
            for contract in queryset.select_for_update():
                if contract.trang_thai == target_status:
                    continue
                contract._audit_user = request.user
                contract.trang_thai = target_status
                try:
                    contract.save(update_fields=["trang_thai"])
                    updated += 1
                except Exception as exc:  # pragma: no cover - surfaced through admin message
                    failed += 1
                    self.message_user(
                        request,
                        f"Không thể chuyển hợp đồng {contract.so_hop_dong}: {exc}",
                        level=messages.ERROR,
                    )
        if updated:
            self.message_user(request, f"Đã chuyển {updated} hợp đồng sang {success_label}.")
        if failed and not updated:
            self.message_user(request, "Không có hợp đồng nào được chuyển trạng thái.", level=messages.WARNING)

    def mark_as_active(self, request, queryset):
        self._bulk_mark_status(request, queryset, 'HIEU_LUC', 'Đang hiệu lực')
    mark_as_active.short_description = "Chuyển sang Đang hiệu lực"

    def mark_as_expiring(self, request, queryset):
        self._bulk_mark_status(request, queryset, 'SAP_HET_HAN', 'Sắp hết hạn')
    mark_as_expiring.short_description = "Chuyển sang Sắp hết hạn"

    def mark_as_closed(self, request, queryset):
        self._bulk_mark_status(request, queryset, 'DA_THANH_LY', 'Đã thanh lý/Hết hạn')
    mark_as_closed.short_description = "Chuyển sang Đã thanh lý/Hết hạn"

# --- 4. MỤC TIÊU ---
class MucTieuQualityFilter(admin.SimpleListFilter):
    title = "Chất lượng mục tiêu"
    parameter_name = "target_quality"

    def lookups(self, request, model_admin):
        return (
            ("missing_gps", "Thiếu tọa độ GPS"),
            ("missing_manager", "Chưa có chỉ huy trưởng"),
            ("missing_contact", "Thiếu đầu mối/SĐT"),
            ("no_posts", "Chưa có chốt trực"),
            ("no_routes", "Chưa có tuyến tuần tra"),
            ("zero_payroll", "Chưa cấu hình lương"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing_gps":
            return queryset.filter(Q(vi_do__isnull=True) | Q(kinh_do__isnull=True))
        if value == "missing_manager":
            return queryset.filter(quan_ly_muc_tieu__isnull=True)
        if value == "missing_contact":
            return queryset.filter(
                Q(nguoi_lien_he__isnull=True) | Q(nguoi_lien_he="") |
                Q(sdt_lien_he__isnull=True) | Q(sdt_lien_he="")
            )
        if value == "no_posts":
            return queryset.annotate(_target_post_count=Count("cac_vi_tri_chot", distinct=True)).filter(_target_post_count=0)
        if value == "no_routes":
            return queryset.annotate(_target_route_count=Count("loaituantra", distinct=True)).filter(_target_route_count=0)
        if value == "zero_payroll":
            return queryset.filter(Q(luong_khoan_bao_ve__isnull=True) | Q(luong_khoan_bao_ve=0))
        return queryset



@admin.register(PhuLucHopDongDichVu)
class PhuLucHopDongDichVuAdmin(admin.ModelAdmin):
    list_display = ("so_phu_luc", "hop_dong", "loai_phu_luc", "ngay_hieu_luc", "ngay_het_han", "trang_thai", "gia_tri_dieu_chinh")
    list_filter = ("trang_thai", "loai_phu_luc", ("ngay_hieu_luc", admin.DateFieldListFilter), ("ngay_het_han", admin.DateFieldListFilter))
    search_fields = ("so_phu_luc", "hop_dong__so_hop_dong", "ghi_chu")
    autocomplete_fields = ("hop_dong", "nguoi_duyet")
    list_select_related = ("hop_dong", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = PhuLucHopDongDichVu.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == PhuLucHopDongDichVu.TrangThai.ACTIVE and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin service appendix status save")


@admin.register(BienBanNghiemThu)
class BienBanNghiemThuAdmin(admin.ModelAdmin):
    list_display = ("so_bien_ban", "hop_dong", "muc_tieu", "tu_ngay", "den_ngay", "tong_gia_tri_nghiem_thu", "trang_thai")
    list_filter = ("trang_thai", ("ngay_lap", admin.DateFieldListFilter), ("tu_ngay", admin.DateFieldListFilter))
    search_fields = ("so_bien_ban", "hop_dong__so_hop_dong", "muc_tieu__ten_muc_tieu")
    autocomplete_fields = ("hop_dong", "muc_tieu", "nguoi_duyet")
    list_select_related = ("hop_dong", "muc_tieu", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = BienBanNghiemThu.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == BienBanNghiemThu.TrangThai.SIGNED and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin acceptance report status save")


class CongNoInline(admin.TabularInline):
    model = CongNo
    extra = 0
    fields = ("so_tham_chieu", "ngay_den_han", "so_tien_phai_thu", "so_tien_da_thu", "so_tien_con_lai", "trang_thai")
    readonly_fields = ("so_tien_da_thu", "so_tien_con_lai", "trang_thai")


class PhanBoThanhToanHoaDonInline(admin.TabularInline):
    model = PhanBoThanhToanHoaDon
    extra = 0
    can_delete = False
    fields = ("hoa_don", "cong_no", "so_tien", "ngay_phan_bo", "nguoi_phan_bo", "ghi_chu")
    readonly_fields = ("ngay_phan_bo", "nguoi_phan_bo")
    autocomplete_fields = ("hoa_don", "cong_no")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        # Existing allocation rows are protected by save_formset immutability guard.
        # Keep only evidence/audit fields readonly globally so new allocations can
        # still be added from the payment page.
        return self.readonly_fields


@admin.register(HoaDon)
class HoaDonAdmin(admin.ModelAdmin):
    list_display = ("so_hoa_don", "hop_dong", "bien_ban", "ngay_phat_hanh", "ngay_den_han", "tong_tien", "so_tien_da_thu_display", "so_tien_con_lai_display", "trang_thai")
    list_filter = ("trang_thai", "hop_dong", ("ngay_phat_hanh", admin.DateFieldListFilter), ("ngay_den_han", admin.DateFieldListFilter))
    search_fields = ("so_hoa_don", "hop_dong__so_hop_dong", "hop_dong__khach_hang_cu__ten_cong_ty", "bien_ban__so_bien_ban")
    autocomplete_fields = ("hop_dong", "bien_ban")
    list_select_related = ("hop_dong", "hop_dong__khach_hang_cu", "bien_ban")
    readonly_fields = ("created_at", "updated_at", "so_tien_da_thu_display", "so_tien_con_lai_display")
    inlines = [CongNoInline]
    save_on_top = True

    def so_tien_da_thu_display(self, obj):
        return f"{obj.so_tien_da_thu_tu_phan_bo:,.0f} ₫" if obj and obj.pk else "0 ₫"
    so_tien_da_thu_display.short_description = "Đã thu từ phân bổ"

    def so_tien_con_lai_display(self, obj):
        return f"{obj.so_tien_con_lai:,.0f} ₫" if obj and obj.pk else "0 ₫"
    so_tien_con_lai_display.short_description = "Còn phải thu"

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = HoaDon.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
            if obj.trang_thai == HoaDon.TrangThai.PAID and obj.so_tien_da_thu_tu_phan_bo < obj.tong_tien:
                raise ValidationError("Không được chuyển hóa đơn sang PAID khi chưa có phân bổ thanh toán đủ tiền.")
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin invoice status save")


@admin.register(CongNo)
class CongNoAdmin(admin.ModelAdmin):
    list_display = ("so_tham_chieu", "hoa_don", "ngay_den_han", "so_tien_phai_thu", "so_tien_da_thu", "so_tien_con_lai", "trang_thai")
    list_filter = ("trang_thai", "hoa_don__hop_dong", ("ngay_den_han", admin.DateFieldListFilter))
    search_fields = ("so_tham_chieu", "hoa_don__so_hoa_don", "hoa_don__hop_dong__so_hop_dong", "hoa_don__hop_dong__khach_hang_cu__ten_cong_ty")
    autocomplete_fields = ("hoa_don",)
    list_select_related = ("hoa_don", "hoa_don__hop_dong", "hoa_don__hop_dong__khach_hang_cu")
    readonly_fields = ("created_at", "updated_at", "so_tien_da_thu", "so_tien_con_lai")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = CongNo.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
            if obj.trang_thai == CongNo.TrangThai.PAID and obj.so_tien_da_thu < obj.so_tien_phai_thu:
                raise ValidationError("Không được chuyển công nợ sang PAID khi chưa có phân bổ thanh toán đủ tiền.")
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin receivable status save")


@admin.register(ThanhToanKhachHang)
class ThanhToanKhachHangAdmin(admin.ModelAdmin):
    list_display = ("ma_phieu", "khach_hang", "hop_dong", "ngay_thanh_toan", "so_tien", "so_tien_da_phan_bo_display", "so_tien_chua_phan_bo_display", "hinh_thuc", "trang_thai")
    list_filter = ("trang_thai", "hinh_thuc", "hop_dong", "khach_hang", ("ngay_thanh_toan", admin.DateFieldListFilter))
    search_fields = ("ma_phieu", "ma_giao_dich", "hop_dong__so_hop_dong", "khach_hang__ten_cong_ty", "ghi_chu")
    autocomplete_fields = ("khach_hang", "hop_dong", "nguoi_ghi_nhan", "nguoi_duyet")
    list_select_related = ("khach_hang", "hop_dong", "nguoi_ghi_nhan", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet", "so_tien_da_phan_bo_display", "so_tien_chua_phan_bo_display")
    inlines = [PhanBoThanhToanHoaDonInline]
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk and obj.cac_phan_bo.exists():
            fields.extend([
                "ma_phieu",
                "so_tien",
                "khach_hang",
                "hop_dong",
                "ngay_thanh_toan",
                "hinh_thuc",
                "ma_giao_dich",
                "file_chung_tu",
            ])
        return tuple(dict.fromkeys(fields))

    def so_tien_da_phan_bo_display(self, obj):
        return f"{obj.so_tien_da_phan_bo:,.0f} ₫" if obj and obj.pk else "0 ₫"
    so_tien_da_phan_bo_display.short_description = "Đã phân bổ"

    def so_tien_chua_phan_bo_display(self, obj):
        return f"{obj.so_tien_chua_phan_bo:,.0f} ₫" if obj and obj.pk else "0 ₫"
    so_tien_chua_phan_bo_display.short_description = "Chưa phân bổ"

    def save_model(self, request, obj, form, change):
        CustomerPaymentPermissionPolicy.enforce_receive(request.user)
        old_status = None
        existing = None
        if change and obj.pk:
            existing = ThanhToanKhachHang.objects.filter(pk=obj.pk).first()
            old_status = existing.trang_thai if existing else None
            _assert_payment_allocation_immutable(existing, obj)
        if obj.trang_thai in (ThanhToanKhachHang.TrangThai.RECEIVED, ThanhToanKhachHang.TrangThai.ALLOCATED) and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
            if obj.trang_thai == ThanhToanKhachHang.TrangThai.CANCELLED and obj.cac_phan_bo.exists():
                raise ValidationError("Không được hủy thanh toán đã phân bổ trong admin. Cần recovery path/reversal riêng.")
            if obj.trang_thai == ThanhToanKhachHang.TrangThai.ALLOCATED and obj.so_tien_da_phan_bo <= 0:
                raise ValidationError("Không được chuyển thanh toán sang ALLOCATED khi chưa có phân bổ.")
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin customer payment status save")

    def save_formset(self, request, form, formset, change):
        CustomerPaymentPermissionPolicy.enforce_allocate(request.user)
        instances = formset.save(commit=False)
        if formset.deleted_objects:
            raise ValidationError("Không được xóa phân bổ thanh toán trực tiếp trong admin. Cần recovery/reversal path riêng.")
        for obj in instances:
            if isinstance(obj, PhanBoThanhToanHoaDon):
                existing = PhanBoThanhToanHoaDon.objects.filter(pk=obj.pk).first() if obj.pk else None
                _assert_allocation_source_immutable(existing, obj)
                obj.nguoi_phan_bo = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
                obj.full_clean()
            obj.save()
            if isinstance(obj, PhanBoThanhToanHoaDon):
                obj.record_event(actor=request.user, note="Admin customer payment allocation save")
                if obj.thanh_toan.trang_thai == ThanhToanKhachHang.TrangThai.RECEIVED:
                    obj.thanh_toan.transition_status(ThanhToanKhachHang.TrangThai.ALLOCATED, actor=request.user, note="Admin allocation created")
                RecalculateReceivableStatusUseCase.execute(hoa_don=obj.hoa_don, cong_no=obj.cong_no, actor=request.user)
        formset.save_m2m()


@admin.register(PhanBoThanhToanHoaDon)
class PhanBoThanhToanHoaDonAdmin(admin.ModelAdmin):
    list_display = ("thanh_toan", "hoa_don", "cong_no", "so_tien", "ngay_phan_bo", "nguoi_phan_bo")
    list_filter = (("ngay_phan_bo", admin.DateFieldListFilter), "thanh_toan__trang_thai", "hoa_don__hop_dong")
    search_fields = ("thanh_toan__ma_phieu", "hoa_don__so_hoa_don", "cong_no__so_tham_chieu", "hoa_don__hop_dong__so_hop_dong")
    autocomplete_fields = ("thanh_toan", "hoa_don", "cong_no", "nguoi_phan_bo")
    list_select_related = ("thanh_toan", "hoa_don", "cong_no", "nguoi_phan_bo")
    readonly_fields = ("ngay_phan_bo", "created_at", "updated_at")
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk:
            fields.extend(["thanh_toan", "hoa_don", "cong_no", "so_tien", "ghi_chu", "nguoi_phan_bo"])
        return tuple(dict.fromkeys(fields))

    def save_model(self, request, obj, form, change):
        CustomerPaymentPermissionPolicy.enforce_allocate(request.user)
        if change and obj.pk:
            existing = PhanBoThanhToanHoaDon.objects.filter(pk=obj.pk).first()
            _assert_allocation_source_immutable(existing, obj)
        if not obj.nguoi_phan_bo_id:
            obj.nguoi_phan_bo = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        obj.full_clean()
        super().save_model(request, obj, form, change)
        obj.record_event(actor=request.user, note="Admin customer payment allocation save")
        if obj.thanh_toan.trang_thai == ThanhToanKhachHang.TrangThai.RECEIVED:
            obj.thanh_toan.transition_status(ThanhToanKhachHang.TrangThai.ALLOCATED, actor=request.user, note="Admin allocation created")
        RecalculateReceivableStatusUseCase.execute(hoa_don=obj.hoa_don, cong_no=obj.cong_no, actor=request.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        raise ValidationError("Không được xóa phân bổ thanh toán trực tiếp. Cần recovery/reversal path riêng.")

    def delete_queryset(self, request, queryset):
        raise ValidationError("Không được xóa phân bổ thanh toán trực tiếp. Cần recovery/reversal path riêng.")


@admin.register(MucTieu)
class MucTieuAdmin(admin.ModelAdmin):
    """Admin mục tiêu bảo vệ.

    Mục tiêu là điểm nối từ hợp đồng sang vận hành: vị trí chốt, ca trực,
    GPS/check-in, tuần tra, kho cấp phát và payroll. List view chỉ đưa những
    thông tin cần quyết định nhanh; chi tiết vẫn nằm ở form sửa mục tiêu.
    """
    change_list_template = "admin/clients/muctieu/change_list.html"
    list_display = [
        'target_identity',
        'contract_customer_summary',
        'operations_summary',
        'payroll_summary',
        'gps_summary',
        'row_actions',
    ]
    list_filter = [
        MucTieuQualityFilter,
        'quan_ly_muc_tieu',
        'so_gio_mot_ngay',
        'hop_dong__trang_thai',
    ]
    search_fields = [
        'ten_muc_tieu',
        'dia_chi',
        'nguoi_lien_he',
        'sdt_lien_he',
        'hop_dong__so_hop_dong',
        'hop_dong__khach_hang_cu__ten_cong_ty',
        'quan_ly_muc_tieu__ho_ten',
        'quan_ly_muc_tieu__ma_nv',
    ]
    autocomplete_fields = ['hop_dong', 'quan_ly_muc_tieu']
    save_on_top = True
    list_per_page = 50
    inlines = [MucTieuDonGiaHistoryInline]
    search_help_text = "Tìm theo tên mục tiêu, địa chỉ, hợp đồng, khách hàng, đầu mối liên hệ hoặc chỉ huy trưởng."

    class Media:
        css = {'all': ('common/css/custom_admin.css', 'css/admin_tweaks.css')}

    formfield_overrides = {
        models.FloatField: {'widget': NumberInput(attrs={'class': 'fix-gps-input', 'step': '0.000001'})},
        models.IntegerField: {'widget': NumberInput(attrs={'class': 'fix-num-input'})},
        models.DecimalField: {'widget': NumberInput(attrs={'class': 'fix-money-input'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'style': 'width: 100%;'})},
    }

    fieldsets = (
        ("Cơ bản", {
            'description': "Thông tin định danh mục tiêu và người phụ trách triển khai vận hành.",
            'fields': (
                'hop_dong',
                'ten_muc_tieu',
                'quan_ly_muc_tieu',
                'so_luong_nhan_vien',
                'dia_chi'
            )
        }),
        ("Cấu hình GPS", {
            'description': "Tọa độ và bán kính kiểm soát dùng cho check-in/check-out, tuần tra và đối soát GPS.",
            'fields': (
                'vi_do',
                'kinh_do',
                'ban_kinh_cho_phep'
            )
        }),
        ("Chế độ và lương", {
            'description': "Thông số này ảnh hưởng trực tiếp đến tính lương, chuyên cần và khấu trừ. Cần đối soát trước khi khóa kỳ lương.",
            'fields': (
                'luong_khoan_bao_ve',
                'so_gio_mot_ngay',
                'tien_chuyen_can',
                'tru_nghi_1_ngay',
                'tru_nghi_2_ngay',
                'tru_nghi_3_ngay'
            )
        }),
        ("Liên hệ tại mục tiêu", {
            'fields': (
                'nguoi_lien_he',
                'sdt_lien_he'
            )
        }),
    )

    def get_queryset(self, request):
        scoped_ids = SiteVisibilityPolicy.visible_sites(request.user).values_list("pk", flat=True)
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=scoped_ids)
            .select_related('hop_dong', 'hop_dong__khach_hang_cu', 'quan_ly_muc_tieu')
            .annotate(
                _post_count=Count('cac_vi_tri_chot', distinct=True),
                _route_count=Count('loaituantra', distinct=True),
            )
        )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return SiteVisibilityPolicy.visible_sites(request.user).filter(pk=obj.pk).exists()

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return SiteVisibilityPolicy.visible_sites(request.user).filter(pk=obj.pk).exists()

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in {"quan_ly_muc_tieu", "quan_ly_vung"}:
            kwargs["queryset"] = StaffVisibilityPolicy.visible_staff(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        annotated = qs.annotate(
            _stats_post_count=Count('cac_vi_tri_chot', distinct=True),
            _stats_route_count=Count('loaituantra', distinct=True),
        )
        stats = {
            'total': qs.count(),
            'with_gps': qs.filter(vi_do__isnull=False, kinh_do__isnull=False).count(),
            'missing_gps': qs.filter(Q(vi_do__isnull=True) | Q(kinh_do__isnull=True)).count(),
            'missing_manager': qs.filter(quan_ly_muc_tieu__isnull=True).count(),
            'missing_contact': qs.filter(
                Q(nguoi_lien_he__isnull=True) | Q(nguoi_lien_he='') |
                Q(sdt_lien_he__isnull=True) | Q(sdt_lien_he='')
            ).count(),
            'no_posts': annotated.filter(_stats_post_count=0).count(),
            'no_routes': annotated.filter(_stats_route_count=0).count(),
            'monthly_payroll': qs.aggregate(total=Sum('luong_khoan_bao_ve'))['total'] or 0,
        }
        links = {
            'add_target': _safe_reverse('admin:clients_muctieu_add'),
            'contract_list': _safe_reverse('admin:clients_hopdong_changelist'),
            'lead_list': _safe_reverse('admin:clients_khachhangtiemnang_changelist'),
            'opportunity_list': _safe_reverse('admin:clients_cohoikinhdoanh_changelist'),
            'post_list': _safe_reverse('admin:operations_vitrichot_changelist'),
            'add_post': _safe_reverse('admin:operations_vitrichot_add'),
            'route_list': _safe_reverse('admin:inspection_loaituantra_changelist'),
            'add_route': _safe_reverse('admin:inspection_loaituantra_add'),
            'shift_list': _safe_reverse('admin:operations_phancongcatruc_changelist'),
            'inventory_target_tools': _safe_reverse('inventory:cong_cu_muc_tieu'),
            'crm_dashboard': _safe_reverse('clients:dashboard_crm'),
        }
        context = {
            'scmd_target_stats': stats,
            'scmd_target_links': links,
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def target_identity(self, obj):
        url = _admin_change_url(obj, 'admin:clients_muctieu_change')
        address = obj.dia_chi or 'Chưa có địa chỉ'
        contact = []
        if obj.nguoi_lien_he:
            contact.append(obj.nguoi_lien_he)
        if obj.sdt_lien_he:
            contact.append(obj.sdt_lien_he)
        contact_text = ' · '.join(contact) if contact else 'Thiếu đầu mối liên hệ'
        return format_html(
            '<div class="scmd-target-cell"><a class="scmd-target-main" href="{}">{}</a><span>{}</span><span>{}</span></div>',
            url,
            obj.ten_muc_tieu,
            address,
            contact_text,
        )
    target_identity.short_description = "Mục tiêu"
    target_identity.admin_order_field = 'ten_muc_tieu'

    def contract_customer_summary(self, obj):
        contract = obj.hop_dong
        if not contract:
            return format_html('<span class="scmd-target-warning">Chưa gắn hợp đồng</span>')
        contract_url = _admin_change_url(contract, 'admin:clients_hopdong_change')
        customer = contract.khach_hang_cu
        customer_line = customer.ten_cong_ty if customer else 'Chưa gắn khách hàng'
        status = contract.get_trang_thai_display() if getattr(contract, 'trang_thai', None) else 'Chưa rõ trạng thái'
        return format_html(
            '<div class="scmd-target-cell"><a class="scmd-target-main" href="{}">{}</a><span>{}</span><span>{}</span></div>',
            contract_url,
            contract.so_hop_dong,
            customer_line,
            status,
        )
    contract_customer_summary.short_description = "Hợp đồng / khách hàng"
    contract_customer_summary.admin_order_field = 'hop_dong__so_hop_dong'

    def operations_summary(self, obj):
        manager = obj.quan_ly_muc_tieu
        manager_label = getattr(manager, 'ho_ten', None) or str(manager) if manager else 'Chưa phân công chỉ huy'
        posts = getattr(obj, '_post_count', 0)
        routes = getattr(obj, '_route_count', 0)
        return format_html(
            '<div class="scmd-target-cell"><strong>{}</strong><span>Định biên: {} người</span><span>{} chốt · {} tuyến</span></div>',
            manager_label,
            obj.so_luong_nhan_vien or 0,
            posts,
            routes,
        )
    operations_summary.short_description = "Vận hành"
    operations_summary.admin_order_field = 'quan_ly_muc_tieu__ho_ten'

    def payroll_summary(self, obj):
        salary = obj.luong_khoan_bao_ve or 0
        if salary <= 0:
            salary_html = format_html('<span class="scmd-target-pill scmd-target-pill-warning">Chưa cấu hình lương</span>')
        else:
            salary_html = format_html('<span class="scmd-target-money">{} ₫/tháng</span>', f'{salary:,.0f}')
        return format_html(
            '<div class="scmd-target-cell">{}<span>{} giờ/ngày · Chuyên cần {} ₫</span></div>',
            salary_html,
            obj.so_gio_mot_ngay or 0,
            f'{(obj.tien_chuyen_can or 0):,.0f}',
        )
    payroll_summary.short_description = "Lương / định mức"
    payroll_summary.admin_order_field = 'luong_khoan_bao_ve'

    def gps_summary(self, obj):
        has_gps = obj.vi_do is not None and obj.kinh_do is not None
        if has_gps:
            return format_html(
                '<div class="scmd-target-cell"><span class="scmd-target-pill scmd-target-pill-success">Đã cấu hình GPS</span><span>Bán kính {}m</span></div>',
                obj.ban_kinh_cho_phep or 0,
            )
        return format_html('<span class="scmd-target-pill scmd-target-pill-warning">Thiếu GPS</span>')
    gps_summary.short_description = "GPS"

    def row_actions(self, obj):
        change_url = _admin_change_url(obj, 'admin:clients_muctieu_change')
        contract_url = _admin_change_url(obj.hop_dong, 'admin:clients_hopdong_change') if obj.hop_dong_id else '#'
        post_url = _safe_reverse('admin:operations_vitrichot_changelist')
        add_post_url = _safe_reverse('admin:operations_vitrichot_add')
        route_url = _safe_reverse('admin:inspection_loaituantra_changelist')
        return format_html(
            '<div class="scmd-admin-actions">'
            '<a class="button scmd-admin-mini-button" href="{}">Sửa</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}">Hợp đồng</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}?muc_tieu__id__exact={}">Chốt</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-success" href="{}?muc_tieu={}">Thêm chốt</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}?muc_tieu__id__exact={}">Tuần tra</a>'
            '</div>',
            change_url,
            contract_url,
            post_url,
            obj.pk,
            add_post_url,
            obj.pk,
            route_url,
            obj.pk,
        )
    row_actions.short_description = "Thao tác"

    # Giữ lại tên method cũ để các template/custom surface đang gọi không bị vỡ.
    def hop_dong_link(self, obj):
        if obj.hop_dong:
            url = _admin_change_url(obj.hop_dong, 'admin:clients_hopdong_change')
            return format_html('<a href="{}" style="font-weight:bold;">{}</a>', url, obj.hop_dong.so_hop_dong)
        return "-"
    hop_dong_link.short_description = "Hợp đồng kinh tế"

    def co_gps(self, obj):
        return self.gps_summary(obj)
    co_gps.short_description = "Cấu hình GPS"
