# -*- coding: utf-8 -*-
"""Centralized audit write helpers for SCMD Pro.

This module is the SSOT for constructing AuditLog records from interface-layer
requests. Domain apps may choose thin domain-specific wrappers here, but should
not duplicate AuditLog.objects.create(...) payload construction in admin/views.
"""

from django.conf import settings

from main.models import AuditLog


def get_client_ip(request):
    """Return the best-effort client IP from a Django request."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") if request else None


def record_admin_audit_action(
    request,
    *,
    action,
    module,
    model_name,
    object_id="",
    note="",
    changes=None,
):
    """Record an admin-side data mutation through the AuditLog SSOT.

    The helper centralizes common request metadata so app-level admin modules do
    not duplicate AuditLog construction details. It intentionally remains a thin
    wrapper around ``main.models.AuditLog`` to avoid introducing a new framework
    or changing the audit schema.
    """
    user = getattr(request, "user", None)
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
        action=action,
        module=module,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        changes=changes or {},
        ip_address=get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:1000],
        note=note,
        status="SUCCESS",
    )


def record_inventory_admin_audit_action(
    request,
    *,
    action,
    model_name,
    object_id="",
    note="",
    changes=None,
):
    """Record Inventory Admin mutations without duplicating AuditLog payloads."""
    return record_admin_audit_action(
        request,
        action=action,
        module="inventory",
        model_name=model_name,
        object_id=object_id,
        note=note,
        changes=changes,
    )
