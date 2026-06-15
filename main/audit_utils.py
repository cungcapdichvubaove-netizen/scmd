import functools

from django.conf import settings

from main.models import AuditLog
from main.services.audit_service import get_client_ip, record_admin_audit_action


def build_export_audit_changes(request, changes=None):
    payload = {
        "query_params": request.GET.dict(),
    }
    if changes:
        payload.update(changes)
    return payload


def record_export_audit(request, *, module, model_name, note, object_id=None, changes=None):
    AuditLog.objects.create(
        user=request.user,
        tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
        action=AuditLog.Action.EXECUTE,
        module=module,
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        changes=build_export_audit_changes(request, changes),
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        note=note,
        status="SUCCESS",
    )


def export_audit_log(
    *,
    module,
    model_name,
    note,
    object_id_resolver=None,
    changes_resolver=None,
):
    """
    Decorator cho cac view export Excel/PDF/CSV de ghi audit log compliance.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            status_code = getattr(response, "status_code", 200)
            if status_code >= 400:
                return response

            object_id = (
                object_id_resolver(request, *args, **kwargs)
                if callable(object_id_resolver)
                else object_id_resolver
            )
            changes = (
                changes_resolver(request, *args, **kwargs)
                if callable(changes_resolver)
                else changes_resolver
            )
            record_export_audit(
                request,
                module=module,
                model_name=model_name,
                note=note,
                object_id=object_id,
                changes=changes,
            )
            return response

        return wrapper

    return decorator
