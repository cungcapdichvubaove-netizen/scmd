# file: clients/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import json

from .models import KhachHangTiemNang, HopDong, CoHoiKinhDoanh

@login_required
def dashboard_view(request):
    """
    DASHBOARD KINH DOANH (CRM)
    """
    today = timezone.now().date()
    
    # 1. KPI TỔNG QUAN
    total_leads = KhachHangTiemNang.objects.count()
    active_contracts = HopDong.objects.filter(trang_thai='HIEU_LUC').count()
    
    # Tổng giá trị hợp đồng đang chạy (Doanh thu tháng dự kiến)
    monthly_revenue = HopDong.objects.filter(trang_thai='HIEU_LUC').aggregate(Sum('gia_tri'))['gia_tri__sum'] or 0
    
    # Cơ hội đang theo đuổi
    open_opportunities = CoHoiKinhDoanh.objects.exclude(
        trang_thai__in=['THANHCONG', 'THATBAI']
    ).count()

    # 2. CẢNH BÁO HỢP ĐỒNG (30 ngày tới)
    next_30_days = today + timedelta(days=30)
    expiring_contracts = HopDong.objects.filter(
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
    recent_leads = KhachHangTiemNang.objects.order_by('-ngay_tao')[:5]

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
    stages = CoHoiKinhDoanh.TrangThai.choices
    pipeline_stages = {}

    for stage_key, stage_name in stages:
        opportunities = CoHoiKinhDoanh.objects.filter(
            trang_thai=stage_key
        ).select_related("khach_hang_tiem_nang", "nguoi_phu_trach")

        summary = opportunities.aggregate(
            total_value=Sum("gia_tri_uoc_tinh"), deal_count=Count("id")
        )

        pipeline_stages[stage_key] = {
            "name": stage_name,
            "opportunities": opportunities,
            "total_value": summary["total_value"] or 0,
            "deal_count": summary["deal_count"],
        }

    return render(request, "clients/pipeline.html", {"pipeline_stages": pipeline_stages})