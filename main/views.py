# file: main/views.py
<<<<<<< HEAD
import random
from pathlib import PurePosixPath
from urllib.parse import unquote
from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connections
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET
from django.apps import apps
from rolepermissions.checkers import has_role

from .dashboard_router import DashboardRouter
from .forms import LoginAuthenticationForm


# Canonical policy matrix for every owned ``upload_to`` media prefix.
# Values describe the object-level policy branch used by ``media_auth_view``.
MEDIA_AUTH_POLICY_MATRIX = {
    # HR / staff records
    "anh_the/": "staff_profile",
    "bang_cap/": "staff_document",
    "hop_dong_lao_dong/": "staff_document",
    "phu_luc_hop_dong_lao_dong/": "staff_document",
    "don_nghi_phep/": "staff_document",
    "quyet_dinh_nghi_viec/": "staff_document",
    "ho_so_bao_hiem/": "staff_document",
    # Operations / inspection evidence
    "check_in/": "attendance_evidence",
    "check_out/": "attendance_evidence",
    "shift_change_requests/": "operations_or_inspection_evidence",
    "de_xuat/": "operations_or_inspection_evidence",
    "su_co/audio/": "operations_or_inspection_evidence",
    "su_co/": "operations_or_inspection_evidence",
    "alive_check/": "alive_or_patrol_evidence",
    "tuan_tra/": "alive_or_patrol_evidence",
    "vipham/": "operations_or_inspection_evidence",
    "thanhtra/": "operations_or_inspection_evidence",
    # Customer / contract receivable documents
    "hop_dong/": "client_document",
    "phu_luc_hop_dong_dich_vu/": "client_document",
    "bien_ban_nghiem_thu/": "client_document",
    "hoa_don/": "client_document",
    "thanh_toan_khach_hang/": "client_document",
    # Accounting/payroll evidence
    "ketoan/chungtu/": "accounting_document",
    "tam_ung_luong/": "accounting_document",
    "khoan_khau_tru/": "accounting_document",
    # Inventory/asset recovery evidence
    "vattu/": "inventory_document",
    "phieu_thu_hoi/": "inventory_document",
    "bien_ban_mat_hong/": "inventory_document",
    # Company branding is still served via the authenticated media gate.
    "logos/": "company_branding",
    "company/logos/": "company_branding",
    # Office workflow documents
    "tasks/": "workflow_document",
    "proposals/": "workflow_document",
}


def _resolve_media_auth_policy(relative_path):
    """Return the policy key for a media path, preferring the longest prefix."""
    for prefix, policy_key in sorted(MEDIA_AUTH_POLICY_MATRIX.items(), key=lambda item: len(item[0]), reverse=True):
        if relative_path.startswith(prefix):
            return policy_key
    return None


# Override legacy famous-quote copy with SCMD Pro operating principles.
LOGIN_QUOTES = [
    {
        "category": "discipline",
        "label": "Kỷ luật",
        "title": "Nguyên tắc 01: Kỷ luật tạo ra độ tin cậy vận hành.",
        "message": "Ca trực đúng giờ, báo cáo đúng mẫu và dữ liệu đúng thời điểm là nền tảng để toàn bộ hệ thống vận hành ổn định.",
        "author": "Nguyên tắc vận hành SCMD Pro",
    },
    {
        "category": "focus",
        "label": "Tập trung",
        "title": "Nguyên tắc 02: Chỉ hiển thị điều phục vụ quyết định.",
        "message": "SCMD Pro ưu tiên tín hiệu vận hành thật, tránh gây nhiễu bằng số liệu trình diễn hoặc thông tin không phục vụ xử lý ca trực.",
        "author": "Nguyên tắc vận hành SCMD Pro",
    },
    {
        "category": "calm",
        "label": "Bình tĩnh",
        "title": "Nguyên tắc 03: Bình tĩnh để giữ chuẩn xác.",
        "message": "Khi phát sinh sự cố, hệ thống cần giúp người trực xác nhận đúng người, đúng vị trí, đúng dữ liệu trước khi hành động.",
        "author": "Nguyên tắc vận hành SCMD Pro",
    },
    {
        "category": "improvement",
        "label": "Cải tiến",
        "title": "Nguyên tắc 04: Cải tiến nhỏ, lặp đúng, tạo khác biệt lớn.",
        "message": "Mọi điều chỉnh về phân công, chấm công, sự cố, lương và kho phải làm hệ thống nhất quán hơn, không chỉ đẹp hơn.",
        "author": "Nguyên tắc vận hành SCMD Pro",
    },
]

LOGIN_FAILURE_COUNT_SESSION_KEY = "login_failure_count"
LOGIN_LOCK_UNTIL_SESSION_KEY = "login_lock_until"
LOGIN_CHALLENGE_QUESTION_SESSION_KEY = "login_challenge_question"
LOGIN_CHALLENGE_ANSWER_SESSION_KEY = "login_challenge_answer"
LOGIN_FAILURE_THRESHOLD = 5
LOGIN_LOCKOUT_MINUTES = 15
LOGIN_FAILURE_CACHE_KEY_PREFIX = "login_failures"
LOGIN_LOCK_CACHE_KEY_PREFIX = "login_lock_until"


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _normalize_login_username(username):
    return (username or "").strip().lower()


def _build_login_cache_key(prefix, request, username):
    return f"{prefix}:{_get_client_ip(request)}:{_normalize_login_username(username)}"


def _generate_login_challenge(request):
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    request.session[LOGIN_CHALLENGE_QUESTION_SESSION_KEY] = f"{left} + {right} = ?"
    request.session[LOGIN_CHALLENGE_ANSWER_SESSION_KEY] = str(left + right)
    request.session.modified = True


def _get_login_challenge_question(request):
    question = request.session.get(LOGIN_CHALLENGE_QUESTION_SESSION_KEY)
    if not question:
        _generate_login_challenge(request)
        question = request.session[LOGIN_CHALLENGE_QUESTION_SESSION_KEY]
    return question


def _clear_login_failures(request):
    request.session.pop(LOGIN_FAILURE_COUNT_SESSION_KEY, None)
    request.session.pop(LOGIN_LOCK_UNTIL_SESSION_KEY, None)
    request.session.modified = True


def _clear_cached_login_failures(request, username):
    cache.delete_many(
        [
            _build_login_cache_key(LOGIN_FAILURE_CACHE_KEY_PREFIX, request, username),
            _build_login_cache_key(LOGIN_LOCK_CACHE_KEY_PREFIX, request, username),
        ]
    )


def _get_cached_login_lock_until(request, username):
    lock_until = cache.get(_build_login_cache_key(LOGIN_LOCK_CACHE_KEY_PREFIX, request, username))
    if not lock_until:
        return None

    if timezone.is_naive(lock_until):
        lock_until = timezone.make_aware(lock_until, timezone.get_current_timezone())

    if lock_until <= timezone.now():
        _clear_cached_login_failures(request, username)
        return None

    return lock_until


def _get_login_lock_until(request):
    lock_until_raw = request.session.get(LOGIN_LOCK_UNTIL_SESSION_KEY)
    if not lock_until_raw:
        return None

    try:
        lock_until = timezone.datetime.fromisoformat(lock_until_raw)
    except ValueError:
        request.session.pop(LOGIN_LOCK_UNTIL_SESSION_KEY, None)
        request.session.modified = True
        return None

    if timezone.is_naive(lock_until):
        lock_until = timezone.make_aware(lock_until, timezone.get_current_timezone())

    if lock_until <= timezone.now():
        _clear_login_failures(request)
        return None

    return lock_until


def _get_effective_login_lock_until(request, username):
    session_lock_until = _get_login_lock_until(request)
    cached_lock_until = _get_cached_login_lock_until(request, username)
    if session_lock_until and cached_lock_until:
        return max(session_lock_until, cached_lock_until)
    return session_lock_until or cached_lock_until


def _register_login_failure(request, username):
    failure_count = int(request.session.get(LOGIN_FAILURE_COUNT_SESSION_KEY, 0)) + 1
    request.session[LOGIN_FAILURE_COUNT_SESSION_KEY] = failure_count
    cache_key = _build_login_cache_key(LOGIN_FAILURE_CACHE_KEY_PREFIX, request, username)
    cached_failure_count = int(cache.get(cache_key, 0)) + 1
    cache.set(cache_key, cached_failure_count, timeout=LOGIN_LOCKOUT_MINUTES * 60)

    lock_until = None
    if max(failure_count, cached_failure_count) >= LOGIN_FAILURE_THRESHOLD:
        lock_until = timezone.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        request.session[LOGIN_LOCK_UNTIL_SESSION_KEY] = lock_until.isoformat()
        request.session[LOGIN_FAILURE_COUNT_SESSION_KEY] = 0
        cache.set(
            _build_login_cache_key(LOGIN_LOCK_CACHE_KEY_PREFIX, request, username),
            lock_until,
            timeout=LOGIN_LOCKOUT_MINUTES * 60,
        )
        cache.delete(cache_key)

    request.session.modified = True
    return lock_until


def _get_login_lock_message(lock_until):
    remaining_seconds = max(int((lock_until - timezone.now()).total_seconds()), 0)
    remaining_minutes = max((remaining_seconds + 59) // 60, 1)
    return (
        "Bạn đã nhập sai quá nhiều lần. "
        f"Vui lòng chờ {remaining_minutes} phút trước khi thử lại."
    )


def _build_login_context(request, form, lock_message=None):
    return {
        "form": form,
        "login_quotes": LOGIN_QUOTES,
        "default_login_quote": LOGIN_QUOTES[0],
        "login_verification_question": _get_login_challenge_question(request),
        "login_is_locked": bool(_get_login_lock_until(request)),
        "login_lock_message": lock_message,
    }


def _resolve_safe_next_url(request):
    next_url = request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return redirect("main:central_hub").url


def _media_user_has_client_document_access(user, relative_path):
    from clients.access_policies import SiteVisibilityPolicy

    if has_role(user, ["ban_giam_doc", "nhan_vien_kinh_doanh", "ke_toan"]):
        privileged_scope = True
    else:
        privileged_scope = False

    visible_sites = SiteVisibilityPolicy.visible_sites(user)
    if relative_path.startswith("hop_dong/"):
        model = apps.get_model("clients", "HopDong")
        qs = model.objects.filter(file_hop_dong=relative_path)
        if privileged_scope:
            return qs.exists()
        return qs.filter(cac_muc_tieu__in=visible_sites).exists()

    document_map = {
        "phu_luc_hop_dong_dich_vu/": ("clients", "PhuLucHopDongDichVu", "file_phu_luc"),
        "bien_ban_nghiem_thu/": ("clients", "BienBanNghiemThu", "file_bien_ban"),
        "hoa_don/": ("clients", "HoaDon", "file_hoa_don"),
        "thanh_toan_khach_hang/": ("clients", "ThanhToanKhachHang", "file_chung_tu"),
    }
    for prefix, (app_label, model_name, file_field) in document_map.items():
        if relative_path.startswith(prefix):
            model = apps.get_model(app_label, model_name)
            qs = model.objects.filter(**{file_field: relative_path})
            if privileged_scope:
                return qs.exists()
            return qs.filter(hop_dong__cac_muc_tieu__in=visible_sites).exists()
    return False


def _media_user_has_staff_document_access(user, relative_path):
    from users.access_policies import StaffVisibilityPolicy

    visible_staff = StaffVisibilityPolicy.visible_staff(user)
    document_map = {
        "bang_cap/": ("users", "BangCap", "file_dinh_kem", "nhan_vien__in"),
        "hop_dong_lao_dong/": ("users", "HopDongLaoDong", "file_hop_dong", "nhan_vien__in"),
        "phu_luc_hop_dong_lao_dong/": ("users", "PhuLucHopDongLaoDong", "file_phu_luc", "hop_dong__nhan_vien__in"),
        "don_nghi_phep/": ("users", "DonNghiPhep", "file_minh_chung", "nhan_vien__in"),
        "quyet_dinh_nghi_viec/": ("users", "QuyetDinhNghiViec", "file_quyet_dinh", "nhan_vien__in"),
        "ho_so_bao_hiem/": ("users", "HoSoBaoHiem", "file_ho_so", "nhan_vien__in"),
    }
    for prefix, (app_label, model_name, file_field, scope_field) in document_map.items():
        if relative_path.startswith(prefix):
            model = apps.get_model(app_label, model_name)
            return model.objects.filter(**{file_field: relative_path, scope_field: visible_staff}).exists()
    return False


def _media_user_has_accounting_document_access(user, relative_path):
    if has_role(user, ["ban_giam_doc", "ke_toan"]):
        privileged_scope = True
    else:
        privileged_scope = False

    if relative_path.startswith("ketoan/chungtu/"):
        from accounting.models_soquy import SoQuy
        if privileged_scope:
            return SoQuy.objects.filter(chung_tu_goc=relative_path).exists()
        return False

    from users.access_policies import StaffVisibilityPolicy

    visible_staff = StaffVisibilityPolicy.visible_staff(user)
    document_map = {
        "tam_ung_luong/": ("accounting", "TamUngLuong", "file_minh_chung"),
        "khoan_khau_tru/": ("accounting", "KhoanKhauTruNhanVien", "file_minh_chung"),
    }
    for prefix, (app_label, model_name, file_field) in document_map.items():
        if relative_path.startswith(prefix):
            model = apps.get_model(app_label, model_name)
            qs = model.objects.filter(**{file_field: relative_path})
            if privileged_scope:
                return qs.exists()
            return qs.filter(nhan_vien__in=visible_staff).exists()
    return False


def _media_user_has_inventory_document_access(user, relative_path):
    if relative_path.startswith("vattu/"):
        return bool(has_role(user, ["thu_kho", "ban_giam_doc", "nghiep_vu", "ke_toan", "nhan_su"]))

    document_map = {
        "phieu_thu_hoi/": ("inventory", "PhieuThuHoi", "file_bien_ban"),
        "bien_ban_mat_hong/": ("inventory", "BienBanMatHongVatTu", "file_minh_chung"),
    }
    for prefix, (app_label, model_name, file_field) in document_map.items():
        if relative_path.startswith(prefix):
            model = apps.get_model(app_label, model_name)
            document = model.objects.filter(**{file_field: relative_path}).select_related("nhan_vien").first()
            if document is None:
                return False
            if getattr(getattr(document, "nhan_vien", None), "user_id", None) == getattr(user, "id", None):
                return True
            return bool(
                getattr(user, "is_superuser", False)
                or has_role(user, ["thu_kho", "ban_giam_doc", "nhan_su", "ke_toan"])
            )
    return False


def _media_user_has_workflow_document_access(user, relative_path):
    if has_role(user, ["ban_giam_doc", "nghiep_vu", "nhan_su"]):
        privileged_scope = True
    else:
        privileged_scope = False

    if relative_path.startswith("tasks/"):
        model = apps.get_model("workflow", "Task")
        qs = model.objects.filter(file_dinh_kem=relative_path)
        if privileged_scope:
            return qs.exists()
        return qs.filter(
            Q(nguoi_giao__user=user) | Q(nguoi_nhan__user=user) | Q(nguoi_phoi_hop__user=user)
        ).exists()

    if relative_path.startswith("proposals/"):
        model = apps.get_model("workflow", "Proposal")
        qs = model.objects.filter(file_dinh_kem=relative_path)
        if privileged_scope:
            return qs.exists()
        return qs.filter(Q(nguoi_de_xuat__user=user) | Q(nguoi_duyet_hien_tai__user=user)).exists()

    return False


def _media_user_has_company_branding_access(user, relative_path):
    # Company logo files are not public files anymore because /media/ is private,
    # but any authenticated user may read them for shell/report rendering.
    return relative_path.startswith(("logos/", "company/logos/")) and user.is_authenticated


def _media_user_has_ops_or_inspection_access(user, relative_path):
    from clients.access_policies import SiteVisibilityPolicy
    from operations.access_policies import IncidentVisibilityPolicy, ProposalVisibilityPolicy, ShiftVisibilityPolicy

    visible_sites = SiteVisibilityPolicy.visible_sites(user)
    if relative_path.startswith("shift_change_requests/"):
        model = apps.get_model("operations", "ShiftChangeRequest")
        visible_shift_ids = ShiftVisibilityPolicy.visible_shifts(user).values_list("pk", flat=True)
        return model.objects.filter(file_minh_chung=relative_path).filter(
            Q(nguoi_yeu_cau__user=user)
            | Q(phan_cong_goc_id__in=visible_shift_ids)
            | Q(vi_tri_mong_muon__muc_tieu__in=visible_sites)
        ).exists()
    if relative_path.startswith("de_xuat/"):
        return ProposalVisibilityPolicy.visible_proposals(user).filter(hinh_anh=relative_path).exists()
    if relative_path.startswith("vipham/"):
        model = apps.get_model("inspection", "BienBanViPham")
        return model.objects.filter(bang_chung_anh=relative_path).filter(
            Q(doi_tuong_vi_pham__user=user)
            | Q(nguoi_lap__user=user)
            | Q(muc_tieu__in=visible_sites)
        ).exists()
    if relative_path.startswith("thanhtra/"):
        model = apps.get_model("inspection", "DotThanhTra")
        return model.objects.filter(hinh_anh_tong_quan=relative_path).filter(
            Q(can_bo__user=user) | Q(muc_tieu__in=visible_sites)
        ).exists()
    if relative_path.startswith("su_co/"):
        return IncidentVisibilityPolicy.visible_incidents(user).filter(
            Q(hinh_anh_1=relative_path) | Q(hinh_anh_2=relative_path) | Q(file_ghi_am=relative_path)
        ).exists()
    return False
=======
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .dashboard_router import DashboardRouter
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


def homepage(request):
    """
    Trang chủ:
    - Nếu đã đăng nhập -> Chuyển vào Hub điều phối.
    - Nếu chưa đăng nhập -> Chuyển sang trang Login.
    """
    if request.user.is_authenticated:
        return redirect("main:central_hub")
    return redirect("main:login")


@login_required
def central_hub(request):
    """
    Trung tâm điều phối:
    - Dùng DashboardRouter làm SSOT cho điều hướng dashboard.
    - Không còn dùng `is_staff` như tín hiệu thay thế cho vai trò nghiệp vụ.
    """
    decision = DashboardRouter.resolve_decision(request.user)

    if not decision.matched:
        messages.warning(
            request,
            f"Xin chào {request.user.username}, tài khoản của bạn chưa được phân nhóm quyền."
        )

    return redirect(decision.route_name)


<<<<<<< HEAD
@login_required
def access_pending(request):
    """Safe landing page for authenticated users without a business role."""
    response = render(request, "main/access_pending.html", {
        "title": "Chưa được phân quyền",
    })
    response["Cache-Control"] = "no-store"
    return response


def handler403(request, exception=None):
    """Friendly access-denied surface for business users."""
    message = str(exception).strip() if exception else ""
    legacy_generic_message = "Bạn không có quyền truy cập khu vực này. Vui lòng liên hệ với Admin."
    generic_message = (
        "Tài khoản của bạn chưa được cấp quyền vào khu vực này. "
        "Vui lòng quay lại khu vực làm việc phù hợp hoặc liên hệ quản trị viên nếu cần điều chỉnh quyền."
    )
    detail_message = ""

    if (
        not message
        or message.lower() == "forbidden"
        or message == "403 Forbidden"
        or message in {generic_message, legacy_generic_message}
    ):
        message = generic_message
    elif message != generic_message:
        detail_message = message
        message = generic_message

    return_route = "main:central_hub"
    if request.user.is_authenticated:
        decision = DashboardRouter.resolve_decision(request.user)
        return_route = decision.route_name

    show_technical_detail = bool(
        detail_message and (settings.DEBUG or getattr(request.user, "is_superuser", False))
    )

    response = render(
        request,
        "main/403.html",
        {
            "title": "Không có quyền truy cập",
            "message": message,
            "detail_message": detail_message if show_technical_detail else "",
            "show_technical_detail": show_technical_detail,
            "return_route": return_route,
        },
        status=403,
    )
    response["Cache-Control"] = "no-store"
    return response


def admin_root_gateway(request):
    """
    Keep `/admin/` aligned with the technical-console contract.

    Business users with a resolved workspace must be sent to their canonical
    workspace instead of remaining on the admin root.
    """
    if request.user.is_authenticated and not DashboardRouter.user_can_access_admin_console(request.user):
        return redirect(DashboardRouter.resolve(request.user))
    if request.user.is_authenticated:
        return admin.site.admin_view(admin.site.index)(request)
    return admin.site.login(request)


@require_GET
def media_auth_view(request):
    """
    Phase 0 media access gate used by Nginx ``auth_request``.

    All ``/media/`` objects are treated as private by default. The view returns
    only a status code to Nginx: 200 when the authenticated user may read the
    requested object, 401 for anonymous users, and 403 for authenticated users
    outside the object scope.
    """
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    requested_uri = (
        request.GET.get("uri")
        or request.META.get("HTTP_X_ORIGINAL_URI")
        or ""
    )
    requested_path = unquote(requested_uri.split("?", 1)[0])
    media_url = settings.MEDIA_URL

    if not requested_path or not requested_path.startswith(media_url):
        return HttpResponse(status=403)

    relative_path = requested_path[len(media_url):].lstrip("/")
    if not relative_path:
        return HttpResponse(status=403)

    # Block path traversal before consulting object-level policies.
    if ".." in PurePosixPath(relative_path).parts:
        return HttpResponse(status=403)

    policy_key = _resolve_media_auth_policy(relative_path)
    if not policy_key:
        return HttpResponse(status=403)

    if request.user.is_superuser:
        return HttpResponse(status=200)

    if policy_key == "staff_profile":
        from users.access_policies import StaffVisibilityPolicy
        staff_qs = StaffVisibilityPolicy.visible_staff(request.user)
        if staff_qs.filter(anh_the=relative_path).exists():
            return HttpResponse(status=200)

    elif policy_key == "attendance_evidence":
        from operations.access_policies import AttendanceVisibilityPolicy
        attendance_qs = AttendanceVisibilityPolicy.visible_attendance(request.user)
        if attendance_qs.filter(Q(anh_check_in=relative_path) | Q(anh_check_out=relative_path)).exists():
            return HttpResponse(status=200)

    elif policy_key == "client_document" and _media_user_has_client_document_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "staff_document" and _media_user_has_staff_document_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "accounting_document" and _media_user_has_accounting_document_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "inventory_document" and _media_user_has_inventory_document_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "operations_or_inspection_evidence" and _media_user_has_ops_or_inspection_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "workflow_document" and _media_user_has_workflow_document_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "company_branding" and _media_user_has_company_branding_access(request.user, relative_path):
        return HttpResponse(status=200)

    elif policy_key == "alive_or_patrol_evidence":
        if has_role(request.user, ["ban_giam_doc", "thanh_tra", "nghiep_vu"]):
            return HttpResponse(status=200)

        if relative_path.startswith("alive_check/"):
            KiemTraQuanSo = apps.get_model('operations', 'KiemTraQuanSo')
            if KiemTraQuanSo.objects.filter(ca_truc__nhan_vien__user=request.user, anh_xac_thuc=relative_path).exists():
                return HttpResponse(status=200)
        else:
            GhiNhanTuanTra = apps.get_model('inspection', 'GhiNhanTuanTra')
            if GhiNhanTuanTra.objects.filter(luot_tuan_tra__nhan_vien__user=request.user, hinh_anh_xac_thuc=relative_path).exists():
                return HttpResponse(status=200)

    return HttpResponse(status=403)


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
def login_view(request):
    """
    Xử lý đăng nhập.
    """
    if request.user.is_authenticated:
        return redirect("main:central_hub")

<<<<<<< HEAD
    submitted_username = _normalize_login_username(request.POST.get("username", "")) if request.method == "POST" else ""
    lock_until = _get_effective_login_lock_until(request, submitted_username)
    lock_message = _get_login_lock_message(lock_until) if lock_until else None

    if request.method == "POST":
        form = LoginAuthenticationForm(request, data=request.POST)
        submitted_username = _normalize_login_username(form.data.get("username", ""))
        lock_until = _get_effective_login_lock_until(request, submitted_username)
        lock_message = _get_login_lock_message(lock_until) if lock_until else None

        if lock_until:
            messages.error(request, lock_message)
        else:
            verification_answer = request.POST.get("login_verification_answer", "").strip()
            expected_answer = request.session.get(LOGIN_CHALLENGE_ANSWER_SESSION_KEY, "")

            if verification_answer != expected_answer:
                lock_until = _register_login_failure(request, submitted_username)
                _generate_login_challenge(request)
                
                error_msg = _get_login_lock_message(lock_until) if lock_until else "Câu trả lời xác minh không chính xác."
                messages.error(request, error_msg)

            elif form.is_valid():
                user = form.get_user()
                login(request, user)
                _clear_login_failures(request)
                _clear_cached_login_failures(request, submitted_username)
                _generate_login_challenge(request)

                redirect_url = _resolve_safe_next_url(request)

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    response = JsonResponse({"success": True, "redirect_url": redirect_url})
                    response["Cache-Control"] = "no-store"
                    return response

                return redirect(redirect_url)
            else:
                lock_until = _register_login_failure(request, submitted_username)
                _generate_login_challenge(request)

                if lock_until:
                    messages.error(request, _get_login_lock_message(lock_until))
                
                # Không thêm messages.error thủ công ở đây để tránh lặp với lỗi từ form
    else:
        form = LoginAuthenticationForm()

    response = render(
        request,
        "main/login.html",
        _build_login_context(request, form, lock_message=lock_message),
    )
    response["Cache-Control"] = "no-store"
    return response
=======
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "main:central_hub")
                return redirect(next_url)

            messages.error(request, "Tài khoản hoặc mật khẩu không chính xác.")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin đăng nhập.")
    else:
        form = AuthenticationForm()

    return render(request, "main/login.html", {"form": form})
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


def logout_view(request):
    """
    Xử lý đăng xuất.
    """
    logout(request)
    return redirect("main:login")
<<<<<<< HEAD


@require_GET
def healthcheck_view(request):
    """
    Healthcheck tối thiểu cho production probe.

    Mục tiêu:
    - Xác nhận web process còn nhận request.
    - Xác nhận database mặc định còn kết nối được.

    Endpoint này cố ý mỏng, không đụng business flow attendance/payroll.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse(
            {
                "status": "unhealthy",
                "service": "scmd-web",
                "checks": {
                    "database": "down",
                },
                "error": str(exc),
            },
            status=503,
        )

    response = JsonResponse(
        {
            "status": "ok",
            "service": "scmd-web",
            "checks": {
                "database": "ok",
            },
        }
    )
    response["Cache-Control"] = "no-store"
    return response
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
