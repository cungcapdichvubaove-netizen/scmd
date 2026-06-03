# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, WorkerHeartbeat


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
        return request.user.is_superuser

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
