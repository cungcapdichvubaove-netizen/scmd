# -*- coding: utf-8 -*-
"""
Application-layer report queries for the reports module.

<<<<<<< HEAD
The reports workspace must scale to large employee lists. Use cases therefore
support explicit filter objects and return paginated/candidate lists instead of
rendering every employee in a select box.
"""

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from operations.access_policies import AttendanceVisibilityPolicy, IncidentVisibilityPolicy
from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc
from users.access_policies import StaffVisibilityPolicy
from users.models import ACTIVE_EMPLOYEE_STATUSES, ChucDanh, NhanVien, PhongBan


REPORT_PAGE_SIZE = 50
CANDIDATE_LIMIT = 80


def _get_employee_scope_queryset(tenant_id=None, user=None):
    """Return employees in the caller's allowed scope.

    Reports must combine report RBAC with object-level staff visibility. When a
    user is supplied, StaffVisibilityPolicy is the SSOT. The tenant fallback is
    kept only for internal/system callers and remains tenant-scoped.
    """
    if user is not None:
        qs = StaffVisibilityPolicy.visible_staff(user)
    elif tenant_id:
        qs = NhanVien.objects.for_tenant(tenant_id)
    else:
        qs = NhanVien.objects.none()
    return qs.filter(trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES)


def _base_target_scope_queryset(tenant_id=None):
    """Return organization-scoped target queryset without object-level narrowing."""
    qs = MucTieu.objects.select_related("hop_dong").order_by("ten_muc_tieu")
    if not tenant_id:
        return qs.none()

    model_fields = {field.name for field in MucTieu._meta.get_fields()}
    if "tenant_id" in model_fields:
        return qs.filter(tenant_id=tenant_id)
    return qs.filter(hop_dong__tenant_id=tenant_id)


def _has_global_report_target_visibility(user):
    """Return True for roles that intentionally retain organization-wide reports.

    Report target dropdowns must mirror the data policies: executive/HR/payroll
    report roles can inspect the whole organization even when they do not have a
    ``NhanVien`` profile; scoped roles such as ``quan_ly_vung`` and
    ``doi_truong`` remain constrained by ``SiteVisibilityPolicy.visible_sites``.
    """
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or any(has_role(user, role) for role in ("ban_giam_doc", "nhan_su", "ke_toan"))
        )
    )


def _get_target_scope_queryset(tenant_id=None, user=None):
    """Return sites/targets in the caller's allowed report scope."""
    if user is not None:
        if _has_global_report_target_visibility(user):
            return _base_target_scope_queryset(tenant_id)
        return SiteVisibilityPolicy.visible_sites(user).order_by("ten_muc_tieu")

    return _base_target_scope_queryset(tenant_id)


def _get_attendance_scope_queryset(tenant_id=None, user=None):
    """Return attendance rows in the caller's allowed scope."""
    if user is not None:
        return AttendanceVisibilityPolicy.visible_attendance(user)
    return ChamCong.objects.for_tenant(tenant_id)


def _get_incident_scope_queryset(tenant_id=None, user=None):
    """Return incidents in the caller's allowed scope."""
    if user is not None:
        return IncidentVisibilityPolicy.visible_incidents(user)
    return BaoCaoSuCo.objects.for_tenant(tenant_id)


def _get_month_date_range(thang: int, nam: int):
    _, num_days = calendar.monthrange(nam, thang)
    period_start = date(nam, thang, 1)
    period_end = date(nam, thang, num_days)
    return period_start, period_end


def _get_month_datetime_range(thang: int, nam: int):
    period_start, period_end = _get_month_date_range(thang, nam)
    range_start = timezone.make_aware(datetime.combine(period_start, time.min))
    range_end = timezone.make_aware(
        datetime.combine(period_end + timedelta(days=1), time.min)
    )
    return range_start, range_end


def _as_int(value):
    try:
        return int(value) if value not in {None, "", "all"} else None
    except (TypeError, ValueError):
        return None


def _apply_employee_filters(qs, filters):
    q = (filters.get("q") or "").strip()
    phong_ban_id = _as_int(filters.get("phong_ban_id"))
    chuc_danh_id = _as_int(filters.get("chuc_danh_id"))
    trang_thai = (filters.get("trang_thai") or "").strip()

    if q:
        qs = qs.filter(
            Q(ho_ten__icontains=q)
            | Q(ma_nhan_vien__icontains=q)
            | Q(sdt_chinh__icontains=q)
        )
    if phong_ban_id:
        qs = qs.filter(phong_ban_id=phong_ban_id)
    if chuc_danh_id:
        qs = qs.filter(chuc_danh_id=chuc_danh_id)
    if trang_thai:
        qs = qs.filter(trang_thai_lam_viec=trang_thai)
    return qs


def _apply_target_filter_to_employees(qs, filters, period_start, period_end, tenant_id, user=None):
    muc_tieu_id = _as_int(filters.get("muc_tieu_id"))
    if not muc_tieu_id:
        return qs

    target_qs = _get_target_scope_queryset(tenant_id, user=user)
    if not target_qs.filter(pk=muc_tieu_id).exists():
        return qs.none()

    assigned_employee_ids = (
        PhanCongCaTruc.objects.for_tenant(tenant_id)
        .filter(
            ngay_truc__range=(period_start, period_end),
            vi_tri_chot__muc_tieu_id=muc_tieu_id,
        )
        .values_list("nhan_vien_id", flat=True)
        .distinct()
    )
    return qs.filter(id__in=assigned_employee_ids)


def _employee_filter_options(tenant_id=None, user=None):
    visible_staff = _get_employee_scope_queryset(tenant_id, user=user)
    return {
        "phong_ban_list": PhongBan.objects.filter(cac_nhan_vien__in=visible_staff).distinct().order_by("ten_phong_ban"),
        "chuc_danh_list": ChucDanh.objects.filter(cac_nhan_vien__in=visible_staff).distinct().order_by("ten_chuc_danh"),
        "trang_thai_choices": NhanVien.TrangThaiLamViec.choices,
    }


def _paginate(qs_or_list, page_number, page_size):
    paginator = Paginator(qs_or_list, page_size)
    return paginator.get_page(page_number or 1)
=======
SCMD currently runs as single-organization hardened. Models without a direct
tenant field remain explicit single-organization exceptions until schema scope
is modeled there.
"""

import calendar

from clients.models import MucTieu
from operations.models import BaoCaoSuCo, ChamCong
from users.models import NhanVien
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


class GetMonthlyAttendanceMatrixUseCase:
    @staticmethod
<<<<<<< HEAD
    def execute(thang: int, nam: int, tenant_id, filters=None, user=None):
        filters = filters or {}
        _, num_days = calendar.monthrange(nam, thang)
        days_in_month = list(range(1, num_days + 1))
        period_start, period_end = _get_month_date_range(thang, nam)

        employees_qs = _get_employee_scope_queryset(tenant_id, user=user).order_by("ma_nhan_vien", "ho_ten")
        employees_qs = _apply_employee_filters(employees_qs, filters)
        employees_qs = _apply_target_filter_to_employees(
            employees_qs, filters, period_start, period_end, tenant_id, user=user
        )

        total_filtered = employees_qs.count()
        requested_page_size = _as_int(filters.get("page_size")) or REPORT_PAGE_SIZE
        page_size = min(requested_page_size, 200)
        matrix_performance_notice = None
        if page_size >= 150:
            matrix_performance_notice = (
                "Hiển thị nhiều dòng có thể làm chậm trình duyệt. "
                "Dữ liệu vẫn được phân trang trên máy chủ; hãy giảm số dòng/trang "
                "hoặc dùng bộ lọc mục tiêu khi thao tác trên máy yếu."
            )
        page_obj = _paginate(employees_qs, filters.get("page"), page_size)
        employee_page_ids = [employee.id for employee in page_obj.object_list]

        cham_cong_qs = (
            _get_attendance_scope_queryset(tenant_id, user=user)
            .filter(
                ca_truc__nhan_vien_id__in=employee_page_ids,
                ca_truc__ngay_truc__range=(period_start, period_end),
            )
            .select_related(
                "ca_truc__nhan_vien",
                "ca_truc__ca_lam_viec",
                "ca_truc__vi_tri_chot__muc_tieu",
            )
            .order_by("ca_truc__nhan_vien_id", "ca_truc__ngay_truc", "-thoi_gian_check_in")
        )
        muc_tieu_id = _as_int(filters.get("muc_tieu_id"))
        if muc_tieu_id:
            cham_cong_qs = cham_cong_qs.filter(ca_truc__vi_tri_chot__muc_tieu_id=muc_tieu_id)

        attendance_by_employee = defaultdict(dict)
        for cham_cong in cham_cong_qs:
            attendance_by_employee[cham_cong.ca_truc.nhan_vien_id].setdefault(
                cham_cong.ca_truc.ngay_truc.day, cham_cong
            )

        report_data = []
        summary = {
            "employee_count": total_filtered,
            "rendered_count": len(employee_page_ids),
            "total_hours": 0,
            "missing_checkout": 0,
            "late_minutes": 0,
            "gps_anomalies": 0,
        }
        for nv in page_obj.object_list:
            row = {"nhan_vien": nv, "days": []}
            total_hours = 0
            total_late = 0
            cc_map = attendance_by_employee.get(nv.id, {})
            for day in days_in_month:
                cc = cc_map.get(day)
                if not cc:
                    row["days"].append({"val": "", "class": "", "title": "Không có dữ liệu"})
                    continue
                total_hours += float(cc.thuc_lam_gio or 0)
                total_late += int(cc.di_muon_phut or 0)
                summary["total_hours"] += float(cc.thuc_lam_gio or 0)
                summary["late_minutes"] += int(cc.di_muon_phut or 0)
                if not cc.thoi_gian_check_out:
                    summary["missing_checkout"] += 1
                    cell = {"val": "No", "class": "text-danger", "title": "Thiếu check-out"}
                elif not cc.vi_tri_hop_le:
                    summary["gps_anomalies"] += 1
                    cell = {"val": "GPS", "class": "text-danger", "title": "GPS bất thường"}
                elif cc.di_muon_phut:
                    cell = {"val": "M", "class": "bg-warning-subtle", "title": f"Đi muộn {cc.di_muon_phut} phút"}
                else:
                    cell = {"val": "X", "class": "bg-success-subtle", "title": "Đủ dữ liệu"}
                row["days"].append(cell)
            row["tong_gio"] = round(total_hours, 2)
            row["tong_muon"] = total_late
            report_data.append(row)

        target_qs = _get_target_scope_queryset(tenant_id, user=user)
        return {
            "report_data": report_data,
            "days_in_month": days_in_month,
            "page_obj": page_obj,
            "summary": summary,
            "matrix_performance_notice": matrix_performance_notice,
            "muc_tieu_list": target_qs[:CANDIDATE_LIMIT],
            **_employee_filter_options(tenant_id, user=user),
        }
=======
    def execute(thang: int, nam: int, tenant_id):
        _, num_days = calendar.monthrange(nam, thang)
        days_in_month = range(1, num_days + 1)

        nhan_vien_list = NhanVien.objects.filter(trang_thai_lam_viec="dang_lam_viec")
        report_data = []

        for nv in nhan_vien_list:
            row = {"nhan_vien": nv, "days": {}}
            total_cong = 0

            cham_cong_qs = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__nhan_vien=nv,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .select_related("ca_truc")
            )
            cc_map = {cc.ca_truc.ngay_truc.day: cc for cc in cham_cong_qs}

            for day in days_in_month:
                cc = cc_map.get(day)
                if cc:
                    status = "X"
                    if cc.thoi_gian_check_in and cc.thoi_gian_check_out:
                        total_cong += 1
                    elif not cc.thoi_gian_check_out:
                        status = "NoOut"
                    row["days"][day] = status
                else:
                    row["days"][day] = ""

            row["total_cong"] = total_cong
            report_data.append(row)

        return {"report_data": report_data, "days_in_month": days_in_month}
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


class GetPersonalAttendanceReportUseCase:
    @staticmethod
<<<<<<< HEAD
    def execute(thang: int, nam: int, nhan_vien_id, tenant_id, filters=None, user=None):
        filters = filters or {}
        selected_nv = None
        report_data = None
        summary = {"total_hours": 0, "work_days": 0, "late_minutes": 0, "early_minutes": 0, "missing_checkout": 0, "gps_anomalies": 0}

        employee_qs = _apply_employee_filters(
            _get_employee_scope_queryset(tenant_id, user=user).order_by("ma_nhan_vien", "ho_ten"), filters
        )
        employee_candidates = employee_qs[:CANDIDATE_LIMIT]

        if nhan_vien_id:
            selected_nv = employee_qs.filter(id=nhan_vien_id).first()
            if selected_nv is not None:
                period_start, period_end = _get_month_date_range(thang, nam)
                qs = (
                    _get_attendance_scope_queryset(tenant_id, user=user)
                    .filter(
                        ca_truc__nhan_vien_id=nhan_vien_id,
                        ca_truc__ngay_truc__range=(period_start, period_end),
                    )
                    .select_related(
                        "ca_truc__nhan_vien",
                        "ca_truc__ca_lam_viec",
                        "ca_truc__vi_tri_chot__muc_tieu",
                    )
                    .order_by("ca_truc__ngay_truc", "ca_truc__ca_lam_viec__gio_bat_dau")
                )
                rows = []
                for cc in qs:
                    summary["total_hours"] += float(cc.thuc_lam_gio or 0)
                    summary["late_minutes"] += int(cc.di_muon_phut or 0)
                    summary["early_minutes"] += int(cc.ve_som_phut or 0)
                    if cc.thoi_gian_check_in:
                        summary["work_days"] += 1
                    if not cc.thoi_gian_check_out:
                        summary["missing_checkout"] += 1
                    if not cc.vi_tri_hop_le:
                        summary["gps_anomalies"] += 1
                    rows.append({
                        "ngay": cc.ca_truc.ngay_truc,
                        "ca": cc.ca_truc.ca_lam_viec.ten_ca if cc.ca_truc.ca_lam_viec else "Ca trực",
                        "muc_tieu": cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu if cc.ca_truc.vi_tri_chot and cc.ca_truc.vi_tri_chot.muc_tieu else "Chưa rõ mục tiêu",
                        "vao": cc.thoi_gian_check_in,
                        "ra": cc.thoi_gian_check_out,
                        "di_muon": cc.di_muon_phut,
                        "ve_som": cc.ve_som_phut,
                        "gio_lam": round(float(cc.thuc_lam_gio or 0), 2),
                        "gps_ok": cc.vi_tri_hop_le,
                    })
                report_data = rows

        return {
            "nhan_vien_list": employee_candidates,
            "employee_total": employee_qs.count(),
            "selected_nv": selected_nv,
            "selected_nhan_vien": selected_nv,
            "report_data": report_data,
            "summary": summary,
            **_employee_filter_options(tenant_id, user=user),
=======
    def execute(thang: int, nam: int, nhan_vien_id, tenant_id):
        selected_nv = None
        report_data = None

        if nhan_vien_id:
            selected_nv = NhanVien.objects.filter(id=nhan_vien_id).first()
            report_data = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__nhan_vien_id=nhan_vien_id,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .order_by("ca_truc__ngay_truc")
            )

        return {
            "nhan_vien_list": NhanVien.objects.filter(
                trang_thai_lam_viec__in=["THUVIEC", "CHINHTHUC", "TAMHOAN", "NGHIVIEC"]
            ).order_by("ho_ten"),
            "selected_nv": selected_nv,
            "report_data": report_data,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        }


class GetTargetAttendanceReportUseCase:
    @staticmethod
<<<<<<< HEAD
    def execute(thang: int, nam: int, muc_tieu_id, tenant_id, filters=None, user=None):
        filters = filters or {}
        report_data = None
        selected_muc_tieu = None
        summary = {"total_hours": 0, "shift_count": 0, "employee_count": 0, "missing_checkout": 0, "gps_anomalies": 0, "late_minutes": 0}
        target_qs = _get_target_scope_queryset(tenant_id, user=user)
        q = (filters.get("target_q") or filters.get("q") or "").strip()
        if q:
            target_qs = target_qs.filter(Q(ten_muc_tieu__icontains=q) | Q(dia_chi__icontains=q) | Q(hop_dong__so_hop_dong__icontains=q))
        target_candidates = target_qs[:CANDIDATE_LIMIT]

        if muc_tieu_id:
            period_start, period_end = _get_month_date_range(thang, nam)
            selected_muc_tieu = target_qs.filter(id=muc_tieu_id).first()
            if selected_muc_tieu is not None:
                qs = (
                    _get_attendance_scope_queryset(tenant_id, user=user)
                    .filter(
                        ca_truc__vi_tri_chot__muc_tieu_id=muc_tieu_id,
                        ca_truc__ngay_truc__range=(period_start, period_end),
                    )
                    .select_related("ca_truc__nhan_vien", "ca_truc__ca_lam_viec", "ca_truc__vi_tri_chot__muc_tieu")
                    .order_by("ca_truc__ngay_truc", "ca_truc__nhan_vien__ho_ten")
                )
                employee_ids = set()
                rows = []
                for cc in qs:
                    employee_ids.add(cc.ca_truc.nhan_vien_id)
                    summary["total_hours"] += float(cc.thuc_lam_gio or 0)
                    summary["shift_count"] += 1
                    summary["late_minutes"] += int(cc.di_muon_phut or 0)
                    if not cc.thoi_gian_check_out:
                        summary["missing_checkout"] += 1
                    if not cc.vi_tri_hop_le:
                        summary["gps_anomalies"] += 1
                    rows.append(cc)
                summary["employee_count"] = len(employee_ids)
                report_data = rows

        return {
            "muc_tieu_list": target_candidates,
            "target_total": target_qs.count(),
            "selected_muc_tieu": selected_muc_tieu,
            "report_data": report_data,
            "summary_data": summary,
=======
    def execute(thang: int, nam: int, muc_tieu_id, tenant_id):
        report_data = None
        selected_muc_tieu = None

        if muc_tieu_id:
            report_data = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__vi_tri_chot__muc_tieu_id=muc_tieu_id,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .order_by("ca_truc__ngay_truc", "ca_truc__nhan_vien__ho_ten")
            )
            selected_muc_tieu = (
                MucTieu.objects.for_tenant(tenant_id).filter(id=muc_tieu_id).first()
            )

        return {
            "muc_tieu_list": MucTieu.objects.for_tenant(tenant_id).order_by("ten_muc_tieu"),
            "selected_muc_tieu": selected_muc_tieu,
            "report_data": report_data,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        }


class GetIncidentReportUseCase:
    @staticmethod
<<<<<<< HEAD
    def execute(thang: int, nam: int, tenant_id, filters=None, paginate=True, user=None):
        filters = filters or {}
        range_start, range_end = _get_month_datetime_range(thang, nam)
        qs = (
            _get_incident_scope_queryset(tenant_id, user=user)
            .filter(created_at__gte=range_start, created_at__lt=range_end)
            .select_related("muc_tieu", "nhan_vien_bao_cao", "nguoi_xu_ly")
            .order_by("-created_at")
        )
        q = (filters.get("q") or "").strip()
        muc_tieu_id = _as_int(filters.get("muc_tieu_id"))
        trang_thai = (filters.get("trang_thai") or "").strip()
        muc_do = (filters.get("muc_do") or "").strip()
        target_qs = _get_target_scope_queryset(tenant_id, user=user)
        if q:
            qs = qs.filter(
                Q(tieu_de__icontains=q)
                | Q(ma_su_co__icontains=q)
                | Q(mo_ta_chi_tiet__icontains=q)
                | Q(nhan_vien_bao_cao__ho_ten__icontains=q)
                | Q(nhan_vien_bao_cao__ma_nhan_vien__icontains=q)
            )
        if muc_tieu_id:
            if target_qs.filter(pk=muc_tieu_id).exists():
                qs = qs.filter(muc_tieu_id=muc_tieu_id)
            else:
                qs = qs.none()
        if trang_thai:
            qs = qs.filter(trang_thai=trang_thai)
        if muc_do:
            qs = qs.filter(muc_do=muc_do)

        summary = {
            "total": qs.count(),
            "open": qs.filter(trang_thai__in=["CHO_XU_LY", "DANG_XU_LY", "CHO_DEN_BU"]).count(),
            "severe": qs.filter(muc_do__in=["CAO", "NGUY_HIEM"]).count(),
            "damage": qs.aggregate(total=Sum("tong_thiet_hai"))["total"] or 0,
        }
        if not paginate:
            return qs
        page_size = min(_as_int(filters.get("page_size")) or REPORT_PAGE_SIZE, 200)
        page_obj = _paginate(qs, filters.get("page"), page_size)
        return {
            "data": page_obj.object_list,
            "page_obj": page_obj,
            "summary": summary,
            "muc_tieu_list": target_qs[:CANDIDATE_LIMIT],
            "trang_thai_choices": BaoCaoSuCo.TRANG_THAI_CHOICES,
            "muc_do_choices": BaoCaoSuCo.MUC_DO_CHOICES,
        }
=======
    def execute(thang: int, nam: int, tenant_id):
        return (
            BaoCaoSuCo.objects.for_tenant(tenant_id)
            .filter(created_at__month=thang, created_at__year=nam)
            .select_related("muc_tieu", "nhan_vien_bao_cao")
            .order_by("-created_at")
        )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
