# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Infrastructure Utility: Audit Log Decorator.
Description: Tu dong hoa viec ghi nhat ky hau kiem cho Application Layer.
"""

import functools
import logging

from django.conf import settings

from main.models import AuditLog

logger = logging.getLogger(__name__)


def application_audit_log(
    module: str,
    model_name: str,
    action: str = AuditLog.Action.EXECUTE,
    object_id_field: str | None = None,
    object_id_resolver=None,
    note_resolver=None,
):
    """
    Decorator danh cho cac phuong thuc execute() cua use case.
    Ho tro ca contract cu va contract mo rong de tranh vo import-time runtime.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            tenant_id = kwargs.get(
                "tenant_id", getattr(settings, "SCMD_ORGANIZATION_ID", None)
            )
            ip_address = kwargs.get("ip_address")
            user_agent = kwargs.get("user_agent")

            def resolve_object_id(result):
                if callable(object_id_resolver):
                    resolved = object_id_resolver(*args, **kwargs)
                    return str(resolved) if resolved is not None else None
                if object_id_resolver is not None:
                    return str(object_id_resolver)

                if object_id_field:
                    value = kwargs.get(object_id_field)
                    if value is None:
                        for arg in args:
                            if hasattr(arg, object_id_field):
                                value = getattr(arg, object_id_field)
                                break
                    if value is not None:
                        value = getattr(value, "pk", value)
                        return str(value)

                if hasattr(result, "pk"):
                    return str(result.pk)
                if isinstance(result, (list, tuple)) and result:
                    first_item = result[0]
                    if hasattr(first_item, "pk"):
                        return str(first_item.pk)
                    if hasattr(first_item, "id"):
                        return str(first_item.id)
                return None

            def resolve_note(exc=None):
                if callable(note_resolver):
                    return str(note_resolver(*args, **kwargs) or "")
                if note_resolver is not None:
                    return str(note_resolver)
                if exc is not None:
                    return f"Exception: {exc}"
                return ""

            try:
                result = func(*args, **kwargs)
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    module=module,
                    model_name=model_name,
                    object_id=resolve_object_id(result),
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    note=resolve_note(),
                    status="SUCCESS",
                )
                return result
            except Exception as exc:
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    module=module,
                    model_name=model_name,
                    object_id=resolve_object_id(None),
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status="FAILED",
                    note=resolve_note(exc),
                )
                logger.error("[Audit] Logic failure in %s: %s", func.__name__, exc)
                raise

        return wrapper

    return decorator
