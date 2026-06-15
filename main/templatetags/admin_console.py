from collections import OrderedDict
from datetime import timedelta
from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from main.application.admin_dashboard_summary import build_admin_dashboard_summary
from main.models import AuditLog, WorkerHeartbeat
from main.services.operations_ux import AdminOperationsUXProvider

register = template.Library()


APP_GROUPS = OrderedDict(
    [
        ("Nhân sự", {"users"}),
        ("Khách hàng & mục tiêu", {"clients"}),
        ("Vận hành", {"operations", "inspection"}),
        ("Kho & cấp phát", {"inventory"}),
        ("Tài chính", {"accounting"}),
        ("Báo cáo & quy trình", {"workflow", "reports"}),
        ("Quản trị hệ thống", {"auth", "main", "sessions", "django_celery_beat", "django_celery_results", "notifications"}),
    ]
)

WORKSPACE_SECTIONS = [
    {
        "title": "Việc cần xử lý",
        "note": "Mở các danh sách có khả năng phát sinh việc tồn đọng.",
        "links": [
            ("Nhân viên chưa hoàn thiện", "admin:users_nhanvien_changelist", "fas fa-id-card", {"staff_ops": "missing_site"}),
            ("Ca trực hôm nay", "admin:operations_phancongcatruc_changelist", "fas fa-calendar-check", {"assignment_quality": "today"}),
            ("Sự cố đang xử lý", "admin:operations_baocaosuco_changelist", "fas fa-triangle-exclamation", {"incident_ops": "open"}),
            ("Tuần tra", "admin:inspection_luottuantra_changelist", "fas fa-route", {"ops": "active"}),
        ],
    },
    {
        "title": "Nhân sự",
        "note": "Hồ sơ, tài khoản và phân bổ nhân sự vận hành.",
        "links": [
            ("Danh sách nhân viên", "admin:users_nhanvien_changelist", "fas fa-users", {}),
            ("Tài khoản đăng nhập", "admin:auth_user_changelist", "fas fa-user-lock", {}),
            ("Phòng ban", "admin:users_phongban_changelist", "fas fa-sitemap", {}),
            ("Chức danh", "admin:users_chucdanh_changelist", "fas fa-user-tag", {}),
        ],
    },
    {
        "title": "Khách hàng & mục tiêu",
        "note": "Hợp đồng, mục tiêu và phạm vi dịch vụ.",
        "links": [
            ("Mục tiêu", "admin:clients_muctieu_changelist", "fas fa-map-marker-alt", {"target_quality": "missing_gps"}),
            ("Hợp đồng", "admin:clients_hopdong_changelist", "fas fa-file-contract", {"contract_quality": "expiring_30"}),
            ("Khách hàng tiềm năng", "admin:clients_khachhangtiemnang_changelist", "fas fa-handshake", {}),
            ("Cơ hội kinh doanh", "admin:clients_cohoikinhdoanh_changelist", "fas fa-chart-line", {}),
        ],
    },
    {
        "title": "Kho & tài chính",
        "note": "Cấp phát, tồn kho, lương và đối soát.",
        "links": [
            ("Vật tư", "admin:inventory_vattu_changelist", "fas fa-boxes-stacked", {"material_issue": "low_stock"}),
            ("Phiếu nhập", "admin:inventory_phieunhap_changelist", "fas fa-right-to-bracket", {"receipt_issue": "draft"}),
            ("Phiếu xuất", "admin:inventory_phieuxuat_changelist", "fas fa-right-from-bracket", {"issue_status": "draft"}),
            ("Bảng lương", "admin:accounting_bangluongthang_changelist", "fas fa-money-check-dollar", {"trang_thai__exact": "DRAFT"}),
        ],
    },
]


ROLE_WORKSPACE_ORDER = {
    "hr": ["Việc cần xử lý", "Nhân sự", "Khách hàng & mục tiêu", "Kho & tài chính"],
    "operations": ["Việc cần xử lý", "Khách hàng & mục tiêu", "Nhân sự", "Kho & tài chính"],
    "accounting": ["Việc cần xử lý", "Kho & tài chính", "Nhân sự", "Khách hàng & mục tiêu"],
    "inventory": ["Việc cần xử lý", "Kho & tài chính", "Khách hàng & mục tiêu", "Nhân sự"],
}


def _workspace_role_bucket(user):
    try:
        role_keys = AdminOperationsUXProvider.role_keys_for_user(user)
    except Exception:
        role_keys = set()
    if role_keys & AdminOperationsUXProvider.HR_KEYS:
        return "hr"
    if role_keys & AdminOperationsUXProvider.OPERATIONS_KEYS:
        return "operations"
    if role_keys & AdminOperationsUXProvider.ACCOUNTING_KEYS:
        return "accounting"
    if role_keys & AdminOperationsUXProvider.INVENTORY_KEYS:
        return "inventory"
    return "operations"


def _ordered_workspace_sections(sections, user=None):
    order = ROLE_WORKSPACE_ORDER.get(_workspace_role_bucket(user), ROLE_WORKSPACE_ORDER["operations"])
    order_map = {title: index for index, title in enumerate(order)}
    return sorted(sections, key=lambda section: order_map.get(section["title"], 99))


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
    "SoQuy": ["critical", "payroll"],
    "VatTu": ["critical", "config"],
    "PhieuNhap": ["critical", "config"],
    "PhieuXuat": ["critical", "payroll"],
    "AuditLog": ["critical", "config"],
    "PeriodicTask": ["critical", "config"],
    "WorkerHeartbeat": ["config"],
}

BADGE_LABELS = {
    "critical": ("Trọng yếu", "warning"),
    "permission": ("Quyền", "lock"),
    "payroll": ("Lương/Tiền", "payroll"),
    "gps": ("GPS/Ảnh", "gps"),
    "config": ("Cấu hình", "config"),
}




def _bounded_count(queryset, limit=999):
    """Return a bounded count for admin-home metrics.

    The admin home must stay fast on large operational datasets. These metrics
    answer whether attention is needed, not exact BI totals, so values above the
    limit are intentionally compressed to keep SQL work predictable.
    """
    try:
        rows = list(queryset.values_list("pk", flat=True)[: limit + 1])
        return limit + 1 if len(rows) > limit else len(rows)
    except Exception:
        return 0


def _bounded_label(value, limit=999):
    return f"{limit}+" if value > limit else value


def _safe_admin_url(name, fallback="#"):
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _workspace_url(name, fallback="#"):
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _with_query(url, params):
    if not params or not url or url == "#":
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


@register.simple_tag
def operations_workspace_sections(user=None):
    """Return business workspace links ordered by the user's likely role.

    This does not change permissions. Jazzmin/Admin will still hide links the
    user cannot access; V6 only changes the order and filter precision so people
    reach work lists faster.
    """
    sections = []
    for section in WORKSPACE_SECTIONS:
        links = []
        for label, url_name, icon, params in section["links"]:
            url = _safe_admin_url(url_name)
            if url and url != "#":
                links.append({"label": label, "url": _with_query(url, params), "icon": icon})
        if links:
            sections.append({"title": section["title"], "note": section["note"], "links": links})
    return _ordered_workspace_sections(sections, user)


@register.simple_tag
def admin_console_metrics(user=None):
    now = timezone.now()
    is_technical_admin = bool(getattr(user, "is_superuser", False))
    heartbeat_threshold = now - timedelta(minutes=3)
    user_model = get_user_model()

    critical_links = [
        {"label": "Nhân sự", "url": _safe_admin_url("admin:users_nhanvien_changelist"), "icon": "fas fa-id-card"},
        {"label": "Mục tiêu", "url": _safe_admin_url("admin:clients_muctieu_changelist"), "icon": "fas fa-map-marker-alt"},
        {"label": "Ca trực", "url": _safe_admin_url("admin:operations_phancongcatruc_changelist"), "icon": "fas fa-calendar-check"},
        {"label": "Chấm công", "url": _safe_admin_url("admin:operations_chamcong_changelist"), "icon": "fas fa-location-crosshairs"},
        {"label": "Sự cố", "url": _safe_admin_url("admin:operations_baocaosuco_changelist"), "icon": "fas fa-triangle-exclamation"},
        {"label": "Bảng lương", "url": _safe_admin_url("admin:accounting_bangluongthang_changelist"), "icon": "fas fa-money-bill-wave"},
        {"label": "Sổ quỹ", "url": _safe_admin_url("admin:accounting_soquy_changelist"), "icon": "fas fa-wallet"},
        {"label": "Kho", "url": _safe_admin_url("admin:inventory_vattu_changelist"), "icon": "fas fa-boxes-stacked"},
    ]

    if not is_technical_admin:
        return {
            "db_status": "hidden",
            "worker_total": 0,
            "worker_active": 0,
            "worker_stale": 0,
            "periodic_total": 0,
            "periodic_enabled": 0,
            "task_result_total": 0,
            "recent_errors": 0,
            "audit_log_total": 0,
            "staff_count": 0,
            "superuser_count": 0,
            "active_sessions": 0,
            "recent_audit_logs": [],
            "recent_task_results": [],
            "recent_workers": [],
            "task_alerts": 0,
            "debug_enabled": False,
            "wildcard_hosts": False,
            "system_ok": True,
            "status_label": "",
            "status_tone": "good",
            "last_updated_label": "",
            "quick_links": [],
            "critical_links": critical_links,
            "workspace_links": [],
            "attention_items": [],
        }

    recent_audit_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:6]
    worker_qs = WorkerHeartbeat.objects.order_by("hostname")
    recent_task_results = TaskResult.objects.order_by("-date_done")[:6]
    enabled_periodic = PeriodicTask.objects.filter(enabled=True)
    task_alerts = TaskResult.objects.exclude(status="SUCCESS")
    task_alert_count = _bounded_count(task_alerts)
    recent_error_count = _bounded_count(AuditLog.objects.exclude(status="SUCCESS"))
    worker_total = _bounded_count(worker_qs)
    worker_active = _bounded_count(worker_qs.filter(is_active=True, last_ping__gte=heartbeat_threshold))
    worker_stale = _bounded_count(worker_qs.filter(is_active=True, last_ping__lt=heartbeat_threshold))
    periodic_total = _bounded_count(PeriodicTask.objects.all())
    periodic_enabled = _bounded_count(enabled_periodic)
    task_result_total = _bounded_count(TaskResult.objects.all())
    staff_count = _bounded_count(user_model.objects.filter(is_staff=True))
    superuser_count = _bounded_count(user_model.objects.filter(is_superuser=True))
    active_sessions = 0
    try:
        from django.contrib.sessions.models import Session
        active_sessions = _bounded_count(Session.objects.filter(expire_date__gte=now))
    except Exception:
        active_sessions = 0

    try:
        connections["default"].ensure_connection()
        db_status = "online"
    except Exception:
        db_status = "offline"

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
    if periodic_total and periodic_enabled == 0:
        attention_items.append({"tone": "warning", "title": "Không có lịch tác vụ bật", "note": "Celery Beat có task nhưng chưa tác vụ nào được bật.", "url": _safe_admin_url("admin:django_celery_beat_periodictask_changelist"), "cta": "Mở lịch"})
    if not attention_items:
        attention_items.append({"tone": "success", "title": "Không có cảnh báo trọng yếu", "note": "Runtime hiện không ghi nhận điểm nghẽn kỹ thuật nổi bật.", "url": _safe_admin_url("admin:main_auditlog_changelist"), "cta": "Xem audit"})

    quick_links = [
        {"label": "Người dùng", "url": _safe_admin_url("admin:auth_user_changelist"), "icon": "fas fa-users-cog", "badge": staff_count},
        {"label": "Nhật ký", "url": _safe_admin_url("admin:main_auditlog_changelist"), "icon": "fas fa-clipboard-list", "badge": recent_error_count},
        {"label": "Worker", "url": _safe_admin_url("admin:main_workerheartbeat_changelist"), "icon": "fas fa-heartbeat", "badge": worker_active},
        {"label": "Lịch tác vụ", "url": _safe_admin_url("admin:django_celery_beat_periodictask_changelist"), "icon": "fas fa-calendar-alt", "badge": periodic_enabled},
        {"label": "Kết quả tác vụ", "url": _safe_admin_url("admin:django_celery_results_taskresult_changelist"), "icon": "fas fa-list-check", "badge": task_alert_count},
    ]

    workspace_links = [
        {"label": "Bảng điều hành vận hành", "url": _workspace_url("dashboard:main"), "icon": "fas fa-gauge-high"},
        {"label": "Báo cáo", "url": _workspace_url("reports:dashboard"), "icon": "fas fa-chart-line"},
        {"label": "Workflow", "url": _workspace_url("workflow:dashboard"), "icon": "fas fa-diagram-project"},
    ]

    system_ok = db_status == "online" and worker_stale == 0 and recent_error_count == 0 and task_alert_count == 0

    return {
        "db_status": db_status,
        "worker_total": worker_total,
        "worker_active": worker_active,
        "worker_stale": worker_stale,
        "periodic_total": periodic_total,
        "periodic_enabled": periodic_enabled,
        "task_result_total": task_result_total,
        "recent_errors": recent_error_count,
        "audit_log_total": _bounded_count(AuditLog.objects.all()),
        "staff_count": staff_count,
        "superuser_count": superuser_count,
        "active_sessions": active_sessions,
        "recent_audit_logs": recent_audit_logs,
        "recent_task_results": recent_task_results,
        "recent_workers": worker_qs[:6],
        "task_alerts": task_alert_count,
        "debug_enabled": debug_enabled,
        "wildcard_hosts": wildcard_hosts,
        "system_ok": system_ok,
        "status_label": "Ổn định" if system_ok else "Cần xử lý",
        "status_tone": "good" if system_ok else "warn",
        "last_updated_label": "Runtime hiện tại",
        "quick_links": quick_links,
        "critical_links": critical_links,
        "workspace_links": workspace_links,
        "attention_items": attention_items[:6],
    }


@register.simple_tag(name="admin_console_metrics")
def admin_console_metrics_cached(user=None):
    """Short-TTL admin shell summary used by the admin homepage."""
    return build_admin_dashboard_summary(user)


@register.simple_tag
def admin_operations_ux(user):
    """Return role-aware operations UX context for admin templates."""
    return AdminOperationsUXProvider.build(user)


@register.simple_tag
def admin_result_range(cl):
    """Return a compact "start–end / total" label for Django changelists."""
    try:
        total = int(getattr(cl, "result_count", 0) or 0)
        if total <= 0:
            return "0 / tổng số 0"
        page_num = int(getattr(cl, "page_num", 0) or 0)
        per_page = int(getattr(cl, "list_per_page", 0) or 0)
        visible = len(getattr(cl, "result_list", []) or [])
        start = page_num * per_page + 1 if per_page else 1
        end = min(start + visible - 1, total) if visible else start
        return f"{start}–{end} / tổng số {total}"
    except Exception:
        return ""


@register.simple_tag
def admin_sidebar_runtime(user=None):
    if not getattr(user, "is_superuser", False):
        return {"periodic_enabled": 0, "task_alerts": 0}
    return {
        "periodic_enabled": _bounded_count(PeriodicTask.objects.filter(enabled=True)),
        "task_alerts": _bounded_count(TaskResult.objects.exclude(status="SUCCESS")),
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
        grouped.append({"title": "Khu vực hệ thống khác", "apps": leftovers})

    return grouped


@register.simple_tag
def model_badges(model):
    object_name = model.get("object_name")
    badge_keys = CRITICAL_MODEL_BADGES.get(object_name, [])
    return [BADGE_LABELS[key] for key in badge_keys]


def _safe_reverse_url(name, args=None, kwargs=None, fallback="#"):
    try:
        return reverse(name, args=args or None, kwargs=kwargs or None)
    except NoReverseMatch:
        return fallback


def _staff_profile_for_user(user):
    try:
        return getattr(user, "nhan_vien", None)
    except Exception:
        return None


def _clean_label(value):
    return str(value or "").strip()


def _display_name_for_user(user, staff_profile=None):
    full_name = ""
    try:
        full_name = _clean_label(user.get_full_name())
    except Exception:
        full_name = ""
    if full_name:
        return full_name

    staff_name = _clean_label(getattr(staff_profile, "ho_ten", ""))
    if staff_name:
        return staff_name

    username = _clean_label(getattr(user, "username", ""))
    if username:
        return username
    return _clean_label(user) or "Người dùng"


def _initials_for_name(display_name):
    tokens = [token for token in _clean_label(display_name).replace(".", " ").split() if token]
    if not tokens:
        return "U"
    if len(tokens) == 1:
        return tokens[0][:2].upper()
    return f"{tokens[0][0]}{tokens[-1][0]}".upper()


def _role_label_for_user(user, staff_profile=None, role_keys=None):
    role_keys = role_keys or set()
    if getattr(user, "is_superuser", False):
        return "Quản trị hệ thống"

    title = _clean_label(getattr(getattr(staff_profile, "chuc_danh", None), "ten_chuc_danh", ""))
    if title:
        return title

    department = _clean_label(getattr(getattr(staff_profile, "phong_ban", None), "ten_phong_ban", ""))
    if department:
        return department

    try:
        group_name = _clean_label(user.groups.values_list("name", flat=True).first())
        if group_name:
            return group_name
    except Exception:
        pass

    if role_keys & AdminOperationsUXProvider.HR_KEYS:
        return "Nhân sự"
    if role_keys & AdminOperationsUXProvider.OPERATIONS_KEYS:
        return "Điều hành"
    if role_keys & AdminOperationsUXProvider.ACCOUNTING_KEYS:
        return "Đối soát"
    if role_keys & AdminOperationsUXProvider.INVENTORY_KEYS:
        return "Kho"
    if role_keys & AdminOperationsUXProvider.CLIENT_KEYS:
        return "Kinh doanh"
    if getattr(user, "is_staff", False):
        return "Nhân sự vận hành"
    return "Người dùng"


def _scope_label_for_user(user, role_keys=None):
    role_keys = role_keys or set()
    if getattr(user, "is_superuser", False) or role_keys & AdminOperationsUXProvider.EXECUTIVE_KEYS:
        return "Toàn hệ thống"
    if "quan_ly_vung" in role_keys or "alias:quan_ly_vung" in role_keys:
        return "Vùng"
    if "doi_truong" in role_keys or "alias:doi_truong" in role_keys:
        return "Mục tiêu"
    if role_keys & (AdminOperationsUXProvider.HR_KEYS | AdminOperationsUXProvider.ACCOUNTING_KEYS | AdminOperationsUXProvider.INVENTORY_KEYS):
        return "Theo phân hệ"
    return "Cá nhân"


def _has_any_perm(user, perm_codes):
    for perm_code in perm_codes:
        try:
            if user.has_perm(perm_code):
                return True
        except Exception:
            continue
    return False


@register.simple_tag
def admin_account_context(request):
    """Build permission-aware account UI context for the Jazzmin admin shell.

    This helper only prepares display labels and reverse-safe links. It does not
    grant permissions or bypass the target admin views; every technical link is
    rendered only when the current user has the corresponding backend permission.
    """
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {
            "display_name": "Khách",
            "initials": "K",
            "role_label": "Chưa đăng nhập",
            "scope_label": "Cá nhân",
            "profile_url": _safe_reverse_url("admin:index"),
            "password_change_url": _safe_reverse_url("admin:password_change"),
            "search_url": _safe_reverse_url("admin_global_search"),
            "console_url": _safe_reverse_url("admin:index"),
            "can_console": False,
            "my_activity_url": "",
            "technical_links": [],
        }

    staff_profile = _staff_profile_for_user(user)
    try:
        role_keys = AdminOperationsUXProvider.role_keys_for_user(user)
    except Exception:
        role_keys = set()

    display_name = _display_name_for_user(user, staff_profile)
    profile_url = "#"
    if staff_profile is not None:
        profile_url = _safe_reverse_url("users:profile")
    if profile_url == "#" and (getattr(user, "is_superuser", False) or _has_any_perm(user, ["auth.view_user", "auth.change_user"])):
        profile_url = _safe_reverse_url("admin:auth_user_change", args=[getattr(user, "pk", None)])
    if profile_url == "#":
        profile_url = _safe_reverse_url("admin:index")

    password_change_url = _safe_reverse_url("admin:password_change")
    search_url = _safe_reverse_url("admin_global_search")
    console_url = _safe_reverse_url("admin:index")
    audit_url = _safe_reverse_url("admin:main_auditlog_changelist")
    worker_url = _safe_reverse_url("admin:main_workerheartbeat_changelist")
    health_url = _safe_reverse_url("main:healthcheck")

    can_view_audit = _has_any_perm(user, ["main.view_auditlog"])
    can_view_worker = _has_any_perm(user, ["main.view_workerheartbeat"])
    can_console = bool(
        getattr(user, "is_superuser", False)
        or can_view_audit
        or can_view_worker
        or _has_any_perm(
            user,
            [
                "django_celery_beat.view_periodictask",
                "django_celery_results.view_taskresult",
            ],
        )
    )

    technical_links = []
    if can_console and console_url != "#":
        technical_links.append({"label": "Console", "url": console_url, "icon": "fas fa-shield-alt"})
    if can_view_audit and audit_url != "#":
        technical_links.append({"label": "Audit Log", "url": audit_url, "icon": "fas fa-clipboard-list"})
    if can_view_worker and worker_url != "#":
        technical_links.append({"label": "Worker Heartbeat", "url": worker_url, "icon": "fas fa-heartbeat"})
    if can_console and health_url != "#":
        technical_links.append({"label": "System Health", "url": health_url, "icon": "fas fa-check-circle"})

    my_activity_url = ""
    if can_view_audit and audit_url != "#":
        username = _clean_label(getattr(user, "username", ""))
        my_activity_url = _with_query(audit_url, {"q": username}) if username else audit_url

    return {
        "display_name": display_name,
        "initials": _initials_for_name(display_name),
        "role_label": _role_label_for_user(user, staff_profile, role_keys),
        "scope_label": _scope_label_for_user(user, role_keys),
        "profile_url": profile_url,
        "password_change_url": password_change_url,
        "search_url": search_url,
        "console_url": console_url,
        "can_console": can_console,
        "my_activity_url": my_activity_url,
        "technical_links": technical_links,
    }
