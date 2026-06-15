# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro reports views.

Reports are a shared workspace for internal departments. Large employee lists are
handled with multi-level filters and pagination instead of rendering 1000+ rows in
one select box.
"""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from main.dashboard_router import dashboard_access_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from main.audit_utils import export_audit_log, record_export_audit
from main.dashboard_cta import admin_url_if_permitted
from operations.access_policies import IncidentVisibilityPolicy
from operations.models import BaoCaoSuCo
from reports.access_policies import ReportAccessPolicy
=======
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: reports/views.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Logic xá»­ lÃ½ BÃ¡o cÃ¡o & Thá»‘ng kÃª.
             UPDATED: Full logic cho CÃ¡ nhÃ¢n, Má»¥c tiÃªu, Sá»± cá»‘.
             NEW FEATURE: TÃ­ch há»£p Export PDF & Excel chuyÃªn nghiá»‡p.
"""

import csv

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rolepermissions.checkers import has_role

from main.models import AuditLog
from operations.models import BaoCaoSuCo
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from reports.application.report_use_cases import (
    GetIncidentReportUseCase,
    GetMonthlyAttendanceMatrixUseCase,
    GetPersonalAttendanceReportUseCase,
    GetTargetAttendanceReportUseCase,
)
<<<<<<< HEAD
from reports.services import ReportService


def _safe_reverse(viewname, *, args=None, kwargs=None, fallback=None):
    try:
        return reverse(viewname, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return fallback


def _current_tenant_id():
    return getattr(settings, "SCMD_ORGANIZATION_ID", None)


def _int_param(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


def _month_year(request):
    now = timezone.now()
    thang = _int_param(request, "thang", _int_param(request, "month", now.month))
    nam = _int_param(request, "nam", _int_param(request, "year", now.year))
    thang = min(max(thang, 1), 12)
    return thang, nam


def _common_filter_params(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "phong_ban_id": request.GET.get("phong_ban_id", ""),
        "chuc_danh_id": request.GET.get("chuc_danh_id", ""),
        "trang_thai": request.GET.get("trang_thai", ""),
        "muc_tieu_id": request.GET.get("muc_tieu_id", request.GET.get("muc_tieu", "")),
        "target_q": request.GET.get("target_q", "").strip(),
        "muc_do": request.GET.get("muc_do", ""),
        "page": request.GET.get("page", 1),
        "page_size": request.GET.get("page_size", 50),
    }


def _querystring_without(request, *keys):
    query = request.GET.copy()
    for key in keys:
        query.pop(key, None)
    return query.urlencode()


def _filter_context(request, thang, nam, extra=None):
    params = _common_filter_params(request)
    if extra:
        params.update(extra)
    return {
        "filters": params,
        "querystring": request.GET.urlencode(),
        "page_querystring": _querystring_without(request, "page"),
        "thang_range": range(1, 13),
        "nam_range": range(nam - 2, nam + 2),
        "selected_thang": thang,
        "selected_nam": nam,
        "thang": thang,
        "nam": nam,
        "urls": {
            "dashboard": _safe_reverse("reports:report_dashboard"),
            "tong_hop": _safe_reverse("reports:tong_hop_cham_cong"),
            "ca_nhan": _safe_reverse("reports:cham_cong_ca_nhan"),
            "muc_tieu": _safe_reverse("reports:cham_cong_muc_tieu"),
            "su_co": _safe_reverse("reports:su_co"),
            "export_attendance": _safe_reverse("reports:export_attendance_excel"),
        },
    }


def _enforce_export_access(request):
    ReportAccessPolicy.enforce_export_access(request.user)


def _log_export(request, model_name, note, changes=None, object_id=None):
    record_export_audit(
        request,
        module="reports",
        model_name=model_name,
        note=note,
        object_id=object_id,
        changes=changes,
    )


@dashboard_access_required("reports:report_dashboard")
def report_dashboard(request):
    """Trang tổng quan báo cáo."""
    thang, nam = _month_year(request)
    return render(request, "reports/dashboard.html", _filter_context(request, thang, nam))
=======
from .services import ReportService

EXPORT_ALLOWED_ROLES = ["ban_giam_doc", "ke_toan", "quan_ly_vung", "doi_truong"]


def _enforce_export_access(request):
    if request.user.is_superuser or has_role(request.user, EXPORT_ALLOWED_ROLES):
        return
    raise PermissionDenied("Ban khong co quyen xuat du lieu nhay cam.")


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _log_export(request, model_name, note, changes=None, object_id=None):
    AuditLog.objects.create(
        user=request.user,
        tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
        action=AuditLog.Action.EXECUTE,
        module="reports",
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        changes=changes or {},
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        note=note,
        status="SUCCESS",
    )


@login_required
def report_dashboard(request):
    """Trang chá»§ Dashboard BÃ¡o cÃ¡o"""
    return render(request, "reports/dashboard.html")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


@login_required
def tong_hop_cham_cong_thang_view(request):
<<<<<<< HEAD
    ReportAccessPolicy.enforce_attendance_report_access(request.user)
    thang, nam = _month_year(request)
    filters = _common_filter_params(request)
    report_context = GetMonthlyAttendanceMatrixUseCase.execute(
        thang,
        nam,
        _current_tenant_id(),
        filters=filters,
        user=request.user,
    )
    context = _filter_context(request, thang, nam)
    context.update(report_context)
    context["matrix_data"] = report_context["report_data"]
    return render(request, "reports/tong_hop_cham_cong.html", context)
=======
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    report_context = GetMonthlyAttendanceMatrixUseCase.execute(thang, nam, tenant_id)

    return render(
        request,
        "reports/tong_hop_cham_cong.html",
        {
            "report_data": report_context["report_data"],
            "days_in_month": report_context["days_in_month"],
            "selected_thang": thang,
            "selected_nam": nam,
            "thang_range": range(1, 13),
        },
    )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


@login_required
def bang_cham_cong_ca_nhan_view(request):
<<<<<<< HEAD
    ReportAccessPolicy.enforce_attendance_report_access(request.user)
    thang, nam = _month_year(request)
    filters = _common_filter_params(request)
    nhan_vien_id = request.GET.get("nhan_vien_id")
=======
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    nhan_vien_id = request.GET.get("nhan_vien_id")
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    report_context = GetPersonalAttendanceReportUseCase.execute(
        thang,
        nam,
        nhan_vien_id,
<<<<<<< HEAD
        _current_tenant_id(),
        filters=filters,
        user=request.user,
    )
    context = _filter_context(request, thang, nam)
    context.update(report_context)
    return render(request, "reports/cham_cong_ca_nhan.html", context)
=======
        tenant_id,
    )

    return render(
        request,
        "reports/cham_cong_ca_nhan.html",
        {
            "nhan_vien_list": report_context["nhan_vien_list"],
            "selected_nv": report_context["selected_nv"],
            "report_data": report_context["report_data"],
            "thang_range": range(1, 13),
            "selected_thang": thang,
            "selected_nam": nam,
        },
    )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


@login_required
def bang_cham_cong_muc_tieu_view(request):
<<<<<<< HEAD
    ReportAccessPolicy.enforce_attendance_report_access(request.user)
    thang, nam = _month_year(request)
    filters = _common_filter_params(request)
    muc_tieu_id = request.GET.get("muc_tieu_id")
=======
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    muc_tieu_id = request.GET.get("muc_tieu_id")
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    report_context = GetTargetAttendanceReportUseCase.execute(
        thang,
        nam,
        muc_tieu_id,
<<<<<<< HEAD
        _current_tenant_id(),
        filters=filters,
        user=request.user,
    )
    context = _filter_context(request, thang, nam)
    context.update(report_context)
    return render(request, "reports/cham_cong_muc_tieu.html", context)
=======
        tenant_id,
    )

    return render(
        request,
        "reports/cham_cong_muc_tieu.html",
        {
            "muc_tieu_list": report_context["muc_tieu_list"],
            "selected_muc_tieu": report_context["selected_muc_tieu"],
            "report_data": report_context["report_data"],
            "thang_range": range(1, 13),
            "selected_thang": thang,
            "selected_nam": nam,
        },
    )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


@login_required
def bao_cao_su_co_view(request):
<<<<<<< HEAD
    ReportAccessPolicy.enforce_incident_report_access(request.user)
    thang, nam = _month_year(request)
    filters = _common_filter_params(request)
    filters["trang_thai"] = request.GET.get("trang_thai", "")
    if request.GET.get("export") == "csv":
        data_context = GetIncidentReportUseCase.execute(
            thang,
            nam,
            _current_tenant_id(),
            filters=filters,
            paginate=False,
            user=request.user,
        )
        _enforce_export_access(request)
        response = ReportService.generate_incident_csv_response(data_context, thang, nam)
=======
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    data = GetIncidentReportUseCase.execute(thang, nam, tenant_id)

    if request.GET.get("export") == "csv":
        _enforce_export_access(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="SuCo_T{thang}_{nam}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Thá»i gian", "TiÃªu Ä‘á»", "Má»¥c tiÃªu", "Má»©c Ä‘á»™", "Tráº¡ng thÃ¡i"])
        for sc in data:
            writer.writerow(
                [
                    sc.created_at.strftime("%d/%m/%Y %H:%M"),
                    sc.tieu_de,
                    sc.muc_tieu.ten_muc_tieu if sc.muc_tieu else "",
                    sc.get_muc_do_display(),
                    sc.get_trang_thai_display(),
                ]
            )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        _log_export(
            request,
            "BaoCaoSuCo",
            "Export CSV bao cao su co",
            changes={"thang": thang, "nam": nam, "filters": request.GET.dict()},
        )
        return response

<<<<<<< HEAD
    data_context = GetIncidentReportUseCase.execute(
        thang,
        nam,
        _current_tenant_id(),
        filters=filters,
        paginate=True,
        user=request.user,
    )
    for incident in data_context.get("data", []):
        incident.admin_change_url = admin_url_if_permitted(
            request.user,
            "admin:operations_baocaosuco_change",
            "operations.change_baocaosuco",
            args=[incident.pk],
        )

    context = _filter_context(request, thang, nam)
    context.update(data_context)
    return render(request, "reports/bao_cao_su_co.html", context)


@login_required
@export_audit_log(
    module="reports",
    model_name="BaoCaoSuCo",
    note="Export PDF bien ban su co",
    object_id_resolver=lambda request, pk: pk,
    changes_resolver=lambda request, pk: {"incident_id": pk},
)
def export_incident_pdf(request, pk):
    """Xuất biên bản sự cố ra PDF."""
    _enforce_export_access(request)
    incident = get_object_or_404(
        IncidentVisibilityPolicy.visible_incidents(request.user),
        pk=pk,
    )
    pdf_buffer, filename = ReportService.generate_incident_pdf(
        incident.pk,
        request,
        tenant_id=_current_tenant_id(),
        user=request.user,
    )

    if not pdf_buffer:
        return HttpResponse("Không tìm thấy sự cố hoặc lỗi tạo PDF.", status=404)

=======
    return render(
        request,
        "reports/bao_cao_su_co.html",
        {
            "data": data,
            "thang_range": range(1, 13),
            "selected_thang": thang,
            "selected_nam": nam,
        },
    )


@login_required
def export_incident_pdf(request, pk):
    """
    Xuáº¥t biÃªn báº£n sá»± cá»‘ ra PDF (Chá»©c nÄƒng má»›i)
    """
    _enforce_export_access(request)
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    incident = get_object_or_404(BaoCaoSuCo.objects.for_tenant(tenant_id), pk=pk)
    pdf_buffer, filename = ReportService.generate_incident_pdf(
        pk,
        request,
        tenant_id=tenant_id,
    )

    if not pdf_buffer:
        return HttpResponse("KhÃ´ng tÃ¬m tháº¥y sá»± cá»‘ hoáº·c lá»—i táº¡o PDF", status=404)

    _log_export(
        request,
        "BaoCaoSuCo",
        "Export PDF bien ban su co",
        changes={"incident_id": pk},
        object_id=incident.pk,
    )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


@login_required
<<<<<<< HEAD
@export_audit_log(
    module="reports",
    model_name="ChamCong",
    note="Export Excel bang cong",
    changes_resolver=lambda request: {
        "month": int(request.GET.get("month", request.GET.get("thang", timezone.now().month))),
        "year": int(request.GET.get("year", request.GET.get("nam", timezone.now().year))),
        "muc_tieu_id": request.GET.get("muc_tieu", request.GET.get("muc_tieu_id")),
        "row_count": getattr(request, "_scmd_export_row_count", None),
    },
)
def export_attendance_excel(request):
    """Xuất bảng công tháng ra Excel."""
    ReportAccessPolicy.enforce_attendance_report_access(request.user)
    _enforce_export_access(request)
    try:
        month = int(request.GET.get("month", request.GET.get("thang", timezone.now().month)))
        year = int(request.GET.get("year", request.GET.get("nam", timezone.now().year)))
        muc_tieu_id = request.GET.get("muc_tieu", request.GET.get("muc_tieu_id"))
=======
def export_attendance_excel(request):
    """
    Xuáº¥t báº£ng cÃ´ng thÃ¡ng ra Excel chuyÃªn nghiá»‡p (Chá»©c nÄƒng má»›i)
    """
    _enforce_export_access(request)
    try:
        month = int(request.GET.get("month", timezone.now().month))
        year = int(request.GET.get("year", timezone.now().year))
        muc_tieu_id = request.GET.get("muc_tieu")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        if muc_tieu_id == "all" or not muc_tieu_id:
            muc_tieu_id = None
        else:
            muc_tieu_id = int(muc_tieu_id)

<<<<<<< HEAD
        export_result = ReportService.generate_attendance_excel(
            month,
            year,
            muc_tieu_id,
            tenant_id=_current_tenant_id(),
            user=request.user,
        )
        if len(export_result) == 3:
            excel_buffer, filename, row_count = export_result
        else:
            # Backward-compatible guard for tests or downstream overrides that
            # still return the historical two-item tuple.
            excel_buffer, filename = export_result
            row_count = None
        request._scmd_export_row_count = row_count
        return FileResponse(
=======
        excel_buffer, filename = ReportService.generate_attendance_excel(
            month,
            year,
            muc_tieu_id,
            tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
        )

        response = FileResponse(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            excel_buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
<<<<<<< HEAD
    except ValueError:
        return HttpResponse("Tham số không hợp lệ.", status=400)
    except ValidationError as exc:
        message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
        return HttpResponse(message, status=400)
=======
        _log_export(
            request,
            "ChamCong",
            "Export Excel bang cong",
            changes={
                "month": month,
                "year": year,
                "muc_tieu_id": muc_tieu_id,
                "filters": request.GET.dict(),
            },
        )
        return response
    except ValueError:
        return HttpResponse("Tham sá»‘ khÃ´ng há»£p lá»‡", status=400)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
