# -*- coding: utf-8 -*-
"""Application-layer summary builders for the SCMD Pro admin shell."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connections
from django.db.models import Count, Q
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from main.models import AuditLog, WorkerHeartbeat


ADMIN_DASHBOARD_SUMMARY_CACHE_TTL = 30


def _bounded_count_from_aggregate(value: int | None, limit: int = 999) -> int:
    value = int(value or 0)
    return limit + 1 if value > limit else value


def _safe_admin_url(name: str, fallback: str = "#") -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _build_critical_links() -> list[dict[str, object]]:
    return [
        {"label": "Nhân sự", "url": _safe_admin_url("admin:users_nhanvien_changelist"), "icon": "fas fa-id-card"},
        {"label": "Mục tiêu", "url": _safe_admin_url("admin:clients_muctieu_changelist"), "icon": "fas fa-map-marker-alt"},
        {"label": "Ca trực", "url": _safe_admin_url("admin:operations_phancongcatruc_changelist"), "icon": "fas fa-calendar-check"},
        {"label": "Chấm công", "url": _safe_admin_url("admin:operations_chamcong_changelist"), "icon": "fas fa-location-crosshairs"},
        {"label": "Sự cố", "url": _safe_admin_url("admin:operations_baocaosuco_changelist"), "icon": "fas fa-triangle-exclamation"},
        {"label": "Bảng lương", "url": _safe_admin_url("admin:accounting_bangluongthang_changelist"), "icon": "fas fa-money-bill-wave"},
        {"label": "Sổ quỹ", "url": _safe_admin_url("admin:accounting_soquy_changelist"), "icon": "fas fa-wallet"},
        {"label": "Kho", "url": _safe_admin_url("admin:inventory_vattu_changelist"), "icon": "fas fa-boxes-stacked"},
    ]


def _summary_cache_key(user_id: int | None, include_technical: bool) -> str:
    org_id = getattr(settings, "SCMD_ORGANIZATION_ID", "org")
    return f"main:admin_dashboard_summary:org:{org_id}:user:{user_id or 'anon'}:technical:{int(include_technical)}"


def build_admin_dashboard_summary(user) -> dict[str, object]:
    """Return render-ready admin shell summary with per-user short TTL cache."""

    is_technical_admin = bool(getattr(user, "is_superuser", False))
    critical_links = _build_critical_links()
    if not is_technical_admin:
        return {
            "critical_links": critical_links,
            "attention_items": [],
            "status_label": "",
            "status_tone": "good",
        }

    cache_key = _summary_cache_key(getattr(user, "pk", None), include_technical=True)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    now = timezone.now()
    heartbeat_threshold = now - timedelta(minutes=3)
    user_model = get_user_model()

    try:
        connections["default"].ensure_connection()
        db_status = "online"
    except Exception:
        db_status = "offline"

    worker_stats = WorkerHeartbeat.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True, last_ping__gte=heartbeat_threshold)),
        stale=Count("id", filter=Q(is_active=True, last_ping__lt=heartbeat_threshold)),
    )
    periodic_stats = PeriodicTask.objects.aggregate(
        total=Count("id"),
        enabled=Count("id", filter=Q(enabled=True)),
    )
    task_stats = TaskResult.objects.aggregate(
        total=Count("id"),
        alerts=Count("id", filter=~Q(status="SUCCESS")),
    )
    audit_stats = AuditLog.objects.aggregate(
        total=Count("id"),
        alerts=Count("id", filter=~Q(status="SUCCESS")),
    )
    user_stats = user_model.objects.aggregate(
        staff=Count("id", filter=Q(is_staff=True)),
        superusers=Count("id", filter=Q(is_superuser=True)),
    )

    worker_stale = _bounded_count_from_aggregate(worker_stats["stale"])
    task_alert_count = _bounded_count_from_aggregate(task_stats["alerts"])
    recent_error_count = _bounded_count_from_aggregate(audit_stats["alerts"])
    superuser_count = _bounded_count_from_aggregate(user_stats["superusers"])

    allowed_hosts = getattr(settings, "ALLOWED_HOSTS", []) or []
    debug_enabled = bool(getattr(settings, "DEBUG", False))
    wildcard_hosts = "*" in allowed_hosts

    attention_items = []
    if db_status != "online":
        attention_items.append({"tone": "danger", "title": "Database mất kết nối", "note": "Kiểm tra DB service, credentials và network trước khi thao tác dữ liệu.", "url": "#", "cta": "Kiểm tra ngay"})
    if debug_enabled:
        attention_items.append({"tone": "warning", "title": "DEBUG đang bật", "note": "Chỉ phù hợp local/dev. Production phải tắt DEBUG.", "url": "#", "cta": "Xem cấu hình"})
    if wildcard_hosts:
        attention_items.append({"tone": "warning", "title": "ALLOWED_HOSTS đang mở *", "note": "Rủi ro cấu hình production. Cần giới hạn host hợp lệ.", "url": "#", "cta": "Rà soát"})
    if worker_stale:
        attention_items.append({"tone": "warning", "title": "Worker chậm nhịp", "note": f"{worker_stale} worker quá ngưỡng 3 phút. Kiểm tra queue và tiến trình worker.", "url": _safe_admin_url("admin:main_workerheartbeat_changelist"), "cta": "Mở worker"})
    if task_alert_count:
        attention_items.append({"tone": "danger", "title": "Tác vụ nền lỗi", "note": f"{task_alert_count} kết quả tác vụ khác mã SUCCESS. Cần xem log tác vụ.", "url": _safe_admin_url("admin:django_celery_results_taskresult_changelist"), "cta": "Mở tác vụ"})
    if recent_error_count:
        attention_items.append({"tone": "warning", "title": "Audit log có lỗi", "note": f"{recent_error_count} bản ghi audit khác SUCCESS. Cần rà soát hành động nhạy cảm.", "url": _safe_admin_url("admin:main_auditlog_changelist"), "cta": "Mở log"})
    if superuser_count > 2:
        attention_items.append({"tone": "warning", "title": "Nhiều superuser", "note": f"Đang có {superuser_count} tài khoản quyền tối cao. Nên rà soát định kỳ.", "url": _safe_admin_url("admin:auth_user_changelist"), "cta": "Mở người dùng"})
    if periodic_stats["total"] and not periodic_stats["enabled"]:
        attention_items.append({"tone": "warning", "title": "Không có lịch tác vụ bật", "note": "Celery Beat có task nhưng chưa tác vụ nào được bật.", "url": _safe_admin_url("admin:django_celery_beat_periodictask_changelist"), "cta": "Mở lịch"})
    if not attention_items:
        attention_items.append({"tone": "success", "title": "Không có cảnh báo trọng yếu", "note": "Runtime hiện không ghi nhận điểm nghẽn kỹ thuật nổi bật.", "url": _safe_admin_url("admin:main_auditlog_changelist"), "cta": "Xem audit"})

    system_ok = db_status == "online" and worker_stale == 0 and recent_error_count == 0 and task_alert_count == 0
    summary = {
        "critical_links": critical_links,
        "attention_items": attention_items[:6],
        "status_label": "Ổn định" if system_ok else "Cần xử lý",
        "status_tone": "good" if system_ok else "warn",
    }
    cache.set(cache_key, summary, ADMIN_DASHBOARD_SUMMARY_CACHE_TTL)
    return summary
