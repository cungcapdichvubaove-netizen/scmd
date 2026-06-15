# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro executive dashboard views.
"""

import json

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.shortcuts import render

from dashboard.application.executive_dashboard import GetExecutiveDashboardUseCase
from main.dashboard_cta import dashboard_route_url, reverse_or_none
from main.dashboard_router import dashboard_access_required
from reports.access_policies import ReportAccessPolicy


def _executive_cta_url(user, action_key):
    """Resolve executive dashboard CTAs with their matching policy guard."""
    if action_key == "incidents":
        return reverse_or_none("reports:su_co") if ReportAccessPolicy.can_view_incident_reports(user) else None
    if action_key == "attendance":
        return reverse_or_none("reports:cham_cong_muc_tieu") if ReportAccessPolicy.can_view_attendance_reports(user) else None
    if action_key == "reports":
        return dashboard_route_url(user, "reports:report_dashboard", viewname="reports:report_dashboard")
    if action_key == "operations":
        return dashboard_route_url(user, "operations:dashboard_vanhanh")
    if action_key == "inventory":
        return dashboard_route_url(user, "inventory:dashboard")
    if action_key == "accounting":
        return dashboard_route_url(user, "accounting:dashboard")
    if action_key == "workflow":
        return None
    return None


def _format_number(value):
    try:
        return intcomma(int(value or 0))
    except (TypeError, ValueError):
        return "0"


def _format_percent(value):
    try:
        numeric = max(0, min(100, int(round(float(value or 0)))))
    except (TypeError, ValueError):
        numeric = 0
    return f"{numeric}%"


def _format_currency(value):
    return f"{_format_number(value)} đ"


@dashboard_access_required("dashboard:main")
def dashboard_main(request):
    tenant_id = settings.SCMD_ORGANIZATION_ID
    context = GetExecutiveDashboardUseCase.execute(request.user, tenant_id)

    for risk in context.get("top_rui_ro", []):
        risk["action_url"] = _executive_cta_url(request.user, risk.get("action_key"))

    operations_url = _executive_cta_url(request.user, "operations")
    reports_url = _executive_cta_url(request.user, "reports")
    incidents_url = _executive_cta_url(request.user, "incidents")
    attendance_url = _executive_cta_url(request.user, "attendance")
    accounting_url = _executive_cta_url(request.user, "accounting")
    inventory_url = _executive_cta_url(request.user, "inventory")
    workflow_url = _executive_cta_url(request.user, "workflow")

    for target in context.get("top_muc_tieu_can_theo_doi", []):
        target.detail_url = (
            reverse_or_none("operations:chi_tiet_muc_tieu", args=[target.pk])
            if operations_url
            else None
        )

    context["executive_cta_urls"] = {
        "incidents": incidents_url,
        "operations": operations_url,
        "attendance": attendance_url,
        "accounting": accounting_url,
        "inventory": inventory_url,
        "reports": reports_url,
        "workflow": workflow_url,
    }

    context["executive_kpis"] = [
        {
            "label": "Sự cố mở",
            "value": _format_number(context.get("open_incidents")),
            "subvalue": f"{_format_number(context.get('new_incidents_today'))} mới hôm nay",
            "trend": context.get("trend_su_co", {}).get("text", ""),
            "tone": "danger" if context.get("high_severity_incidents", 0) else "warning" if context.get("open_incidents", 0) else "success",
            "url": incidents_url,
            "cta": "Mở sự cố",
        },
        {
            "label": "Ca chưa check-in",
            "value": _format_number(context.get("unchecked_shifts_today")),
            "subvalue": f"{_format_number(context.get('total_shifts_today'))} ca hôm nay",
            "trend": context.get("trend_quan_so", {}).get("text", ""),
            "tone": "warning" if context.get("unchecked_shifts_today", 0) else "success",
            "url": operations_url or attendance_url,
            "cta": "Kiểm tra ca",
        },
        {
            "label": "Mục tiêu rủi ro",
            "value": _format_number(context.get("risk_targets")),
            "subvalue": f"{_format_number(context.get('active_targets'))} mục tiêu hoạt động",
            "trend": context.get("trend_muc_tieu_rui_ro", {}).get("text", ""),
            "tone": "warning" if context.get("risk_targets", 0) else "success",
            "url": operations_url,
            "cta": "Mở vận hành",
        },
        {
            "label": "Hồ sơ chờ duyệt",
            "value": _format_number(context.get("pending_approvals")),
            "subvalue": "Theo dõi đề xuất đang treo",
            "trend": context.get("trend_de_xuat", {}).get("text", ""),
            "tone": "info" if context.get("pending_approvals", 0) else "neutral",
            "url": workflow_url,
            "cta": "Mở hồ sơ",
        },
        {
            "label": "Kho cảnh báo",
            "value": _format_number(context.get("inventory_alerts")),
            "subvalue": "Vật tư dưới ngưỡng tồn",
            "trend": "Đối chiếu cùng dashboard kho",
            "tone": "warning" if context.get("inventory_alerts", 0) else "success",
            "url": inventory_url,
            "cta": "Mở kho",
        },
    ]

    context["immediate_actions"] = [
        {
            "title": "Sự cố nghiêm trọng",
            "value": _format_number(context.get("high_severity_incidents")),
            "detail": "Rà soát người xử lý và mức độ ảnh hưởng ngay trong ngày.",
            "url": incidents_url,
            "cta": "Xem sự cố",
        },
        {
            "title": "Thiếu dữ liệu đầu ca",
            "value": _format_number(context.get("unchecked_shifts_today")),
            "detail": "Bổ sung check-in để tránh sai lệch bảng công cuối ngày.",
            "url": operations_url or attendance_url,
            "cta": "Kiểm tra ca",
        },
        {
            "title": "Mục tiêu cần theo dõi",
            "value": _format_number(context.get("risk_targets")),
            "detail": "Ưu tiên các mục tiêu có sự cố mở hoặc thiếu dữ liệu ca trực.",
            "url": operations_url,
            "cta": "Mở mục tiêu",
        },
    ]

    context["coverage_rate_display"] = _format_percent(context.get("coverage_rate_today"))
    context["projected_revenue_display"] = _format_currency(context.get("projected_revenue_this_month"))
    context["realized_profit_display"] = _format_currency(context.get("realized_profit_this_month"))
=======
SCMD ERP executive dashboard.
"""

import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from dashboard.application.executive_dashboard import GetExecutiveDashboardUseCase


@login_required
def dashboard_main(request):
    # SSOT: Logic nghiệp vụ được tách biệt hoàn toàn khỏi View theo Rule 3.2
    tenant_id = settings.SCMD_ORGANIZATION_ID
    
    # Orchestrate data through Use Case
    context = GetExecutiveDashboardUseCase.execute(request.user, tenant_id)
    
    # Convert chart data to JSON for Template
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    context["chart_labels"] = json.dumps(context.get("chart_labels", []))
    context["data_su_co"] = json.dumps(context.get("data_su_co", []))
    context["data_doanh_thu"] = json.dumps(context.get("data_doanh_thu", []))

    return render(request, "dashboard/main.html", context)
