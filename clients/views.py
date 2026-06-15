# file: clients/views.py
<<<<<<< HEAD
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from typing import cast

from django.conf import settings
from django.contrib.auth.decorators import login_required
from main.dashboard_router import dashboard_access_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.shortcuts import render

from core.datetime_ranges import local_date_range_bounds, local_day_bounds
from main.dashboard_cta import admin_url_if_permitted

from .models import CoHoiKinhDoanh, HopDong, KhachHangTiemNang, MucTieu
from clients.application.receivable_report_use_cases import CustomerReceivableReportUseCase


def _tenant_id():
    return getattr(settings, "SCMD_ORGANIZATION_ID", None)


def _safe_reverse(name: str, *args, fallback: str | None = None, **kwargs) -> str | None:
    """Return a URL without allowing optional dashboard CTAs to crash the page."""
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return fallback


def _admin_url_if_permitted(user, viewname, permission_codename, *args, fallback: str | None = None, **kwargs) -> str | None:
    return admin_url_if_permitted(user, viewname, permission_codename, args=args or None, kwargs=kwargs or None) or fallback


def _with_query(url: str | None, **params) -> str | None:
    if not url:
        return None
    clean_params = {key: value for key, value in params.items() if value not in (None, "")}
    if not clean_params:
        return url
    return f"{url}?{urlencode(clean_params)}"


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _date_range_from_request(request):
    today = timezone.localdate()
    period = request.GET.get("period", "month")
    if period == "today":
        return period, today, today
    if period == "7d":
        return period, today - timedelta(days=6), today
    if period == "30d":
        return period, today - timedelta(days=29), today
    # Default: current calendar month.
    return "month", today.replace(day=1), today


@dashboard_access_required("clients:dashboard_crm")
def dashboard_view(request):
    """
    Dashboard Kinh doanh & CRM.

    Mục tiêu: là màn hình làm việc chính cho bộ phận kinh doanh sau đăng nhập,
    tập trung vào lead mới, pipeline, hợp đồng, cảnh báo tái ký và các CTA thao tác.
    """
    tenant_id = _tenant_id()
    today = timezone.localdate()
    period, date_from, date_to = _date_range_from_request(request)
    next_30_days = today + timedelta(days=30)
    add_lead_url = _admin_url_if_permitted(request.user, "admin:clients_khachhangtiemnang_add", "clients.add_khachhangtiemnang")
    add_opportunity_url = _admin_url_if_permitted(request.user, "admin:clients_cohoikinhdoanh_add", "clients.add_cohoikinhdoanh")
    add_contract_url = _admin_url_if_permitted(request.user, "admin:clients_hopdong_add", "clients.add_hopdong")
    lead_list_url = _admin_url_if_permitted(request.user, "admin:clients_khachhangtiemnang_changelist", "clients.view_khachhangtiemnang")
    opportunity_list_url = _admin_url_if_permitted(request.user, "admin:clients_cohoikinhdoanh_changelist", "clients.view_cohoikinhdoanh")
    contract_list_url = _admin_url_if_permitted(request.user, "admin:clients_hopdong_changelist", "clients.view_hopdong")
    pipeline_url = _safe_reverse("clients:pipeline")
    receivable_list_url = _admin_url_if_permitted(request.user, "admin:clients_congno_changelist", "clients.view_congno")
    period_start, period_end = local_date_range_bounds(date_from, date_to)
    today_start, today_end = local_day_bounds(today)
    stale_cutoff_exclusive = local_day_bounds(today - timedelta(days=7))[1]

    leads_qs = cast("TenantAwareManager", KhachHangTiemNang.objects).for_tenant(tenant_id)
    opportunities_qs = cast("TenantAwareManager", CoHoiKinhDoanh.objects).for_tenant(tenant_id).select_related(
        "khach_hang_tiem_nang", "nguoi_phu_trach"
    )
    contracts_qs = cast("TenantAwareManager", HopDong.objects).for_tenant(tenant_id).select_related(
        "khach_hang_cu", "co_hoi", "co_hoi__khach_hang_tiem_nang"
    )
    targets_qs = MucTieu.objects.filter(hop_dong__tenant_id=tenant_id).select_related(
        "hop_dong", "quan_ly_muc_tieu"
    )

    new_leads_period = leads_qs.filter(ngay_tao__gte=period_start, ngay_tao__lt=period_end)
    new_leads_today = leads_qs.filter(ngay_tao__gte=today_start, ngay_tao__lt=today_end).count()
    total_leads = leads_qs.count()
    nurturing_leads = leads_qs.filter(trang_thai__in=["MOI", "TIEM_NANG", "BAO_GIA"]).count()

    open_opportunities_qs = opportunities_qs.exclude(
        trang_thai__in=[
            CoHoiKinhDoanh.TrangThai.THANH_CONG,
            CoHoiKinhDoanh.TrangThai.THAT_BAI,
        ]
    )
    open_opportunities = open_opportunities_qs.count()
    won_opportunities = opportunities_qs.filter(
        trang_thai=CoHoiKinhDoanh.TrangThai.THANH_CONG,
        ngay_tao__gte=period_start,
        ngay_tao__lt=period_end,
    ).count()
    lost_opportunities = opportunities_qs.filter(
        trang_thai=CoHoiKinhDoanh.TrangThai.THAT_BAI,
        ngay_tao__gte=period_start,
        ngay_tao__lt=period_end,
    ).count()
    pipeline_value = _money(open_opportunities_qs.aggregate(total=Sum("gia_tri_uoc_tinh"))["total"])

    active_contracts_qs = contracts_qs.filter(trang_thai="HIEU_LUC")
    active_contracts = active_contracts_qs.count()
    monthly_revenue = _money(active_contracts_qs.aggregate(total=Sum("gia_tri"))["total"])
    active_targets = targets_qs.filter(hop_dong__trang_thai="HIEU_LUC").count()

    expiring_contracts_qs = contracts_qs.filter(
        ngay_het_han__range=[today, next_30_days]
    ).order_by("ngay_het_han")
    expiring_contracts_count = expiring_contracts_qs.count()

    # Pipeline theo đúng thứ tự bán hàng.
    pipeline_counts = {
        row["trang_thai"]: row["count"]
        for row in opportunities_qs.values("trang_thai").annotate(count=Count("id"))
    }
    pipeline_values = {
        row["trang_thai"]: _money(row["total"])
        for row in opportunities_qs.values("trang_thai").annotate(total=Sum("gia_tri_uoc_tinh"))
    }
    ordered_stages = [
        CoHoiKinhDoanh.TrangThai.MOI,
        CoHoiKinhDoanh.TrangThai.LIEN_HE,
        CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA,
        CoHoiKinhDoanh.TrangThai.THUONG_LUONG,
        CoHoiKinhDoanh.TrangThai.THANH_CONG,
    ]
    stage_labels = dict(CoHoiKinhDoanh.TrangThai.choices)
    max_stage_count = max([pipeline_counts.get(stage, 0) for stage in ordered_stages] + [1])
    pipeline_stages = []
    for stage in ordered_stages:
        count = pipeline_counts.get(stage, 0)
        pipeline_stages.append(
            {
                "key": stage,
                "label": stage_labels.get(stage, stage),
                "count": count,
                "value": pipeline_values.get(stage, Decimal("0")),
                "percent": int((count / max_stage_count) * 100) if max_stage_count else 0,
                "url": _with_query(opportunity_list_url, trang_thai__exact=stage),
            }
        )

    # Danh sách hành động ưu tiên cho sales/CSKH.
    hot_leads = leads_qs.filter(trang_thai__in=["MOI", "TIEM_NANG"]).order_by("-ngay_tao")[:8]
    key_opportunities = open_opportunities_qs.order_by("-gia_tri_uoc_tinh", "-ngay_tao")[:8]
    recent_contracts = list(contracts_qs.order_by("-ngay_ky", "-id")[:6])
    expiring_contracts = list(expiring_contracts_qs[:8])
    hot_leads = list(hot_leads)
    key_opportunities = list(key_opportunities)

    for hd in expiring_contracts + recent_contracts:
        hd.dashboard_url = _admin_url_if_permitted(
            request.user, "admin:clients_hopdong_change", "clients.change_hopdong", hd.pk
        )
    for lead in hot_leads:
        lead.dashboard_url = _admin_url_if_permitted(
            request.user, "admin:clients_khachhangtiemnang_change", "clients.change_khachhangtiemnang", lead.pk
        )
    for opp in key_opportunities:
        opp.dashboard_url = _admin_url_if_permitted(
            request.user, "admin:clients_cohoikinhdoanh_change", "clients.change_cohoikinhdoanh", opp.pk
        )

    stale_leads_count = leads_qs.filter(
        trang_thai__in=["MOI", "TIEM_NANG"],
        ngay_tao__lt=stale_cutoff_exclusive,
    ).count()
    quotation_opportunities_count = opportunities_qs.filter(
        trang_thai=CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA
    ).count()
    negotiation_opportunities_count = opportunities_qs.filter(
        trang_thai=CoHoiKinhDoanh.TrangThai.THUONG_LUONG
    ).count()
    won_without_contract_count = opportunities_qs.filter(
        trang_thai=CoHoiKinhDoanh.TrangThai.THANH_CONG,
        hop_dong__isnull=True,
    ).count()

    action_items = []
    if expiring_contracts_count:
        action_items.append(
            {
                "priority": "Cao",
                "type": "Tái ký hợp đồng",
                "title": f"{expiring_contracts_count} hợp đồng hết hạn trong 30 ngày",
                "description": "Cần gọi khách hàng, xác nhận nhu cầu và chuẩn bị phụ lục/tái ký.",
                "url": contract_list_url,
                "icon": "fa-file-signature",
            }
        )
    if won_without_contract_count:
        action_items.append(
            {
                "priority": "Cao",
                "type": "Chuyển đổi hợp đồng",
                "title": f"{won_without_contract_count} cơ hội đã thắng chưa tạo hợp đồng",
                "description": "Cần tạo hợp đồng và mục tiêu triển khai để bàn giao vận hành.",
                "url": add_contract_url,
                "icon": "fa-handshake",
            }
        )
    if quotation_opportunities_count:
        action_items.append(
            {
                "priority": "Vừa",
                "type": "Theo dõi báo giá",
                "title": f"{quotation_opportunities_count} cơ hội đang ở giai đoạn báo giá",
                "description": "Cần hẹn lịch follow-up và ghi nhận phản hồi khách hàng.",
                "url": _with_query(opportunity_list_url, trang_thai__exact=CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA),
                "icon": "fa-file-invoice-dollar",
            }
        )
    if stale_leads_count:
        action_items.append(
            {
                "priority": "Vừa",
                "type": "Chăm sóc lead",
                "title": f"{stale_leads_count} lead chưa chuyển trạng thái sau 7 ngày",
                "description": "Cần rà soát, gọi lại hoặc loại bỏ để giữ pipeline sạch.",
                "url": _with_query(lead_list_url, trang_thai__in="MOI,TIEM_NANG"),
                "icon": "fa-phone-volume",
            }
        )
    can_view_receivables = True
    try:
        receivable_report = CustomerReceivableReportUseCase.execute(tenant_id=tenant_id, today=today, user=request.user)
    except PermissionDenied:
        can_view_receivables = False
        receivable_report = {
            "overdue_receivables": [],
            "overdue_receivables_count": 0,
            "partial_paid_invoices": [],
            "partial_paid_invoices_count": 0,
            "receivable_totals": {},
        }
    if receivable_report["overdue_receivables_count"]:
        action_items.append(
            {
                "priority": "Cao",
                "type": "Công nợ quá hạn",
                "title": f"{receivable_report['overdue_receivables_count']} công nợ khách hàng đã quá hạn",
                "description": "Cần rà soát chứng từ thanh toán, phân bổ tiền thu và nhắc nợ theo hợp đồng.",
                "url": receivable_list_url,
                "icon": "fa-scale-balanced",
            }
        )

    if not action_items:
        action_items.append(
            {
                "priority": "OK",
                "type": "Pipeline ổn định",
                "title": "Chưa có cảnh báo kinh doanh nghiêm trọng",
                "description": "Tiếp tục bổ sung lead, cập nhật cơ hội và duy trì lịch chăm sóc khách hàng.",
                "url": pipeline_url,
                "icon": "fa-check-circle",
            }
        )

    lead_sources = list(
        leads_qs.values("nguon").annotate(count=Count("id")).order_by("-count")[:6]
    )
    source_labels = dict(KhachHangTiemNang.NGUON_DEN)
    max_source_count = max([item["count"] for item in lead_sources] + [1])
    for item in lead_sources:
        item["label"] = source_labels.get(item["nguon"], item["nguon"] or "Không rõ")
        item["percent"] = int((item["count"] / max_source_count) * 100)
        item["url"] = _with_query(lead_list_url, nguon__exact=item["nguon"])

    hero_metrics = [
        {
            "label": "Lead mới",
            "value": new_leads_period.count(),
            "hint": f"Hôm nay {new_leads_today} · Tổng {total_leads}",
            "url": lead_list_url,
        },
        {
            "label": "Cơ hội mở",
            "value": open_opportunities,
            "hint": f"BG {quotation_opportunities_count} · TL {negotiation_opportunities_count}",
            "url": opportunity_list_url,
        },
        {
            "label": "Pipeline",
            "value": pipeline_value,
            "hint": f"Doanh thu HĐ {active_contracts} hợp đồng hiệu lực",
            "url": pipeline_url,
            "money": True,
        },
        {
            "label": "Cần tái ký",
            "value": expiring_contracts_count,
            "hint": f"HĐ hiệu lực {active_contracts} · MT {active_targets}",
            "url": contract_list_url,
            "alert": bool(expiring_contracts_count),
        },
    ]
    sales_priority_cards = [
        {
            "title": "Lead mới trong kỳ",
            "value": new_leads_period.count(),
            "note": f"Hôm nay {new_leads_today} lead, tổng {total_leads} lead.",
            "url": lead_list_url,
            "cta": "Mở lead",
            "tone": "info",
        },
        {
            "title": "Báo giá cần follow-up",
            "value": quotation_opportunities_count,
            "note": "Rà soát báo giá đã gửi để không mất cơ hội chuyển thương thảo.",
            "url": _with_query(opportunity_list_url, trang_thai__exact=CoHoiKinhDoanh.TrangThai.GUI_BAO_GIA),
            "cta": "Mở báo giá",
            "tone": "warning",
        },
        {
            "title": "Hợp đồng cần tái ký",
            "value": expiring_contracts_count,
            "note": "Ưu tiên làm việc với khách sắp hết hạn trong 30 ngày tới.",
            "url": contract_list_url,
            "cta": "Mở hợp đồng",
            "tone": "danger",
        },
        {
            "title": "Công nợ quá hạn",
            "value": receivable_report["overdue_receivables_count"],
            "note": "Phối hợp với kế toán để chốt thu tiền và không ảnh hưởng triển khai.",
            "url": receivable_list_url if can_view_receivables else None,
            "cta": "Mở công nợ",
            "tone": "danger",
        },
    ]
    compact_kpis = [
        {
            "label": "Lead cần nuôi dưỡng",
            "value": nurturing_leads,
            "note": "Lead mới, tiềm năng và đã báo giá.",
            "url": _with_query(lead_list_url, trang_thai__in="MOI,TIEM_NANG,BAO_GIA"),
        },
        {
            "label": "Cơ hội mở",
            "value": open_opportunities,
            "note": f"Thương thảo {negotiation_opportunities_count} · thắng {won_opportunities}",
            "url": opportunity_list_url,
        },
        {
            "label": "Doanh thu HĐ hiệu lực",
            "value": monthly_revenue,
            "note": f"{active_contracts} hợp đồng đang hiệu lực · {active_targets} mục tiêu",
            "url": contract_list_url,
            "money": True,
        },
        {
            "label": "Pipeline giá trị",
            "value": pipeline_value,
            "note": f"{open_opportunities} cơ hội chưa chốt · thất bại {lost_opportunities}",
            "url": pipeline_url,
            "money": True,
        },
    ]

    context = {
        "period": period,
        "date_from": date_from,
        "date_to": date_to,
        "total_leads": total_leads,
        "new_leads_today": new_leads_today,
        "new_leads_period": new_leads_period.count(),
        "nurturing_leads": nurturing_leads,
        "open_opportunities": open_opportunities,
        "pipeline_value": pipeline_value,
        "won_opportunities": won_opportunities,
        "lost_opportunities": lost_opportunities,
        "active_contracts": active_contracts,
        "active_targets": active_targets,
        "monthly_revenue": monthly_revenue,
        "expiring_contracts_count": expiring_contracts_count,
        "quotation_opportunities_count": quotation_opportunities_count,
        "negotiation_opportunities_count": negotiation_opportunities_count,
        "won_without_contract_count": won_without_contract_count,
        "hero_metrics": [item for item in hero_metrics if item.get("url")],
        "sales_priority_cards": [item for item in sales_priority_cards if item.get("url")],
        "compact_kpis": [item for item in compact_kpis if item.get("url")],
        "pipeline_stages": pipeline_stages,
        "lead_sources": lead_sources,
        "action_items": action_items[:6],
        "hot_leads": hot_leads,
        "key_opportunities": key_opportunities,
        "expiring_contracts": expiring_contracts,
        "recent_contracts": recent_contracts,
        "overdue_receivables": receivable_report["overdue_receivables"],
        "overdue_receivables_count": receivable_report["overdue_receivables_count"],
        "partial_paid_invoices": receivable_report["partial_paid_invoices"],
        "partial_paid_invoices_count": receivable_report["partial_paid_invoices_count"],
        "receivable_totals": receivable_report["receivable_totals"],
        "urls": {
            "add_lead": add_lead_url,
            "add_opportunity": add_opportunity_url,
            "add_contract": add_contract_url,
            "lead_list": lead_list_url,
            "opportunity_list": opportunity_list_url,
            "contract_list": contract_list_url,
            "pipeline": pipeline_url,
            "receivables": receivable_list_url,
        },
    }
    return render(request, "clients/dashboard_crm.html", context)


@login_required
def pipeline_view(request):
    """Giao diện Kanban Board cho Sales."""
=======
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import json

from .models import KhachHangTiemNang, HopDong, CoHoiKinhDoanh

@login_required
def dashboard_view(request):
    """
    DASHBOARD KINH DOANH (CRM)
    """
    today = timezone.now().date()
    
    # 1. KPI TỔNG QUAN
    total_leads = KhachHangTiemNang.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).count()
    active_contracts = HopDong.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(trang_thai='HIEU_LUC').count()
    
    # Tổng giá trị hợp đồng đang chạy (Doanh thu tháng dự kiến)
    monthly_revenue = HopDong.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(trang_thai='HIEU_LUC').aggregate(Sum('gia_tri'))['gia_tri__sum'] or 0
    
    # Cơ hội đang theo đuổi
    open_opportunities = CoHoiKinhDoanh.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).exclude(
        trang_thai__in=['THANHCONG', 'THATBAI']
    ).count()

    # 2. CẢNH BÁO HỢP ĐỒNG (30 ngày tới)
    next_30_days = today + timedelta(days=30)
    expiring_contracts = HopDong.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(
        ngay_het_han__range=[today, next_30_days]
    ).select_related('co_hoi__khach_hang_tiem_nang').order_by('ngay_het_han')

    # 3. DỮ LIỆU BIỂU ĐỒ PHỄU (PIPELINE)
    pipeline_stats = CoHoiKinhDoanh.objects.values('trang_thai').annotate(count=Count('id'))
    
    # Sắp xếp theo quy trình: Mới -> Liên hệ -> Báo giá -> Thương thảo -> Chốt
    ordered_stages = ['MOI', 'LIENHE', 'BAOGIA', 'THUONGLUONG', 'THANHCONG']
    status_dict = {item['trang_thai']: item['count'] for item in pipeline_stats}
    
    chart_labels = []
    chart_data = []
    
    for stage in ordered_stages:
        label = dict(CoHoiKinhDoanh.TrangThai.choices).get(stage, stage)
        chart_labels.append(label)
        chart_data.append(status_dict.get(stage, 0))

    # 4. KHÁCH HÀNG MỚI NHẤT
    recent_leads = KhachHangTiemNang.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).order_by('-ngay_tao')[:5]

    context = {
        'total_leads': total_leads,
        'active_contracts': active_contracts,
        'monthly_revenue': monthly_revenue,
        'open_opportunities': open_opportunities,
        'expiring_contracts': expiring_contracts,
        'recent_leads': recent_leads,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, "clients/dashboard_crm.html", context)

@login_required
def pipeline_view(request):
    """
    Giao diện Kanban Board cho Sales
    """
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    stages = CoHoiKinhDoanh.TrangThai.choices
    pipeline_stages = {}

    for stage_key, stage_name in stages:
<<<<<<< HEAD
        opportunities = cast("TenantAwareManager", CoHoiKinhDoanh.objects).for_tenant(_tenant_id()).filter(
=======
        opportunities = CoHoiKinhDoanh.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            trang_thai=stage_key
        ).select_related("khach_hang_tiem_nang", "nguoi_phu_trach")

        summary = opportunities.aggregate(
            total_value=Sum("gia_tri_uoc_tinh"), deal_count=Count("id")
        )

<<<<<<< HEAD
        opportunities = list(opportunities)
        for opportunity in opportunities:
            opportunity.admin_change_url = _admin_url_if_permitted(
                request.user,
                "admin:clients_cohoikinhdoanh_change",
                "clients.change_cohoikinhdoanh",
                opportunity.pk,
            )

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        pipeline_stages[stage_key] = {
            "name": stage_name,
            "opportunities": opportunities,
            "total_value": summary["total_value"] or 0,
            "deal_count": summary["deal_count"],
        }

<<<<<<< HEAD
    return render(request, "clients/pipeline.html", {"pipeline_stages": pipeline_stages})
=======
    return render(request, "clients/pipeline.html", {"pipeline_stages": pipeline_stages})
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
