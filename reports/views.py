# -*- coding: utf-8 -*-
"""
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
from reports.application.report_use_cases import (
    GetIncidentReportUseCase,
    GetMonthlyAttendanceMatrixUseCase,
    GetPersonalAttendanceReportUseCase,
    GetTargetAttendanceReportUseCase,
)
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


@login_required
def tong_hop_cham_cong_thang_view(request):
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


@login_required
def bang_cham_cong_ca_nhan_view(request):
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    nhan_vien_id = request.GET.get("nhan_vien_id")
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    report_context = GetPersonalAttendanceReportUseCase.execute(
        thang,
        nam,
        nhan_vien_id,
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


@login_required
def bang_cham_cong_muc_tieu_view(request):
    thang = int(request.GET.get("thang", timezone.now().month))
    nam = int(request.GET.get("nam", timezone.now().year))
    muc_tieu_id = request.GET.get("muc_tieu_id")
    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    report_context = GetTargetAttendanceReportUseCase.execute(
        thang,
        nam,
        muc_tieu_id,
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


@login_required
def bao_cao_su_co_view(request):
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
        _log_export(
            request,
            "BaoCaoSuCo",
            "Export CSV bao cao su co",
            changes={"thang": thang, "nam": nam, "filters": request.GET.dict()},
        )
        return response

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
    return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


@login_required
def export_attendance_excel(request):
    """
    Xuáº¥t báº£ng cÃ´ng thÃ¡ng ra Excel chuyÃªn nghiá»‡p (Chá»©c nÄƒng má»›i)
    """
    _enforce_export_access(request)
    try:
        month = int(request.GET.get("month", timezone.now().month))
        year = int(request.GET.get("year", timezone.now().year))
        muc_tieu_id = request.GET.get("muc_tieu")

        if muc_tieu_id == "all" or not muc_tieu_id:
            muc_tieu_id = None
        else:
            muc_tieu_id = int(muc_tieu_id)

        excel_buffer, filename = ReportService.generate_attendance_excel(
            month,
            year,
            muc_tieu_id,
            tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
        )

        response = FileResponse(
            excel_buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
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
