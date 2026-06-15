# -*- coding: utf-8 -*-
"""
SCMD Pro - Inventory Module
--------------------------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: inventory/admin.py
Description: Cấu hình giao diện Admin cho module Quản lý Kho vật tư và Công cụ hỗ trợ.
Optimized for: SCMD Pro Inventory Admin
"""

import csv

from django.contrib import admin
from django.contrib.admin.helpers import ActionForm
from django.contrib import messages
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from inventory.access_policies import InventoryScopePolicy
from main.models import AuditLog
from main.services.audit_service import record_inventory_admin_audit_action

from inventory.access_policies import InventoryDocumentPolicy
from inventory.application.inventory_document_use_cases import (
    InventoryDocumentPostingError,
    InventoryDocumentUseCase,
)
from inventory.application.asset_recovery_use_cases import (
    ApproveAssetDamageReportUseCase,
    AssetRecoveryError,
    PostAssetRecoveryUseCase,
    VoidAssetRecoveryUseCase,
)
from inventory.application.asset_recovery_permission_policy import AssetRecoveryPermissionPolicy


class MaterialCategoryOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng danh mục"
    parameter_name = "category_issue"

    def lookups(self, request, model_admin):
        return (
            ("no_description", "Thiếu mô tả"),
            ("has_items", "Đã có vật tư"),
            ("empty", "Chưa có vật tư"),
            ("low_stock", "Có vật tư cảnh báo"),
            ("out_of_stock", "Có vật tư hết tồn"),
            ("target_tools", "Có công cụ tại mục tiêu"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "no_description":
            return queryset.filter(Q(mo_ta__isnull=True) | Q(mo_ta=""))
        if value == "has_items":
            return queryset.filter(vat_tu_count__gt=0)
        if value == "empty":
            return queryset.filter(vat_tu_count=0)
        if value == "low_stock":
            return queryset.filter(low_stock_count__gt=0)
        if value == "out_of_stock":
            return queryset.filter(out_of_stock_count__gt=0)
        if value == "target_tools":
            return queryset.filter(target_tool_count__gt=0)
        return queryset



class MaterialOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng vật tư"
    parameter_name = "material_issue"

    def lookups(self, request, model_admin):
        return (
            ("low_stock", "Dưới hoặc bằng mức cảnh báo"),
            ("out_of_stock", "Hết tồn"),
            ("healthy_stock", "Tồn kho an toàn"),
            ("no_category", "Thiếu phân loại"),
            ("missing_image", "Thiếu ảnh minh họa"),
            ("no_cost", "Thiếu giá vốn"),
            ("payroll_deductible", "Có giá trừ lương"),
            ("target_tools", "Đang bàn giao tại mục tiêu"),
            ("has_movement", "Đã phát sinh nhập/xuất"),
            ("no_movement", "Chưa phát sinh nhập/xuất"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "low_stock":
            return queryset.filter(so_luong_ton__lte=F("muc_canh_bao"))
        if value == "out_of_stock":
            return queryset.filter(so_luong_ton__lte=0)
        if value == "healthy_stock":
            return queryset.filter(so_luong_ton__gt=F("muc_canh_bao"))
        if value == "no_category":
            return queryset.filter(loai_vat_tu__isnull=True)
        if value == "missing_image":
            return queryset.filter(Q(hinh_anh__isnull=True) | Q(hinh_anh=""))
        if value == "no_cost":
            return queryset.filter(gia_nhap__lte=0)
        if value == "payroll_deductible":
            return queryset.filter(gia_ban__gt=0)
        if value == "target_tools":
            return queryset.filter(target_tool_count__gt=0)
        if value == "has_movement":
            return queryset.filter(Q(receipt_line_count__gt=0) | Q(issue_line_count__gt=0))
        if value == "no_movement":
            return queryset.filter(receipt_line_count=0, issue_line_count=0)
        return queryset


class TargetToolOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng CCHT tại mục tiêu"
    parameter_name = "target_tool_issue"

    def lookups(self, request, model_admin):
        return (
            ("zero_quantity", "Số lượng bằng 0"),
            ("active_quantity", "Đang giữ thực tế"),
            ("today_update", "Cập nhật hôm nay"),
            ("month_update", "Cập nhật tháng này"),
            ("material_low_stock", "Vật tư đang cảnh báo tồn"),
            ("material_out_stock", "Vật tư đã hết tồn"),
            ("no_material_category", "Vật tư thiếu phân loại"),
            ("payroll_deductible", "Có giá trừ lương"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()
        if value == "zero_quantity":
            return queryset.filter(so_luong_dang_giu__lte=0)
        if value == "active_quantity":
            return queryset.filter(so_luong_dang_giu__gt=0)
        if value == "today_update":
            return queryset.filter(ngay_cap_gan_nhat=today)
        if value == "month_update":
            return queryset.filter(ngay_cap_gan_nhat__year=today.year, ngay_cap_gan_nhat__month=today.month)
        if value == "material_low_stock":
            return queryset.filter(vat_tu__so_luong_ton__lte=F("vat_tu__muc_canh_bao"))
        if value == "material_out_stock":
            return queryset.filter(vat_tu__so_luong_ton__lte=0)
        if value == "no_material_category":
            return queryset.filter(vat_tu__loai_vat_tu__isnull=True)
        if value == "payroll_deductible":
            return queryset.filter(vat_tu__gia_ban__gt=0)
        return queryset


class ReceiptOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng phiếu nhập"
    parameter_name = "receipt_issue"

    def lookups(self, request, model_admin):
        return (
            ("draft", "Phiếu nháp"),
            ("posted", "Đã ghi sổ"),
            ("voided", "Đã hủy"),
            ("today", "Nhập hôm nay"),
            ("month", "Nhập tháng này"),
            ("no_lines", "Chưa có dòng vật tư"),
            ("has_lines", "Đã có dòng vật tư"),
            ("missing_keeper", "Thiếu thủ kho"),
            ("no_note", "Thiếu ghi chú"),
            ("large_receipt", "Phiếu nhập lớn"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()
        if value == "draft":
            return queryset.filter(trang_thai=PhieuNhap.TrangThai.DRAFT)
        if value == "posted":
            return queryset.filter(trang_thai=PhieuNhap.TrangThai.POSTED)
        if value == "voided":
            return queryset.filter(trang_thai=PhieuNhap.TrangThai.VOIDED)
        if value == "today":
            return queryset.filter(ngay_nhap__date=today)
        if value == "month":
            return queryset.filter(ngay_nhap__year=today.year, ngay_nhap__month=today.month)
        if value == "no_lines":
            return queryset.filter(line_count=0)
        if value == "has_lines":
            return queryset.filter(line_count__gt=0)
        if value == "missing_keeper":
            return queryset.filter(nguoi_nhap__isnull=True)
        if value == "no_note":
            return queryset.filter(Q(ghi_chu__isnull=True) | Q(ghi_chu=""))
        if value == "large_receipt":
            return queryset.filter(total_quantity__gte=50)
        return queryset


class IssueOperationalFilter(admin.SimpleListFilter):
    title = "Tình trạng phiếu xuất"
    parameter_name = "issue_status"

    def lookups(self, request, model_admin):
        return (
            ("draft", "Phiếu nháp"),
            ("posted", "Đã ghi sổ"),
            ("voided", "Đã hủy"),
            ("today", "Xuất hôm nay"),
            ("month", "Xuất tháng này"),
            ("no_lines", "Chưa có dòng vật tư"),
            ("has_lines", "Đã có dòng vật tư"),
            ("missing_receiver", "Thiếu đối tượng nhận"),
            ("employee_issue", "Xuất cho nhân viên"),
            ("target_issue", "Cấp CCHT cho mục tiêu"),
            ("payroll_deduction", "Chờ khấu trừ lương"),
            ("large_issue", "Phiếu xuất lớn"),
            ("no_note", "Thiếu ghi chú"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()
        if value == "draft":
            return queryset.filter(trang_thai=PhieuXuat.TrangThai.DRAFT)
        if value == "posted":
            return queryset.filter(trang_thai=PhieuXuat.TrangThai.POSTED)
        if value == "voided":
            return queryset.filter(trang_thai=PhieuXuat.TrangThai.VOIDED)
        if value == "today":
            return queryset.filter(ngay_xuat__date=today)
        if value == "month":
            return queryset.filter(ngay_xuat__year=today.year, ngay_xuat__month=today.month)
        if value == "no_lines":
            return queryset.filter(line_count=0)
        if value == "has_lines":
            return queryset.filter(line_count__gt=0)
        if value == "missing_receiver":
            return queryset.filter(
                Q(loai_xuat__in=["CAP_PHAT", "BAN_TRU_LUONG"], nhan_vien_nhan__isnull=True)
                | Q(loai_xuat="CONG_CU", muc_tieu_nhan__isnull=True)
            )
        if value == "employee_issue":
            return queryset.filter(loai_xuat__in=["CAP_PHAT", "BAN_TRU_LUONG"])
        if value == "target_issue":
            return queryset.filter(loai_xuat="CONG_CU")
        if value == "payroll_deduction":
            return queryset.filter(loai_xuat="BAN_TRU_LUONG", trang_thai_thanh_toan="CHUA_TRU")
        if value == "large_issue":
            return queryset.filter(total_quantity__gte=20)
        if value == "no_note":
            return queryset.filter(Q(ghi_chu__isnull=True) | Q(ghi_chu=""))
        return queryset


class InventoryVoidActionForm(ActionForm):
    void_reason = forms.CharField(
        required=False,
        label=_("Lý do hủy"),
        help_text=_("Bắt buộc khi hủy phiếu kho đã ghi sổ."),
    )
from .models import (
    LoaiVatTu, 
    VatTu, 
    PhieuNhap, 
    ChiTietPhieuNhap, 
    PhieuXuat, 
    ChiTietPhieuXuat, 
    CongCuTaiMucTieu,
    PhieuThuHoi,
    ChiTietPhieuThuHoi,
    BienBanMatHongVatTu,
)

# --- Setup Inlines (Bảng nhập liệu chi tiết) ---

class ChiTietNhapInline(admin.TabularInline):
    """Bảng nhập liệu chi tiết vật tư trong phiếu nhập kho"""
    model = ChiTietPhieuNhap
    extra = 1  # Số dòng trống hiển thị sẵn
    autocomplete_fields = ['vat_tu']  # Giúp tìm vật tư nhanh nếu list dài
    verbose_name = _("Chi tiết vật tư nhập")
    verbose_name_plural = _("Danh sách vật tư nhập kho")

    def has_add_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuNhap.TrangThai.DRAFT:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuNhap.TrangThai.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.trang_thai != PhieuNhap.TrangThai.DRAFT:
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)


class ChiTietXuatInline(admin.TabularInline):
    """Bảng nhập liệu chi tiết vật tư trong phiếu xuất kho"""
    model = ChiTietPhieuXuat
    extra = 1
    autocomplete_fields = ['vat_tu']
    verbose_name = _("Chi tiết vật tư xuất")
    verbose_name_plural = _("Danh sách vật tư xuất kho")

    def has_add_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuXuat.TrangThai.DRAFT:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuXuat.TrangThai.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.trang_thai != PhieuXuat.TrangThai.DRAFT:
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)


# --- Config Admin Chính ---


@admin.register(LoaiVatTu)
class LoaiVatTuAdmin(admin.ModelAdmin):
    """Danh mục phân loại vật tư, đồng phục và công cụ hỗ trợ."""
    change_list_template = "admin/inventory/loaivattu/change_list.html"
    list_display = (
        "ten_loai_hien_thi",
        "vat_tu_count_hien_thi",
        "ton_kho_hien_thi",
        "canh_bao_hien_thi",
        "cong_cu_muc_tieu_hien_thi",
        "thao_tac_nhanh",
    )
    search_fields = ("ten_loai", "mo_ta")
    list_filter = (MaterialCategoryOperationalFilter,)
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Thông tin danh mục", {"fields": ("ten_loai", "mo_ta")}),
        ("Ghi chú vận hành", {"fields": (), "description": "Danh mục vật tư là cấu hình nền cho kho. Khi đã có vật tư phát sinh nhập/xuất, nên đổi tên/mô tả có kiểm soát để tránh sai lệch báo cáo tồn kho."}),
    )

    def get_queryset(self, request):
        queryset = InventoryScopePolicy.current_queryset(self.model)
        return queryset.annotate(
            vat_tu_count=Count("vattu", distinct=True),
            total_stock=Coalesce(Sum("vattu__so_luong_ton"), Value(0), output_field=IntegerField()),
            low_stock_count=Count(
                "vattu",
                filter=Q(vattu__so_luong_ton__lte=F("vattu__muc_canh_bao")),
                distinct=True,
            ),
            out_of_stock_count=Count(
                "vattu",
                filter=Q(vattu__so_luong_ton__lte=0),
                distinct=True,
            ),
            target_tool_count=Count("vattu__congcutaimuctieu", distinct=True),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_loaivattu_export_csv",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        summary = queryset.aggregate(
            total_categories=Count("id", distinct=True),
            total_items=Count("vattu", distinct=True),
            total_stock=Coalesce(Sum("vattu__so_luong_ton"), Value(0), output_field=IntegerField()),
            empty_categories=Count("id", filter=Q(vattu__isnull=True), distinct=True),
            no_description=Count("id", filter=Q(mo_ta=""), distinct=True),
            low_stock_categories=Count(
                "id",
                filter=Q(vattu__so_luong_ton__lte=F("vattu__muc_canh_bao")),
                distinct=True,
            ),
            out_of_stock_categories=Count("id", filter=Q(vattu__so_luong_ton__lte=0), distinct=True),
            target_tool_categories=Count(
                "id",
                filter=Q(vattu__congcutaimuctieu__isnull=False),
                distinct=True,
            ),
        )
        query_string = request.META.get("QUERY_STRING", "")
        export_url = "export-csv/" + (f"?{query_string}" if query_string else "")
        extra_context.update({
            "inventory_category_summary": summary,
            "inventory_category_export_url": export_url,
            "inventory_quick_links": {
                "dashboard": "/inventory/",
                "stock_report": "/inventory/bao-cao-ton/",
                "items": "../vattu/",
                "receipts": "../phieunhap/",
                "issues": "../phieuxuat/",
                "target_tools": "../congcutaimuctieu/",
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="scmdpro-loai-vat-tu.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Tên loại vật tư",
            "Mô tả",
            "Số loại vật tư",
            "Tổng tồn kho",
            "Vật tư cảnh báo",
            "Vật tư hết tồn",
            "Công cụ tại mục tiêu",
        ])
        for category in queryset:
            writer.writerow([
                category.pk,
                category.ten_loai,
                category.mo_ta,
                getattr(category, "vat_tu_count", 0),
                getattr(category, "total_stock", 0),
                getattr(category, "low_stock_count", 0),
                getattr(category, "out_of_stock_count", 0),
                getattr(category, "target_tool_count", 0),
            ])
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.ACCESS,
            model_name="LoaiVatTu",
            note="Xuất CSV danh mục loại vật tư từ Django Admin.",
            changes={"rows": queryset.count(), "query": request.GET.dict()},
        )
        return response

    def save_model(self, request, obj, form, change):
        action = AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE
        before = None
        if change and obj.pk:
            before = LoaiVatTu.objects.for_current().filter(pk=obj.pk).values("ten_loai", "mo_ta").first()
        super().save_model(request, obj, form, change)
        record_inventory_admin_audit_action(
            request,
            action=action,
            model_name="LoaiVatTu",
            object_id=obj.pk,
            note="Cập nhật danh mục loại vật tư qua Django Admin." if change else "Tạo danh mục loại vật tư qua Django Admin.",
            changes={"before": before, "after": {"ten_loai": obj.ten_loai, "mo_ta": obj.mo_ta}},
        )

    def delete_model(self, request, obj):
        object_id = obj.pk
        before = {"ten_loai": obj.ten_loai, "mo_ta": obj.mo_ta}
        super().delete_model(request, obj)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="LoaiVatTu",
            object_id=object_id,
            note="Xóa danh mục loại vật tư qua Django Admin.",
            changes={"before": before},
        )

    def delete_queryset(self, request, queryset):
        safe_queryset = LoaiVatTu.objects.selected_from_queryset(queryset)
        ids = list(safe_queryset.values_list("pk", flat=True))
        names = list(safe_queryset.values_list("ten_loai", flat=True))
        if not ids:
            self.message_user(request, _("Không có danh mục vật tư nào trong phạm vi được phép."), messages.ERROR)
            return
        with transaction.atomic():
            locked_queryset = LoaiVatTu.objects.for_current().select_for_update().filter(pk__in=ids)
            super().delete_queryset(request, locked_queryset)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="LoaiVatTu",
            note="Xóa hàng loạt danh mục loại vật tư qua Django Admin.",
            changes={"ids": ids, "names": names},
        )

    def ten_loai_hien_thi(self, obj):
        return format_html('<strong style="color:#0f172a;">{}</strong><br><small style="color:#64748b;">{}</small>', obj.ten_loai, obj.mo_ta or "Chưa có mô tả")
    ten_loai_hien_thi.short_description = _("Loại vật tư")
    ten_loai_hien_thi.admin_order_field = "ten_loai"

    def vat_tu_count_hien_thi(self, obj):
        count = getattr(obj, "vat_tu_count", 0)
        return format_html('<a href="../vattu/?loai_vat_tu__id__exact={}" style="font-weight:800;">{} vật tư</a>', obj.pk, count)
    vat_tu_count_hien_thi.short_description = _("Số vật tư")
    vat_tu_count_hien_thi.admin_order_field = "vat_tu_count"

    def ton_kho_hien_thi(self, obj):
        value = getattr(obj, "total_stock", 0) or 0
        return format_html('<strong style="color:#059669;">{}</strong>', value)
    ton_kho_hien_thi.short_description = _("Tổng tồn")
    ton_kho_hien_thi.admin_order_field = "total_stock"

    def canh_bao_hien_thi(self, obj):
        low_stock = getattr(obj, "low_stock_count", 0) or 0
        out_of_stock = getattr(obj, "out_of_stock_count", 0) or 0
        if out_of_stock:
            return format_html('<span style="color:#dc2626;font-weight:800;">{} hết tồn</span><br><small>{} cảnh báo</small>', out_of_stock, low_stock)
        if low_stock:
            return format_html('<span style="color:#d97706;font-weight:800;">{} cảnh báo</span>', low_stock)
        return format_html('<span style="color:#059669;font-weight:800;">Ổn định</span>')
    canh_bao_hien_thi.short_description = _("Cảnh báo")
    canh_bao_hien_thi.admin_order_field = "low_stock_count"

    def cong_cu_muc_tieu_hien_thi(self, obj):
        count = getattr(obj, "target_tool_count", 0) or 0
        if count:
            return format_html('<a href="../congcutaimuctieu/?vat_tu__loai_vat_tu__id__exact={}" style="font-weight:800;">{} mục tiêu</a>', obj.pk, count)
        return "0"
    cong_cu_muc_tieu_hien_thi.short_description = _("CCHT tại mục tiêu")
    cong_cu_muc_tieu_hien_thi.admin_order_field = "target_tool_count"

    def thao_tac_nhanh(self, obj):
        return format_html(
            '<a class="button" href="../vattu/?loai_vat_tu__id__exact={}">Vật tư</a> '
            '<a class="button" href="../vattu/add/?loai_vat_tu={}">Thêm vật tư</a> '
            '<a class="button" href="{}">Sửa</a>',
            obj.pk,
            obj.pk,
            f"{obj.pk}/change/",
        )
    thao_tac_nhanh.short_description = _("Thao tác")

@admin.register(VatTu)
class VatTuAdmin(admin.ModelAdmin):
    """Quản lý danh mục vật tư, công cụ hỗ trợ và tồn kho hiện tại."""
    change_list_template = "admin/inventory/vattu/change_list.html"
    list_display = (
        "ten_vat_tu_hien_thi",
        "loai_vat_tu_hien_thi",
        "ton_kho_hien_thi",
        "muc_canh_bao_hien_thi",
        "gia_tri_ton_hien_thi",
        "luan_chuyen_hien_thi",
        "thao_tac_nhanh",
    )
    search_fields = ("ten_vat_tu", "loai_vat_tu__ten_loai", "don_vi_tinh")
    list_filter = (MaterialOperationalFilter, "loai_vat_tu", "don_vi_tinh")
    list_select_related = ("loai_vat_tu",)
    readonly_fields = ("so_luong_ton",)
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Thông tin vật tư", {"fields": ("loai_vat_tu", "ten_vat_tu", "don_vi_tinh", "hinh_anh")}),
        ("Giá và tồn kho", {"fields": ("gia_nhap", "gia_ban", "so_luong_ton", "muc_canh_bao")}),
        ("Ghi chú thủ kho", {"fields": (), "description": "Tồn kho hiện tại được cập nhật qua phiếu nhập/xuất đã ghi sổ. Không chỉnh tay số tồn nếu chưa có biên bản đối soát hoặc phiếu điều chỉnh."}),
    )

    def get_queryset(self, request):
        queryset = InventoryScopePolicy.current_queryset(self.model)
        return queryset.select_related("loai_vat_tu").annotate(
            receipt_line_count=Count("chitietphieunhap", distinct=True),
            issue_line_count=Count("chitietphieuxuat", distinct=True),
            target_tool_count=Count("congcutaimuctieu", distinct=True),
            target_tool_quantity=Coalesce(Sum("congcutaimuctieu__so_luong_dang_giu"), Value(0), output_field=IntegerField()),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_vattu_export_csv",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        summary = queryset.aggregate(
            total_items=Count("id", distinct=True),
            total_stock=Coalesce(Sum("so_luong_ton"), Value(0), output_field=IntegerField()),
            low_stock=Count("id", filter=Q(so_luong_ton__lte=F("muc_canh_bao")), distinct=True),
            out_of_stock=Count("id", filter=Q(so_luong_ton__lte=0), distinct=True),
            no_category=Count("id", filter=Q(loai_vat_tu__isnull=True), distinct=True),
            missing_image=Count("id", filter=Q(hinh_anh__isnull=True) | Q(hinh_anh=""), distinct=True),
            no_cost=Count("id", filter=Q(gia_nhap__lte=0), distinct=True),
            payroll_deductible=Count("id", filter=Q(gia_ban__gt=0), distinct=True),
            target_tools=Count("id", filter=Q(congcutaimuctieu__isnull=False), distinct=True),
        )
        # Dùng values_list để không defer FK đang select_related trong Django 5.x.
        total_value = 0
        for stock, cost in queryset.values_list("so_luong_ton", "gia_nhap").iterator(chunk_size=300):
            total_value += int(stock or 0) * int(cost or 0)
        summary["total_value"] = total_value
        query_string = request.META.get("QUERY_STRING", "")
        export_url = "export-csv/" + (f"?{query_string}" if query_string else "")
        extra_context.update({
            "inventory_material_summary": summary,
            "inventory_material_export_url": export_url,
            "inventory_material_links": {
                "add": "add/",
                "categories": "../loaivattu/",
                "stock_report": "/inventory/bao-cao-ton/",
                "dashboard": "/inventory/",
                "receipts": "../phieunhap/",
                "issues": "../phieuxuat/",
                "target_tools": "../congcutaimuctieu/",
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="scmdpro-vat-tu-ton-kho.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Tên vật tư/CCHT",
            "Loại vật tư",
            "Đơn vị tính",
            "Tồn kho",
            "Mức cảnh báo",
            "Giá vốn",
            "Giá trừ lương",
            "Giá trị tồn",
            "Dòng nhập",
            "Dòng xuất",
            "CCHT tại mục tiêu",
            "Số lượng tại mục tiêu",
        ])
        for material in queryset:
            stock = int(material.so_luong_ton or 0)
            cost = int(material.gia_nhap or 0)
            writer.writerow([
                material.pk,
                material.ten_vat_tu,
                material.loai_vat_tu.ten_loai if material.loai_vat_tu else "",
                material.don_vi_tinh,
                stock,
                material.muc_canh_bao,
                cost,
                int(material.gia_ban or 0),
                stock * cost,
                getattr(material, "receipt_line_count", 0) or 0,
                getattr(material, "issue_line_count", 0) or 0,
                getattr(material, "target_tool_count", 0) or 0,
                getattr(material, "target_tool_quantity", 0) or 0,
            ])
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.ACCESS,
            model_name="VatTu",
            object_id="export-csv",
            note=f"Xuất CSV danh mục vật tư/tồn kho qua admin. Số dòng: {queryset.count()}.",
            changes={"path": request.get_full_path()},
        )
        return response

    def save_model(self, request, obj, form, change):
        changed_data = list(getattr(form, "changed_data", []) or [])
        before = {}
        if change and obj.pk:
            previous = VatTu.objects.for_current().filter(pk=obj.pk).first()
            if previous:
                before = {field: str(getattr(previous, field, "")) for field in changed_data}
        super().save_model(request, obj, form, change)
        after = {field: str(getattr(obj, field, "")) for field in changed_data}
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name="VatTu",
            object_id=obj.pk,
            note="Cập nhật danh mục vật tư/tồn kho nền qua admin.",
            changes={"before": before, "after": after, "changed_fields": changed_data},
        )

    def delete_model(self, request, obj):
        object_id = obj.pk
        snapshot = {"ten_vat_tu": obj.ten_vat_tu, "so_luong_ton": obj.so_luong_ton}
        super().delete_model(request, obj)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="VatTu",
            object_id=object_id,
            note="Xóa vật tư qua admin.",
            changes=snapshot,
        )

    def delete_queryset(self, request, queryset):
        safe_queryset = VatTu.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            snapshots = [
                {"id": item.pk, "ten_vat_tu": item.ten_vat_tu, "so_luong_ton": item.so_luong_ton}
                for item in locked_queryset
            ]
            if not snapshots:
                self.message_user(request, _("Không có vật tư nào trong phạm vi được phép."), messages.ERROR)
                return
            super().delete_queryset(request, locked_queryset)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="VatTu",
            object_id="bulk-delete",
            note=f"Xóa hàng loạt {len(snapshots)} vật tư qua admin.",
            changes={"items": snapshots},
        )

    def ten_vat_tu_hien_thi(self, obj):
        if obj.hinh_anh:
            return format_html('<strong>{}</strong><br><small style="color:#64748b;">Có ảnh minh họa</small>', obj.ten_vat_tu)
        return format_html('<strong>{}</strong><br><small style="color:#dc2626;">Thiếu ảnh minh họa</small>', obj.ten_vat_tu)
    ten_vat_tu_hien_thi.short_description = _("Vật tư/CCHT")
    ten_vat_tu_hien_thi.admin_order_field = "ten_vat_tu"

    def loai_vat_tu_hien_thi(self, obj):
        if obj.loai_vat_tu_id:
            return format_html('<a href="../loaivattu/{}/change/" style="font-weight:800;">{}</a>', obj.loai_vat_tu_id, obj.loai_vat_tu)
        return format_html('<span style="color:#dc2626;font-weight:800;">Thiếu phân loại</span>')
    loai_vat_tu_hien_thi.short_description = _("Phân loại")
    loai_vat_tu_hien_thi.admin_order_field = "loai_vat_tu__ten_loai"

    def ton_kho_hien_thi(self, obj):
        stock = obj.so_luong_ton or 0
        threshold = obj.muc_canh_bao or 0
        if stock <= 0:
            return format_html('<strong style="color:#dc2626;">{} {}</strong><br><small>Hết tồn</small>', stock, obj.don_vi_tinh)
        if stock <= threshold:
            return format_html('<strong style="color:#d97706;">{} {}</strong><br><small>Dưới mức cảnh báo</small>', stock, obj.don_vi_tinh)
        return format_html('<strong style="color:#059669;">{} {}</strong><br><small>An toàn</small>', stock, obj.don_vi_tinh)
    ton_kho_hien_thi.short_description = _("Tồn kho")
    ton_kho_hien_thi.admin_order_field = "so_luong_ton"

    def muc_canh_bao_hien_thi(self, obj):
        return format_html('<span>{} {}</span>', obj.muc_canh_bao or 0, obj.don_vi_tinh)
    muc_canh_bao_hien_thi.short_description = _("Mức cảnh báo")
    muc_canh_bao_hien_thi.admin_order_field = "muc_canh_bao"

    def gia_tri_ton_hien_thi(self, obj):
        value = int(obj.so_luong_ton or 0) * int(obj.gia_nhap or 0)
        return format_html('<strong>{:,} đ</strong><br><small>Giá vốn: {:,} đ</small>', value, int(obj.gia_nhap or 0))
    gia_tri_ton_hien_thi.short_description = _("Giá trị tồn")
    gia_tri_ton_hien_thi.admin_order_field = "gia_nhap"

    def luan_chuyen_hien_thi(self, obj):
        receipt_count = getattr(obj, "receipt_line_count", 0) or 0
        issue_count = getattr(obj, "issue_line_count", 0) or 0
        target_qty = getattr(obj, "target_tool_quantity", 0) or 0
        return format_html(
            '<span>Nhập: <strong>{}</strong></span><br><span>Xuất: <strong>{}</strong></span><br><span>Mục tiêu giữ: <strong>{}</strong></span>',
            receipt_count,
            issue_count,
            target_qty,
        )
    luan_chuyen_hien_thi.short_description = _("Luân chuyển")

    def thao_tac_nhanh(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" href="../phieunhap/?chi_tiet__vat_tu__id__exact={}">Nhập</a> '
            '<a class="button" href="../phieuxuat/?chi_tiet__vat_tu__id__exact={}">Xuất</a> '
            '<a class="button" href="../congcutaimuctieu/?vat_tu__id__exact={}">Mục tiêu</a>',
            f"{obj.pk}/change/",
            obj.pk,
            obj.pk,
            obj.pk,
        )
    thao_tac_nhanh.short_description = _("Thao tác")

@admin.register(PhieuNhap)
class PhieuNhapAdmin(admin.ModelAdmin):
    """Quản lý phiếu nhập kho vật tư từ nhà cung cấp hoặc thu hồi."""
    change_list_template = "admin/inventory/phieunhap/change_list.html"
    list_display = (
        "ma_phieu_hien_thi",
        "trang_thai_hien_thi",
        "ngay_nhap_format",
        "nguoi_nhap_hien_thi",
        "tong_hop_vat_tu_hien_thi",
        "thao_tac_nhanh",
    )
    list_filter = (ReceiptOperationalFilter, "trang_thai", "ngay_nhap", "nguoi_nhap")
    list_select_related = ("nguoi_nhap",)
    inlines = [ChiTietNhapInline]
    search_fields = ("ma_phieu", "nguoi_nhap__ho_ten", "nguoi_nhap__ma_nhan_vien", "ghi_chu")
    date_hierarchy = "ngay_nhap"
    actions = ["post_inventory_documents", "void_inventory_documents"]
    action_form = InventoryVoidActionForm
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Thông tin phiếu nhập", {"fields": ("ma_phieu", "nguoi_nhap", "ngay_nhap", "trang_thai")}),
        ("Ghi chú đối soát", {"fields": ("ghi_chu",), "description": "Phiếu nhập là chứng từ làm tăng tồn kho. Sau khi ghi sổ không sửa trực tiếp nội dung chính; nếu sai phải hủy có lý do và lập chứng từ điều chỉnh để giữ lịch sử kho."}),
    )

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_view_document(request.user, obj).allowed

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_change_document(request.user, obj).allowed

    def get_queryset(self, request):
        queryset = InventoryScopePolicy.current_queryset(self.model)
        return queryset.select_related("nguoi_nhap").annotate(
            line_count=Count("chi_tiet", distinct=True),
            material_count=Count("chi_tiet__vat_tu", distinct=True),
            total_quantity=Coalesce(Sum("chi_tiet__so_luong"), Value(0), output_field=IntegerField()),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_phieunhap_export_csv",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        today = timezone.localdate()
        summary = queryset.aggregate(
            total_receipts=Count("id", distinct=True),
            draft_receipts=Count("id", filter=Q(trang_thai=PhieuNhap.TrangThai.DRAFT), distinct=True),
            posted_receipts=Count("id", filter=Q(trang_thai=PhieuNhap.TrangThai.POSTED), distinct=True),
            voided_receipts=Count("id", filter=Q(trang_thai=PhieuNhap.TrangThai.VOIDED), distinct=True),
            today_receipts=Count("id", filter=Q(ngay_nhap__date=today), distinct=True),
            month_receipts=Count(
                "id",
                filter=Q(ngay_nhap__year=today.year, ngay_nhap__month=today.month),
                distinct=True,
            ),
            no_lines=Count("id", filter=Q(chi_tiet__isnull=True), distinct=True),
            missing_keeper=Count("id", filter=Q(nguoi_nhap__isnull=True), distinct=True),
            no_note=Count("id", filter=Q(ghi_chu__isnull=True) | Q(ghi_chu=""), distinct=True),
            total_lines=Count("chi_tiet", distinct=True),
            total_quantity=Coalesce(Sum("chi_tiet__so_luong"), Value(0), output_field=IntegerField()),
        )
        total_value = 0
        for quantity, unit_price in ChiTietPhieuNhap.objects.filter(phieu_nhap__in=queryset).values_list("so_luong", "don_gia").iterator(chunk_size=500):
            total_value += int(quantity or 0) * int(unit_price or 0)
        summary["total_value"] = total_value
        query_string = request.META.get("QUERY_STRING", "")
        export_url = "export-csv/" + (f"?{query_string}" if query_string else "")
        extra_context.update({
            "receipt_summary": summary,
            "receipt_export_url": export_url,
            "receipt_links": {
                "add": "add/",
                "materials": "../vattu/",
                "categories": "../loaivattu/",
                "issues": "../phieuxuat/",
                "target_tools": "../congcutaimuctieu/",
                "stock_report": "/inventory/bao-cao-ton/",
                "dashboard": "/inventory/",
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="scmdpro-phieu-nhap-kho.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Mã phiếu",
            "Trạng thái",
            "Ngày nhập",
            "Thủ kho",
            "Số dòng vật tư",
            "Số loại vật tư",
            "Tổng số lượng",
            "Tổng giá trị nhập",
            "Ghi chú",
        ])
        detail_values = {}
        detail_queryset = ChiTietPhieuNhap.objects.filter(phieu_nhap__in=queryset).values_list("phieu_nhap_id", "so_luong", "don_gia")
        for receipt_id, quantity, unit_price in detail_queryset.iterator(chunk_size=500):
            detail_values[receipt_id] = detail_values.get(receipt_id, 0) + int(quantity or 0) * int(unit_price or 0)
        for receipt in queryset:
            writer.writerow([
                receipt.pk,
                receipt.ma_phieu,
                receipt.get_trang_thai_display(),
                timezone.localtime(receipt.ngay_nhap).strftime("%d/%m/%Y %H:%M") if receipt.ngay_nhap else "",
                str(receipt.nguoi_nhap) if receipt.nguoi_nhap_id else "",
                getattr(receipt, "line_count", 0) or 0,
                getattr(receipt, "material_count", 0) or 0,
                getattr(receipt, "total_quantity", 0) or 0,
                detail_values.get(receipt.pk, 0),
                receipt.ghi_chu,
            ])
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.ACCESS,
            model_name="PhieuNhap",
            object_id="export-csv",
            note=f"Xuất CSV phiếu nhập kho qua admin. Số dòng: {queryset.count()}.",
            changes={"path": request.get_full_path()},
        )
        return response

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.trang_thai != PhieuNhap.TrangThai.DRAFT:
            readonly_fields.extend(field.name for field in self.model._meta.fields)
        return tuple(dict.fromkeys(readonly_fields))

    def has_delete_permission(self, request, obj=None):
        base_permission = super().has_delete_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_delete_document(request.user, obj).allowed

    def save_model(self, request, obj, form, change):
        changed_data = list(getattr(form, "changed_data", []) or [])
        before = {}
        if change and obj.pk:
            previous = PhieuNhap.objects.for_current().filter(pk=obj.pk).first()
            policy = InventoryDocumentPolicy.can_change_document(request.user, previous)
            if not policy.allowed:
                raise PermissionDenied(policy.message)
            if previous and previous.trang_thai != PhieuNhap.TrangThai.DRAFT:
                raise ValidationError(_("Không được sửa trực tiếp phiếu nhập đã ghi sổ hoặc đã hủy."))
            if previous:
                before = {
                    "ma_phieu": previous.ma_phieu,
                    "nguoi_nhap": str(previous.nguoi_nhap) if previous.nguoi_nhap_id else "",
                    "ngay_nhap": previous.ngay_nhap.isoformat() if previous.ngay_nhap else "",
                    "trang_thai": previous.trang_thai,
                    "ghi_chu": previous.ghi_chu,
                }
        super().save_model(request, obj, form, change)
        after = {
            "ma_phieu": obj.ma_phieu,
            "nguoi_nhap": str(obj.nguoi_nhap) if obj.nguoi_nhap_id else "",
            "ngay_nhap": obj.ngay_nhap.isoformat() if obj.ngay_nhap else "",
            "trang_thai": obj.trang_thai,
            "ghi_chu": obj.ghi_chu,
        }
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name="PhieuNhap",
            object_id=obj.pk,
            note="Cập nhật phiếu nhập kho qua admin." if change else "Tạo phiếu nhập kho qua admin.",
            changes={"before": before, "after": after, "changed_fields": changed_data},
        )

    def delete_model(self, request, obj):
        policy = InventoryDocumentPolicy.can_delete_document(request.user, obj)
        if not policy.allowed:
            raise PermissionDenied(policy.message)
        object_id = obj.pk
        snapshot = {
            "ma_phieu": obj.ma_phieu,
            "trang_thai": obj.trang_thai,
            "nguoi_nhap": str(obj.nguoi_nhap) if obj.nguoi_nhap_id else "",
            "ngay_nhap": obj.ngay_nhap.isoformat() if obj.ngay_nhap else "",
        }
        super().delete_model(request, obj)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="PhieuNhap",
            object_id=object_id,
            note="Xóa phiếu nhập kho nháp qua admin.",
            changes=snapshot,
        )

    def delete_queryset(self, request, queryset):
        safe_queryset = PhieuNhap.objects.selected_from_queryset(queryset)
        non_draft_count = safe_queryset.exclude(trang_thai=PhieuNhap.TrangThai.DRAFT).count()
        if non_draft_count:
            self.message_user(request, _("Chỉ được xóa hàng loạt phiếu nhập còn ở trạng thái Nháp."), messages.ERROR)
            return
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            snapshots = []
            for item in locked_queryset:
                policy = InventoryDocumentPolicy.can_delete_document(request.user, item)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                snapshots.append({"id": item.pk, "ma_phieu": item.ma_phieu, "trang_thai": item.trang_thai})
            if not snapshots:
                return
            super().delete_queryset(request, safe_queryset.filter(pk__in=[item["id"] for item in snapshots]))
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="PhieuNhap",
            object_id="bulk-delete",
            note=f"Xóa hàng loạt {len(snapshots)} phiếu nhập nháp qua admin.",
            changes={"items": snapshots},
        )

    @admin.action(description="Ghi sổ phiếu nhập kho")
    def post_inventory_documents(self, request, queryset):
        success_count = 0
        safe_queryset = PhieuNhap.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update().prefetch_related("chi_tiet")
            for document in locked_queryset:
                policy = InventoryDocumentPolicy.can_post_document(request.user, document)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                try:
                    InventoryDocumentUseCase.post_inventory_document(document, user=request.user)
                    success_count += 1
                    record_inventory_admin_audit_action(
                        request,
                        action=AuditLog.Action.UPDATE,
                        model_name="PhieuNhap",
                        object_id=document.pk,
                        note="Ghi sổ phiếu nhập kho qua admin action.",
                        changes={"ma_phieu": document.ma_phieu, "from_action": "post_inventory_documents"},
                    )
                except InventoryDocumentPostingError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
        if success_count:
            self.message_user(request, f"Đã ghi sổ {success_count} phiếu nhập.", messages.SUCCESS)

    @admin.action(description="Hủy phiếu nhập kho đã ghi sổ")
    def void_inventory_documents(self, request, queryset):
        reason = (request.POST.get("void_reason") or "").strip()
        if not reason:
            self.message_user(request, _("Phải nhập lý do khi hủy phiếu nhập kho."), messages.ERROR)
            return
        success_count = 0
        safe_queryset = PhieuNhap.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            for document in locked_queryset:
                policy = InventoryDocumentPolicy.can_void_document(request.user, document)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                try:
                    InventoryDocumentUseCase.void_inventory_document(
                        document,
                        reason=reason,
                        user=request.user,
                    )
                    success_count += 1
                    record_inventory_admin_audit_action(
                        request,
                        action=AuditLog.Action.UPDATE,
                        model_name="PhieuNhap",
                        object_id=document.pk,
                        note="Hủy phiếu nhập kho đã ghi sổ qua admin action.",
                        changes={"ma_phieu": document.ma_phieu, "reason": reason, "from_action": "void_inventory_documents"},
                    )
                except InventoryDocumentPostingError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
        if success_count:
            self.message_user(request, f"Đã hủy {success_count} phiếu nhập.", messages.SUCCESS)

    def ma_phieu_hien_thi(self, obj):
        return format_html('<strong>{}</strong><br><small style="color:#64748b;">ID #{}</small>', obj.ma_phieu, obj.pk)
    ma_phieu_hien_thi.short_description = _("Mã phiếu")
    ma_phieu_hien_thi.admin_order_field = "ma_phieu"

    def trang_thai_hien_thi(self, obj):
        if obj.trang_thai == PhieuNhap.TrangThai.POSTED:
            return format_html('<span style="color:#059669;font-weight:800;">Đã ghi sổ</span>')
        if obj.trang_thai == PhieuNhap.TrangThai.VOIDED:
            return format_html('<span style="color:#dc2626;font-weight:800;">Đã hủy</span>')
        return format_html('<span style="color:#d97706;font-weight:800;">Nháp</span>')
    trang_thai_hien_thi.short_description = _("Trạng thái")
    trang_thai_hien_thi.admin_order_field = "trang_thai"

    def ngay_nhap_format(self, obj):
        return timezone.localtime(obj.ngay_nhap).strftime("%d/%m/%Y %H:%M") if obj.ngay_nhap else ""
    ngay_nhap_format.short_description = _("Ngày nhập kho")
    ngay_nhap_format.admin_order_field = "ngay_nhap"

    def nguoi_nhap_hien_thi(self, obj):
        if obj.nguoi_nhap_id:
            return format_html('<strong>{}</strong>', obj.nguoi_nhap)
        return format_html('<span style="color:#dc2626;font-weight:800;">Thiếu thủ kho</span>')
    nguoi_nhap_hien_thi.short_description = _("Thủ kho")
    nguoi_nhap_hien_thi.admin_order_field = "nguoi_nhap__ho_ten"

    def tong_hop_vat_tu_hien_thi(self, obj):
        return format_html(
            '<span>Dòng: <strong>{}</strong></span><br><span>Loại vật tư: <strong>{}</strong></span><br><span>Số lượng: <strong>{}</strong></span>',
            getattr(obj, "line_count", 0) or 0,
            getattr(obj, "material_count", 0) or 0,
            getattr(obj, "total_quantity", 0) or 0,
        )
    tong_hop_vat_tu_hien_thi.short_description = _("Tổng hợp nhập")

    def thao_tac_nhanh(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" href="../vattu/">Vật tư</a> '
            '<a class="button" href="../phieuxuat/">Xuất</a>',
            f"{obj.pk}/change/",
        )
    thao_tac_nhanh.short_description = _("Thao tác")


@admin.register(PhieuXuat)
class PhieuXuatAdmin(admin.ModelAdmin):
    """Quản lý phiếu xuất kho, cấp phát đồng phục/CCHT và các khoản bán trừ lương."""
    change_list_template = "admin/inventory/phieuxuat/change_list.html"
    list_display = (
        "ma_phieu_hien_thi",
        "trang_thai_hien_thi",
        "loai_xuat_hien_thi",
        "nguoi_nhan_hien_thi",
        "tong_hop_vat_tu_hien_thi",
        "thanh_toan_hien_thi",
        "thao_tac_nhanh",
    )
    list_filter = (IssueOperationalFilter, "trang_thai", "loai_xuat", "trang_thai_thanh_toan", "ngay_xuat")
    list_select_related = ("nhan_vien_nhan", "muc_tieu_nhan")
    inlines = [ChiTietXuatInline]
    autocomplete_fields = ("nhan_vien_nhan", "muc_tieu_nhan")
    search_fields = (
        "ma_phieu",
        "nhan_vien_nhan__ho_ten",
        "nhan_vien_nhan__ma_nhan_vien",
        "muc_tieu_nhan__ten_muc_tieu",
        "ghi_chu",
    )
    date_hierarchy = "ngay_xuat"
    actions = ["post_inventory_documents", "void_inventory_documents"]
    action_form = InventoryVoidActionForm
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        ("Thông tin phiếu xuất", {"fields": ("ma_phieu", "loai_xuat", "ngay_xuat", "trang_thai")}),
        ("Đối tượng tiếp nhận", {"fields": ("nhan_vien_nhan", "muc_tieu_nhan", "trang_thai_thanh_toan")}),
        ("Tài chính và ghi chú", {"fields": ("tong_tien_phai_thu", "ghi_chu"), "description": "Phiếu xuất làm giảm tồn kho. Phiếu bán trừ lương cần đối soát với payroll; phiếu CCHT tại mục tiêu cần trace được về mục tiêu nhận."}),
    )
    readonly_fields = ("tong_tien_phai_thu",)

    def has_view_permission(self, request, obj=None):
        base_permission = super().has_view_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_view_document(request.user, obj).allowed

    def has_change_permission(self, request, obj=None):
        base_permission = super().has_change_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_change_document(request.user, obj).allowed

    def get_queryset(self, request):
        queryset = InventoryScopePolicy.current_queryset(self.model)
        return queryset.select_related("nhan_vien_nhan", "muc_tieu_nhan").annotate(
            line_count=Count("chi_tiet", distinct=True),
            material_count=Count("chi_tiet__vat_tu", distinct=True),
            total_quantity=Coalesce(Sum("chi_tiet__so_luong"), Value(0), output_field=IntegerField()),
            payroll_line_count=Count("chi_tiet", filter=Q(loai_xuat="BAN_TRU_LUONG"), distinct=True),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_phieuxuat_export_csv",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        today = timezone.localdate()
        summary = queryset.aggregate(
            total_issues=Count("id", distinct=True),
            draft_issues=Count("id", filter=Q(trang_thai=PhieuXuat.TrangThai.DRAFT), distinct=True),
            posted_issues=Count("id", filter=Q(trang_thai=PhieuXuat.TrangThai.POSTED), distinct=True),
            voided_issues=Count("id", filter=Q(trang_thai=PhieuXuat.TrangThai.VOIDED), distinct=True),
            today_issues=Count("id", filter=Q(ngay_xuat__date=today), distinct=True),
            month_issues=Count("id", filter=Q(ngay_xuat__year=today.year, ngay_xuat__month=today.month), distinct=True),
            no_lines=Count("id", filter=Q(chi_tiet__isnull=True), distinct=True),
            employee_issues=Count("id", filter=Q(loai_xuat__in=["CAP_PHAT", "BAN_TRU_LUONG"]), distinct=True),
            target_issues=Count("id", filter=Q(loai_xuat="CONG_CU"), distinct=True),
            payroll_deduction=Count("id", filter=Q(loai_xuat="BAN_TRU_LUONG"), distinct=True),
            pending_payroll=Count("id", filter=Q(loai_xuat="BAN_TRU_LUONG", trang_thai_thanh_toan="CHUA_TRU"), distinct=True),
            missing_receiver=Count(
                "id",
                filter=(
                    Q(loai_xuat__in=["CAP_PHAT", "BAN_TRU_LUONG"], nhan_vien_nhan__isnull=True)
                    | Q(loai_xuat="CONG_CU", muc_tieu_nhan__isnull=True)
                ),
                distinct=True,
            ),
            total_lines=Count("chi_tiet", distinct=True),
            total_quantity=Coalesce(Sum("chi_tiet__so_luong"), Value(0), output_field=IntegerField()),
            total_payroll_amount=Coalesce(Sum("tong_tien_phai_thu"), Value(0), output_field=IntegerField()),
        )
        total_value = 0
        for quantity, unit_price in ChiTietPhieuXuat.objects.filter(phieu_xuat__in=queryset).values_list("so_luong", "don_gia_ban").iterator(chunk_size=500):
            total_value += int(quantity or 0) * int(unit_price or 0)
        summary["total_value"] = total_value
        query_string = request.META.get("QUERY_STRING", "")
        export_url = "export-csv/" + (f"?{query_string}" if query_string else "")
        extra_context.update({
            "issue_summary": summary,
            "issue_export_url": export_url,
            "issue_links": {
                "add": "add/",
                "materials": "../vattu/",
                "categories": "../loaivattu/",
                "receipts": "../phieunhap/",
                "target_tools": "../congcutaimuctieu/",
                "stock_report": "/inventory/bao-cao-ton/",
                "dashboard": "/inventory/",
                "employees": "../../users/nhanvien/",
                "targets": "../../clients/muctieu/",
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="scmdpro-phieu-xuat-kho.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Mã phiếu",
            "Loại xuất",
            "Trạng thái chứng từ",
            "Trạng thái thanh toán",
            "Ngày xuất",
            "Nhân viên nhận",
            "Mục tiêu nhận",
            "Số dòng",
            "Số loại vật tư",
            "Tổng số lượng",
            "Tổng tiền phải thu",
            "Ghi chú",
        ])
        for document in queryset:
            writer.writerow([
                document.pk,
                document.ma_phieu,
                document.get_loai_xuat_display(),
                document.get_trang_thai_display(),
                document.get_trang_thai_thanh_toan_display(),
                timezone.localtime(document.ngay_xuat).strftime("%d/%m/%Y %H:%M") if document.ngay_xuat else "",
                str(document.nhan_vien_nhan) if document.nhan_vien_nhan_id else "",
                str(document.muc_tieu_nhan) if document.muc_tieu_nhan_id else "",
                getattr(document, "line_count", 0) or 0,
                getattr(document, "material_count", 0) or 0,
                getattr(document, "total_quantity", 0) or 0,
                int(document.tong_tien_phai_thu or 0),
                document.ghi_chu,
            ])
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.ACCESS,
            model_name="PhieuXuat",
            object_id="export-csv",
            note=f"Xuất CSV phiếu xuất kho qua admin. Số dòng: {queryset.count()}.",
            changes={"path": request.get_full_path()},
        )
        return response

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.trang_thai != PhieuXuat.TrangThai.DRAFT:
            readonly_fields.extend(field.name for field in self.model._meta.fields)
        return tuple(dict.fromkeys(readonly_fields))

    def has_delete_permission(self, request, obj=None):
        base_permission = super().has_delete_permission(request, obj)
        if not base_permission or obj is None:
            return base_permission
        return InventoryDocumentPolicy.can_delete_document(request.user, obj).allowed

    def save_model(self, request, obj, form, change):
        changed_data = list(getattr(form, "changed_data", []) or [])
        before = {}
        if change and obj.pk:
            previous = PhieuXuat.objects.for_current().select_related("nhan_vien_nhan", "muc_tieu_nhan").filter(pk=obj.pk).first()
            policy = InventoryDocumentPolicy.can_change_document(request.user, previous)
            if not policy.allowed:
                raise PermissionDenied(policy.message)
            if previous:
                if previous.trang_thai != PhieuXuat.TrangThai.DRAFT:
                    raise ValidationError(_("Không được sửa trực tiếp phiếu xuất đã ghi sổ hoặc đã hủy."))
                before = {
                    "ma_phieu": previous.ma_phieu,
                    "loai_xuat": previous.loai_xuat,
                    "trang_thai": previous.trang_thai,
                    "trang_thai_thanh_toan": previous.trang_thai_thanh_toan,
                    "nhan_vien_nhan": str(previous.nhan_vien_nhan) if previous.nhan_vien_nhan_id else "",
                    "muc_tieu_nhan": str(previous.muc_tieu_nhan) if previous.muc_tieu_nhan_id else "",
                    "tong_tien_phai_thu": str(previous.tong_tien_phai_thu),
                }
        super().save_model(request, obj, form, change)
        after = {
            "ma_phieu": obj.ma_phieu,
            "loai_xuat": obj.loai_xuat,
            "trang_thai": obj.trang_thai,
            "trang_thai_thanh_toan": obj.trang_thai_thanh_toan,
            "nhan_vien_nhan": str(obj.nhan_vien_nhan) if obj.nhan_vien_nhan_id else "",
            "muc_tieu_nhan": str(obj.muc_tieu_nhan) if obj.muc_tieu_nhan_id else "",
            "tong_tien_phai_thu": str(obj.tong_tien_phai_thu),
        }
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name="PhieuXuat",
            object_id=obj.pk,
            note="Cập nhật phiếu xuất kho qua admin." if change else "Tạo phiếu xuất kho qua admin.",
            changes={"before": before, "after": after, "changed_fields": changed_data},
        )

    def delete_model(self, request, obj):
        policy = InventoryDocumentPolicy.can_delete_document(request.user, obj)
        if not policy.allowed:
            raise PermissionDenied(policy.message)
        object_id = obj.pk
        snapshot = {
            "ma_phieu": obj.ma_phieu,
            "trang_thai": obj.trang_thai,
            "loai_xuat": obj.loai_xuat,
            "nhan_vien_nhan": str(obj.nhan_vien_nhan) if obj.nhan_vien_nhan_id else "",
            "muc_tieu_nhan": str(obj.muc_tieu_nhan) if obj.muc_tieu_nhan_id else "",
        }
        super().delete_model(request, obj)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="PhieuXuat",
            object_id=object_id,
            note="Xóa phiếu xuất kho nháp qua admin.",
            changes=snapshot,
        )

    def delete_queryset(self, request, queryset):
        safe_queryset = PhieuXuat.objects.selected_from_queryset(queryset)
        non_draft_count = safe_queryset.exclude(trang_thai=PhieuXuat.TrangThai.DRAFT).count()
        if non_draft_count:
            self.message_user(request, _("Chỉ được xóa hàng loạt phiếu xuất còn ở trạng thái Nháp."), messages.ERROR)
            return
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            snapshots = []
            for item in locked_queryset:
                policy = InventoryDocumentPolicy.can_delete_document(request.user, item)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                snapshots.append({"id": item.pk, "ma_phieu": item.ma_phieu, "trang_thai": item.trang_thai, "loai_xuat": item.loai_xuat})
            if not snapshots:
                return
            super().delete_queryset(request, safe_queryset.filter(pk__in=[item["id"] for item in snapshots]))
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="PhieuXuat",
            object_id="bulk-delete",
            note=f"Xóa hàng loạt {len(snapshots)} phiếu xuất nháp qua admin.",
            changes={"items": snapshots},
        )

    @admin.action(description="Ghi sổ phiếu xuất kho")
    def post_inventory_documents(self, request, queryset):
        success_count = 0
        safe_queryset = PhieuXuat.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update().prefetch_related("chi_tiet")
            for document in locked_queryset:
                policy = InventoryDocumentPolicy.can_post_document(request.user, document)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                try:
                    InventoryDocumentUseCase.post_inventory_document(document, user=request.user)
                    success_count += 1
                    record_inventory_admin_audit_action(
                        request,
                        action=AuditLog.Action.UPDATE,
                        model_name="PhieuXuat",
                        object_id=document.pk,
                        note="Ghi sổ phiếu xuất kho qua admin action.",
                        changes={"ma_phieu": document.ma_phieu, "from_action": "post_inventory_documents"},
                    )
                except InventoryDocumentPostingError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
        if success_count:
            self.message_user(request, f"Đã ghi sổ {success_count} phiếu xuất.", messages.SUCCESS)

    @admin.action(description="Hủy phiếu xuất kho đã ghi sổ")
    def void_inventory_documents(self, request, queryset):
        reason = (request.POST.get("void_reason") or "").strip()
        if not reason:
            self.message_user(request, _("Phải nhập lý do khi hủy phiếu xuất kho."), messages.ERROR)
            return
        success_count = 0
        safe_queryset = PhieuXuat.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            for document in locked_queryset:
                policy = InventoryDocumentPolicy.can_void_document(request.user, document)
                if not policy.allowed:
                    self.message_user(request, policy.message, messages.ERROR)
                    continue
                try:
                    InventoryDocumentUseCase.void_inventory_document(
                        document,
                        reason=reason,
                        user=request.user,
                    )
                    success_count += 1
                    record_inventory_admin_audit_action(
                        request,
                        action=AuditLog.Action.UPDATE,
                        model_name="PhieuXuat",
                        object_id=document.pk,
                        note="Hủy phiếu xuất kho đã ghi sổ qua admin action.",
                        changes={"ma_phieu": document.ma_phieu, "reason": reason, "from_action": "void_inventory_documents"},
                    )
                except InventoryDocumentPostingError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
        if success_count:
            self.message_user(request, f"Đã hủy {success_count} phiếu xuất.", messages.SUCCESS)

    def ma_phieu_hien_thi(self, obj):
        return format_html('<strong>{}</strong><br><small style="color:#64748b;">ID #{}</small>', obj.ma_phieu, obj.pk)
    ma_phieu_hien_thi.short_description = _("Mã phiếu")
    ma_phieu_hien_thi.admin_order_field = "ma_phieu"

    def trang_thai_hien_thi(self, obj):
        if obj.trang_thai == PhieuXuat.TrangThai.POSTED:
            return format_html('<span style="color:#059669;font-weight:800;">Đã ghi sổ</span>')
        if obj.trang_thai == PhieuXuat.TrangThai.VOIDED:
            return format_html('<span style="color:#dc2626;font-weight:800;">Đã hủy</span>')
        return format_html('<span style="color:#d97706;font-weight:800;">Nháp</span>')
    trang_thai_hien_thi.short_description = _("Trạng thái")
    trang_thai_hien_thi.admin_order_field = "trang_thai"

    def loai_xuat_hien_thi(self, obj):
        label = obj.get_loai_xuat_display()
        if obj.loai_xuat == "BAN_TRU_LUONG":
            return format_html('<strong style="color:#7c3aed;">{}</strong><br><small>Cần đối soát payroll</small>', label)
        if obj.loai_xuat == "CONG_CU":
            return format_html('<strong style="color:#0f766e;">{}</strong><br><small>Gắn mục tiêu</small>', label)
        return format_html('<strong>{}</strong>', label)
    loai_xuat_hien_thi.short_description = _("Hình thức xuất")
    loai_xuat_hien_thi.admin_order_field = "loai_xuat"

    def nguoi_nhan_hien_thi(self, obj):
        if obj.loai_xuat in ["CAP_PHAT", "BAN_TRU_LUONG"]:
            if obj.nhan_vien_nhan_id:
                return format_html('<a href="../../users/nhanvien/{}/change/" style="font-weight:800;">{}</a>', obj.nhan_vien_nhan_id, obj.nhan_vien_nhan)
            return format_html('<span style="color:#dc2626;font-weight:800;">Thiếu nhân viên nhận</span>')
        if obj.loai_xuat == "CONG_CU":
            if obj.muc_tieu_nhan_id:
                return format_html('<a href="../../clients/muctieu/{}/change/" style="font-weight:800;">{}</a>', obj.muc_tieu_nhan_id, obj.muc_tieu_nhan)
            return format_html('<span style="color:#dc2626;font-weight:800;">Thiếu mục tiêu nhận</span>')
        return _("Xuất hủy/khác")
    nguoi_nhan_hien_thi.short_description = _("Đối tượng nhận")

    def tong_hop_vat_tu_hien_thi(self, obj):
        return format_html(
            '<span>Dòng: <strong>{}</strong></span><br><span>Loại vật tư: <strong>{}</strong></span><br><span>Số lượng: <strong>{}</strong></span>',
            getattr(obj, "line_count", 0) or 0,
            getattr(obj, "material_count", 0) or 0,
            getattr(obj, "total_quantity", 0) or 0,
        )
    tong_hop_vat_tu_hien_thi.short_description = _("Tổng hợp xuất")

    def thanh_toan_hien_thi(self, obj):
        amount = int(obj.tong_tien_phai_thu or 0)
        if obj.loai_xuat == "BAN_TRU_LUONG":
            return format_html('<strong>{:,} đ</strong><br><small>{}</small>', amount, obj.get_trang_thai_thanh_toan_display())
        return format_html('<span>{}</span>', obj.get_trang_thai_thanh_toan_display())
    thanh_toan_hien_thi.short_description = _("Khấu trừ")
    thanh_toan_hien_thi.admin_order_field = "tong_tien_phai_thu"

    def ngay_xuat_format(self, obj):
        return timezone.localtime(obj.ngay_xuat).strftime('%d/%m/%Y %H:%M') if obj.ngay_xuat else ""
    ngay_xuat_format.short_description = _("Ngày xuất kho")
    ngay_xuat_format.admin_order_field = "ngay_xuat"

    def thao_tac_nhanh(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" href="../vattu/">Vật tư</a> '
            '<a class="button" href="../phieunhap/">Nhập</a> '
            '<a class="button" href="../congcutaimuctieu/">CCHT mục tiêu</a>',
            f"{obj.pk}/change/",
        )
    thao_tac_nhanh.short_description = _("Thao tác")


@admin.register(CongCuTaiMucTieu)
class CongCuTaiMucTieuAdmin(admin.ModelAdmin):
    """Theo dõi công cụ hỗ trợ đang bàn giao cho từng mục tiêu bảo vệ."""
    change_list_template = "admin/inventory/congcutaimuctieu/change_list.html"
    list_display = (
        "muc_tieu_hien_thi",
        "vat_tu_hien_thi",
        "so_luong_hien_thi",
        "ton_kho_lien_quan_hien_thi",
        "ngay_cap_gan_nhat_hien_thi",
        "thao_tac_nhanh",
    )
    list_filter = (TargetToolOperationalFilter, "muc_tieu", "vat_tu__loai_vat_tu", "vat_tu")
    list_select_related = ("muc_tieu", "vat_tu", "vat_tu__loai_vat_tu")
    search_fields = ("muc_tieu__ten_muc_tieu", "vat_tu__ten_vat_tu", "vat_tu__loai_vat_tu__ten_loai")
    autocomplete_fields = ("muc_tieu", "vat_tu")
    list_per_page = 25
    save_on_top = True
    date_hierarchy = "ngay_cap_gan_nhat"
    fieldsets = (
        ("Thông tin bàn giao", {"fields": ("muc_tieu", "vat_tu", "so_luong_dang_giu")}),
        ("Ghi chú thủ kho", {"fields": (), "description": "Công cụ tại mục tiêu là số lượng đang bàn giao thực tế tại hiện trường. Khi thu hồi/cấp mới nên đi qua phiếu xuất/thu hồi hoặc biên bản đối soát để giữ được lịch sử kho."}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("muc_tieu", "vat_tu", "vat_tu__loai_vat_tu")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_congcutaimuctieu_export_csv",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        today = timezone.localdate()
        summary = queryset.aggregate(
            total_rows=Count("id", distinct=True),
            total_quantity=Coalesce(Sum("so_luong_dang_giu"), Value(0), output_field=IntegerField()),
            active_targets=Count("muc_tieu", distinct=True),
            active_materials=Count("vat_tu", distinct=True),
            zero_quantity=Count("id", filter=Q(so_luong_dang_giu__lte=0), distinct=True),
            today_update=Count("id", filter=Q(ngay_cap_gan_nhat=today), distinct=True),
            month_update=Count(
                "id",
                filter=Q(ngay_cap_gan_nhat__year=today.year, ngay_cap_gan_nhat__month=today.month),
                distinct=True,
            ),
            material_low_stock=Count(
                "id",
                filter=Q(vat_tu__so_luong_ton__lte=F("vat_tu__muc_canh_bao")),
                distinct=True,
            ),
            material_out_stock=Count("id", filter=Q(vat_tu__so_luong_ton__lte=0), distinct=True),
            no_material_category=Count("id", filter=Q(vat_tu__loai_vat_tu__isnull=True), distinct=True),
            payroll_deductible=Count("id", filter=Q(vat_tu__gia_ban__gt=0), distinct=True),
        )
        query_string = request.META.get("QUERY_STRING", "")
        export_url = "export-csv/" + (f"?{query_string}" if query_string else "")
        extra_context.update({
            "target_tool_summary": summary,
            "target_tool_export_url": export_url,
            "target_tool_links": {
                "add": "add/",
                "materials": "../vattu/",
                "categories": "../loaivattu/",
                "stock_report": "/inventory/bao-cao-ton/",
                "dashboard": "/inventory/",
                "receipts": "../phieunhap/",
                "issues": "../phieuxuat/",
                "targets": "../../clients/muctieu/",
            },
        })
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="scmdpro-cong-cu-tai-muc-tieu.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Mục tiêu",
            "Vật tư/CCHT",
            "Phân loại",
            "Đơn vị tính",
            "Số lượng đang giữ",
            "Tồn kho hiện tại",
            "Mức cảnh báo",
            "Giá vốn",
            "Giá trừ lương",
            "Ngày cập nhật gần nhất",
        ])
        for item in queryset:
            material = item.vat_tu
            writer.writerow([
                item.pk,
                item.muc_tieu.ten_muc_tieu if item.muc_tieu_id else "",
                material.ten_vat_tu if material else "",
                material.loai_vat_tu.ten_loai if material and material.loai_vat_tu_id else "",
                material.don_vi_tinh if material else "",
                item.so_luong_dang_giu,
                material.so_luong_ton if material else "",
                material.muc_canh_bao if material else "",
                int(material.gia_nhap or 0) if material else 0,
                int(material.gia_ban or 0) if material else 0,
                item.ngay_cap_gan_nhat.strftime("%d/%m/%Y") if item.ngay_cap_gan_nhat else "",
            ])
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.ACCESS,
            model_name="CongCuTaiMucTieu",
            object_id="export-csv",
            note=f"Xuất CSV công cụ tại mục tiêu qua admin. Số dòng: {queryset.count()}.",
            changes={"path": request.get_full_path()},
        )
        return response

    def save_model(self, request, obj, form, change):
        changed_data = list(getattr(form, "changed_data", []) or [])
        before = {}
        if change and obj.pk:
            previous = CongCuTaiMucTieu.objects.for_current().select_related("muc_tieu", "vat_tu").filter(pk=obj.pk).first()
            if previous:
                before = {
                    "muc_tieu": str(previous.muc_tieu),
                    "vat_tu": str(previous.vat_tu),
                    "so_luong_dang_giu": previous.so_luong_dang_giu,
                }
        super().save_model(request, obj, form, change)
        after = {
            "muc_tieu": str(obj.muc_tieu),
            "vat_tu": str(obj.vat_tu),
            "so_luong_dang_giu": obj.so_luong_dang_giu,
        }
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            model_name="CongCuTaiMucTieu",
            object_id=obj.pk,
            note="Cập nhật công cụ tại mục tiêu qua admin." if change else "Tạo bản ghi công cụ tại mục tiêu qua admin.",
            changes={"before": before, "after": after, "changed_fields": changed_data},
        )

    def delete_model(self, request, obj):
        object_id = obj.pk
        snapshot = {
            "muc_tieu": str(obj.muc_tieu),
            "vat_tu": str(obj.vat_tu),
            "so_luong_dang_giu": obj.so_luong_dang_giu,
        }
        super().delete_model(request, obj)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="CongCuTaiMucTieu",
            object_id=object_id,
            note="Xóa bản ghi công cụ tại mục tiêu qua admin.",
            changes=snapshot,
        )

    def delete_queryset(self, request, queryset):
        safe_queryset = CongCuTaiMucTieu.objects.selected_from_queryset(queryset)
        with transaction.atomic():
            locked_queryset = safe_queryset.select_for_update()
            snapshots = [
                {
                    "id": item.pk,
                    "muc_tieu": str(item.muc_tieu),
                    "vat_tu": str(item.vat_tu),
                    "so_luong_dang_giu": item.so_luong_dang_giu,
                }
                for item in locked_queryset
            ]
            if not snapshots:
                self.message_user(request, _("Không có công cụ tại mục tiêu nào trong phạm vi được phép."), messages.ERROR)
                return
            super().delete_queryset(request, locked_queryset)
        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.DELETE,
            model_name="CongCuTaiMucTieu",
            object_id="bulk-delete",
            note=f"Xóa hàng loạt {len(snapshots)} bản ghi công cụ tại mục tiêu qua admin.",
            changes={"items": snapshots},
        )

    def muc_tieu_hien_thi(self, obj):
        return format_html('<a href="../../clients/muctieu/{}/change/" style="font-weight:800;">{}</a>', obj.muc_tieu_id, obj.muc_tieu)
    muc_tieu_hien_thi.short_description = _("Mục tiêu")
    muc_tieu_hien_thi.admin_order_field = "muc_tieu__ten_muc_tieu"

    def vat_tu_hien_thi(self, obj):
        material = obj.vat_tu
        category = material.loai_vat_tu.ten_loai if material and material.loai_vat_tu_id else "Thiếu phân loại"
        return format_html(
            '<a href="../vattu/{}/change/" style="font-weight:800;">{}</a><br><small style="color:#64748b;">{}</small>',
            obj.vat_tu_id,
            material.ten_vat_tu,
            category,
        )
    vat_tu_hien_thi.short_description = _("Vật tư/CCHT")
    vat_tu_hien_thi.admin_order_field = "vat_tu__ten_vat_tu"

    def so_luong_hien_thi(self, obj):
        quantity = obj.so_luong_dang_giu or 0
        unit = obj.vat_tu.don_vi_tinh if obj.vat_tu_id else ""
        if quantity <= 0:
            return format_html('<strong style="color:#dc2626;">{} {}</strong><br><small>Cần đối soát/thu hồi</small>', quantity, unit)
        return format_html('<strong style="color:#0f766e;">{} {}</strong><br><small>Đang giữ tại mục tiêu</small>', quantity, unit)
    so_luong_hien_thi.short_description = _("Số lượng thực tế")
    so_luong_hien_thi.admin_order_field = "so_luong_dang_giu"

    def ton_kho_lien_quan_hien_thi(self, obj):
        material = obj.vat_tu
        stock = material.so_luong_ton or 0
        threshold = material.muc_canh_bao or 0
        if stock <= 0:
            return format_html('<strong style="color:#dc2626;">{} tồn kho</strong><br><small>Đã hết tồn tổng</small>', stock)
        if stock <= threshold:
            return format_html('<strong style="color:#d97706;">{} tồn kho</strong><br><small>Dưới mức cảnh báo {}</small>', stock, threshold)
        return format_html('<strong style="color:#059669;">{} tồn kho</strong><br><small>Mức cảnh báo {}</small>', stock, threshold)
    ton_kho_lien_quan_hien_thi.short_description = _("Tồn kho tổng")
    ton_kho_lien_quan_hien_thi.admin_order_field = "vat_tu__so_luong_ton"

    def ngay_cap_gan_nhat_hien_thi(self, obj):
        return obj.ngay_cap_gan_nhat.strftime('%d/%m/%Y') if obj.ngay_cap_gan_nhat else ""
    ngay_cap_gan_nhat_hien_thi.short_description = _("Ngày cập nhật")
    ngay_cap_gan_nhat_hien_thi.admin_order_field = "ngay_cap_gan_nhat"

    def thao_tac_nhanh(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" href="../phieuxuat/?muc_tieu_nhan__id__exact={}">Phiếu xuất</a> '
            '<a class="button" href="../vattu/?id__exact={}">Vật tư</a> '
            '<a class="button" href="../../clients/muctieu/{}/change/">Mục tiêu</a>',
            f"{obj.pk}/change/",
            obj.muc_tieu_id,
            obj.vat_tu_id,
            obj.muc_tieu_id,
        )
    thao_tac_nhanh.short_description = _("Thao tác")


class ChiTietPhieuThuHoiInline(admin.TabularInline):
    model = ChiTietPhieuThuHoi
    extra = 1
    autocomplete_fields = ["vat_tu"]
    raw_id_fields = ["chi_tiet_phieu_xuat"]
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            fields.extend(["chi_tiet_phieu_xuat", "vat_tu", "so_luong_thu_hoi", "so_luong_nhap_lai_kho", "so_luong_mat_hong", "tinh_trang", "ghi_chu"])
        return tuple(dict.fromkeys(fields))


@admin.register(PhieuThuHoi)
class PhieuThuHoiAdmin(admin.ModelAdmin):
    list_display = ("ma_phieu", "nhan_vien", "ngay_thu_hoi", "nguoi_thu_hoi", "trang_thai", "posted_at", "voided_at")
    list_filter = ("trang_thai", ("ngay_thu_hoi", admin.DateFieldListFilter), "nguoi_thu_hoi")
    search_fields = ("ma_phieu", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "quyet_dinh_nghi_viec__so_quyet_dinh", "ghi_chu")
    autocomplete_fields = ("nhan_vien", "nguoi_thu_hoi", "quyet_dinh_nghi_viec", "offboarding_checklist")
    inlines = [ChiTietPhieuThuHoiInline]
    readonly_fields = ("posted_at", "voided_at", "created_at", "updated_at")
    actions = ("post_recovery_documents", "void_recovery_documents")
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            fields.extend(["ma_phieu", "nhan_vien", "quyet_dinh_nghi_viec", "offboarding_checklist", "ngay_thu_hoi", "nguoi_thu_hoi", "file_bien_ban", "trang_thai", "ghi_chu"])
        return tuple(dict.fromkeys(fields))

    def has_delete_permission(self, request, obj=None):
        if obj and obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not AssetRecoveryPermissionPolicy.can_create(request.user):
            raise PermissionDenied(_("Không có quyền tạo/cập nhật phiếu thu hồi tài sản."))
        super().save_model(request, obj, form, change)

    @admin.action(description="Ghi sổ phiếu thu hồi đã chọn")
    def post_recovery_documents(self, request, queryset):
        posted = 0
        for document in PhieuThuHoi.objects.selected_from_queryset(queryset):
            try:
                PostAssetRecoveryUseCase.execute(phieu_thu_hoi=document, actor=request.user)
                posted += 1
            except (AssetRecoveryError, PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{document.ma_phieu}: {exc}", messages.ERROR)
        if posted:
            self.message_user(request, f"Đã ghi sổ {posted} phiếu thu hồi.", messages.SUCCESS)

    @admin.action(description="Hủy/reversal phiếu thu hồi đã chọn")
    def void_recovery_documents(self, request, queryset):
        voided = 0
        reason = request.POST.get("void_reason") or "Void phiếu thu hồi qua admin"
        for document in PhieuThuHoi.objects.selected_from_queryset(queryset):
            try:
                VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=document, reason=reason, actor=request.user)
                voided += 1
            except (AssetRecoveryError, PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{document.ma_phieu}: {exc}", messages.ERROR)
        if voided:
            self.message_user(request, f"Đã hủy {voided} phiếu thu hồi.", messages.SUCCESS)


@admin.register(BienBanMatHongVatTu)
class BienBanMatHongVatTuAdmin(admin.ModelAdmin):
    list_display = ("id", "nhan_vien", "vat_tu", "so_luong", "tong_tien", "trang_thai", "khoan_khau_tru")
    list_filter = ("trang_thai", "vat_tu", "nhan_vien")
    search_fields = ("nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "vat_tu__ten_vat_tu", "ly_do", "phieu_thu_hoi__ma_phieu")
    autocomplete_fields = ("phieu_thu_hoi", "nhan_vien", "vat_tu", "khoan_khau_tru", "nguoi_duyet")
    raw_id_fields = ("chi_tiet_thu_hoi",)
    readonly_fields = ("tong_tien", "khoan_khau_tru", "ngay_duyet", "created_at", "updated_at")
    actions = ("approve_damage_reports",)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.trang_thai in (BienBanMatHongVatTu.TrangThai.APPROVED, BienBanMatHongVatTu.TrangThai.APPLIED, BienBanMatHongVatTu.TrangThai.CANCELLED):
            fields.extend(["phieu_thu_hoi", "chi_tiet_thu_hoi", "nhan_vien", "vat_tu", "so_luong", "don_gia_khau_tru", "ly_do", "file_minh_chung", "trang_thai", "ghi_chu"])
        return tuple(dict.fromkeys(fields))

    @admin.action(description="Duyệt biên bản mất/hỏng và tạo khoản khấu trừ")
    def approve_damage_reports(self, request, queryset):
        approved = 0
        for report in BienBanMatHongVatTu.objects.selected_from_queryset(queryset):
            try:
                ApproveAssetDamageReportUseCase.execute(bien_ban=report, actor=request.user)
                approved += 1
            except (AssetRecoveryError, PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"Biên bản {report.pk}: {exc}", messages.ERROR)
        if approved:
            self.message_user(request, f"Đã duyệt {approved} biên bản mất/hỏng.", messages.SUCCESS)
