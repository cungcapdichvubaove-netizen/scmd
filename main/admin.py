# -*- coding: utf-8 -*-
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, CompanyInfo, WorkerHeartbeat


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "action",
        "module",
        "model_name",
        "status",
        "verification_status",
    )
    list_filter = ("action", "module", "status", "timestamp")
    search_fields = ("object_id", "note", "user__username")
    readonly_fields = (
        "timestamp",
        "user",
        "action",
        "module",
        "model_name",
        "object_id",
        "changes",
        "checksum",
        "verification_status",
        "ip_address",
        "user_agent",
    )

    def verification_status(self, obj):
        if not obj.checksum:
            return format_html('<span style="color: gray;">{}</span>', _("N/A"))

        calculated_checksum = obj.generate_checksum()
        if obj.checksum == calculated_checksum:
            return format_html(
                '<span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: bold;">✅ {}</span>',
                _("Hợp lệ"),
            )
        return format_html(
            '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: bold;">⚠️ {}</span>',
            _("Bị chỉnh sửa"),
        )

    verification_status.short_description = _("Kiểm tra toàn vẹn")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(WorkerHeartbeat)
class WorkerHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("hostname", "last_ping", "is_active")
    list_filter = ("is_active", "last_ping")
    search_fields = ("hostname",)
    readonly_fields = ("tenant_id", "hostname", "last_ping", "is_active")

    def has_add_permission(self, request):
        return False



@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    """Singleton admin for company/legal information used in exports."""

    change_list_template = "admin/main/companyinfo/change_list.html"
    fieldsets = (
        (_("Thông tin nhận diện"), {
            "fields": ("ten_cong_ty", "ten_phap_ly", "ma_so_thue", "logo")
        }),
        (_("Thông tin liên hệ"), {
            "fields": ("dia_chi", "dien_thoai", "hotline", "email", "website")
        }),
        (_("Thông tin pháp lý / mẫu biểu"), {
            "fields": (
                "nguoi_dai_dien",
                "chuc_vu_nguoi_dai_dien",
                "so_tai_khoan",
                "ngan_hang",
                "ghi_chu",
            )
        }),
        (_("Hệ thống"), {
            "classes": ("collapse",),
            "fields": ("tenant_id", "updated_at"),
        }),
    )
    list_display = (
        "company_identity",
        "tax_code_display",
        "contact_display",
        "email_display",
        "updated_display",
        "profile_actions",
    )
    list_display_links = ("company_identity",)
    search_fields = ("ten_cong_ty", "ten_phap_ly", "ma_so_thue", "dien_thoai", "hotline", "email")
    readonly_fields = ("tenant_id", "updated_at")
    list_per_page = 20

    def has_add_permission(self, request):
        # Allow adding only if no CompanyInfo object exists for the current tenant.
        # CompanyInfo.objects is already tenant-scoped due to TenantScopedModel.
        return not CompanyInfo.objects.exists()

    def changelist_view(self, request, extra_context=None):
        # For a singleton model, if an object exists, redirect to its change form.
        # CompanyInfo.objects is already tenant-scoped due to TenantScopedModel.
        obj = CompanyInfo.objects.first()
        if obj:
            return redirect(reverse("admin:main_companyinfo_change", args=[obj.pk]))
        # If no object exists, proceed to the default changelist view (which will show "Add CompanyInfo").
        return super().changelist_view(request, extra_context)

    @admin.display(description=_("Công ty / Đơn vị"), ordering="ten_cong_ty")
    def company_identity(self, obj):
        return format_html(
            '<div class="scmd-user-cell"><strong>{}</strong><span>{}</span></div>',
            obj.ten_cong_ty,
            obj.ten_phap_ly or _("Chưa có tên pháp lý"),
        )

    @admin.display(description=_("Mã số thuế"), ordering="ma_so_thue")
    def tax_code_display(self, obj):
        return obj.ma_so_thue or "-"

    @admin.display(description=_("Liên hệ"))
    def contact_display(self, obj):
        phone = obj.dien_thoai or "-"
        hotline = f"Hotline: {obj.hotline}" if obj.hotline else ""
        return format_html(
            '<span>{}</span><br><small style="color:#64748b;">{}</small>',
            phone,
            hotline
        )

    @admin.display(description=_("Email"))
    def email_display(self, obj):
        return obj.email or "-"

    @admin.display(description=_("Cập nhật"), ordering="updated_at")
    def updated_display(self, obj):
        """Hiển thị thời gian cập nhật cuối cùng.
        
        FIXED: Tránh sử dụng format specifier trực tiếp trong format_html 
        khi giá trị có thể là SafeString.
        """
        if not obj.updated_at:
            return "-"
        # Định dạng date thành string trước khi đưa vào format_html
        local_dt = timezone.localtime(obj.updated_at)
        date_str = local_dt.strftime("%d/%m/%Y %H:%M")
        return format_html('<span style="color:#64748b;">{}</span>', date_str)

    @admin.display(description=_("Thao tác"))
    def profile_actions(self, obj):
        url = reverse("admin:main_companyinfo_change", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">{}</a>',
            url,
            _("Chỉnh sửa")
        )