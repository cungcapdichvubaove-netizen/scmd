from collections import OrderedDict
from datetime import timedelta

from django import template
from django.contrib.auth import get_user_model
from django.db import connections
from django.utils import timezone

from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from main.models import AuditLog, WorkerHeartbeat

register = template.Library()


APP_GROUPS = OrderedDict(
    [
        ("CORE MASTER DATA", {"users", "clients"}),
        ("ACCESS & SECURITY", {"auth", "main", "sessions"}),
        ("OPERATIONS DATA", {"operations"}),
        ("INSPECTION DATA", {"inspection"}),
        ("FINANCE DATA", {"accounting"}),
        ("SYSTEM AUTOMATION", {"django_celery_beat", "django_celery_results", "notifications"}),
        ("MAINTENANCE", {"backup_restore", "reports", "inventory", "workflow"}),
    ]
)

CRITICAL_MODEL_BADGES = {
    "User": ["critical", "permission"],
    "Group": ["critical", "permission"],
    "NhanVien": ["critical", "permission"],
    "PhongBan": ["critical", "config"],
    "ChucDanh": ["critical", "permission"],
    "MucTieu": ["critical", "gps"],
    "HopDong": ["critical", "config"],
    "PhanCongCaTruc": ["critical", "gps"],
    "ChamCong": ["critical", "gps", "payroll"],
    "BangLuongThang": ["critical", "payroll"],
    "ChiTietLuong": ["critical", "payroll"],
    "AuditLog": ["critical", "config"],
    "PeriodicTask": ["critical", "config"],
    "WorkerHeartbeat": ["config"],
}

BADGE_LABELS = {
    "critical": ("Critical", "warning"),
    "permission": ("Permission-sensitive", "lock"),
    "payroll": ("Payroll-sensitive", "payroll"),
    "gps": ("GPS-sensitive", "gps"),
    "config": ("Config-sensitive", "config"),
}


@register.simple_tag
def admin_console_metrics():
    now = timezone.now()
    heartbeat_threshold = now - timedelta(minutes=3)
    recent_audit_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:5]
    worker_qs = WorkerHeartbeat.objects.order_by("hostname")
    recent_task_results = TaskResult.objects.order_by("-date_done")[:5]
    user_model = get_user_model()
    enabled_periodic = PeriodicTask.objects.filter(enabled=True)
    task_alerts = TaskResult.objects.exclude(status="SUCCESS")
    recent_error_count = AuditLog.objects.exclude(status="SUCCESS").count()
    worker_total = worker_qs.count()
    worker_active = worker_qs.filter(is_active=True, last_ping__gte=heartbeat_threshold).count()
    worker_stale = worker_qs.filter(is_active=True, last_ping__lt=heartbeat_threshold).count()
    periodic_total = PeriodicTask.objects.count()
    periodic_enabled = enabled_periodic.count()
    task_result_total = TaskResult.objects.count()

    try:
        connections["default"].ensure_connection()
        db_status = "online"
    except Exception:
        db_status = "offline"

    system_ok = db_status == "online" and worker_stale == 0 and recent_error_count == 0
    quick_links = [
        {
            "label": "Người dùng & Nhóm quyền",
            "url": "/admin/auth/user/",
            "icon": "fas fa-users-cog",
            "badge": user_model.objects.filter(is_staff=True).count(),
        },
        {
            "label": "Nhật ký hệ thống",
            "url": "/admin/main/auditlog/",
            "icon": "fas fa-clipboard-list",
            "badge": recent_error_count,
        },
        {
            "label": "Giám sát worker",
            "url": "/admin/main/workerheartbeat/",
            "icon": "fas fa-heartbeat",
            "badge": worker_active,
        },
        {
            "label": "Lịch tác vụ",
            "url": "/admin/django_celery_beat/periodictask/",
            "icon": "fas fa-calendar-alt",
            "badge": periodic_enabled,
        },
    ]

    return {
        "db_status": db_status,
        "worker_total": worker_total,
        "worker_active": worker_active,
        "worker_stale": worker_stale,
        "periodic_total": periodic_total,
        "periodic_enabled": periodic_enabled,
        "task_result_total": task_result_total,
        "recent_errors": recent_error_count,
        "audit_log_total": AuditLog.objects.count(),
        "staff_count": user_model.objects.filter(is_staff=True).count(),
        "superuser_count": user_model.objects.filter(is_superuser=True).count(),
        "recent_audit_logs": recent_audit_logs,
        "recent_task_results": recent_task_results,
        "recent_workers": worker_qs[:5],
        "task_alerts": task_alerts.count(),
        "system_ok": system_ok,
        "status_label": "Toàn hệ thống ổn định" if system_ok else "Cần theo dõi",
        "status_tone": "good" if system_ok else "warn",
        "last_updated_label": "Cập nhật theo runtime hiện tại",
        "quick_links": quick_links,
    }


@register.simple_tag
def admin_sidebar_runtime():
    return {
        "periodic_enabled": PeriodicTask.objects.filter(enabled=True).count(),
        "task_alerts": TaskResult.objects.exclude(status="SUCCESS").count(),
    }


@register.simple_tag
def group_admin_apps(app_list):
    grouped = []
    assigned_labels = set()

    for section_title, app_labels in APP_GROUPS.items():
        apps = [app for app in app_list if app["app_label"] in app_labels]
        if apps:
            grouped.append({"title": section_title, "apps": apps})
            assigned_labels.update(app_labels)

    leftovers = [app for app in app_list if app["app_label"] not in assigned_labels]
    if leftovers:
        grouped.append({"title": "OTHER SYSTEM AREAS", "apps": leftovers})

    return grouped


@register.simple_tag
def model_badges(model):
    object_name = model.get("object_name")
    badge_keys = CRITICAL_MODEL_BADGES.get(object_name, [])
    return [BADGE_LABELS[key] for key in badge_keys]
