# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: inspection/views.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: Views module Thanh tra.
             MERGED: Giá»¯ logic cÅ© + TÃ­ch há»£p Hybrid Trust (GPS check).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from main.dashboard_cta import admin_url_if_permitted, reverse_or_none
from django.contrib.auth.decorators import login_required
from main.dashboard_router import dashboard_access_required
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import math
from pathlib import Path
from rolepermissions.decorators import has_permission_decorator
from django.core.exceptions import PermissionDenied, ValidationError
from main.audit_utils import export_audit_log

# Models & Forms
from .models import LoaiTuanTra, LuotTuanTra, DiemTuanTra, GhiNhanTuanTra, BienBanViPham, DotThanhTra, BuoiHuanLuyen
from users.models import NhanVien
from operations.models import PhanCongCaTruc, ChamCong
from .forms import BienBanViPhamForm, DotThanhTraForm

# Application Use Cases
from .application.patrol_use_cases import (
    StartPatrolSessionUseCase,
    RecordPatrolCheckpointUseCase,
    CompletePatrolSessionUseCase
)
from .application.violation_use_cases import CreateViolationUseCase

# Libs for PDF
import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab import rl_config



def _safe_reverse(viewname, *, args=None):
    """Reverse admin/action URL without crashing dashboard when an admin model is not registered yet."""
    return reverse_or_none(viewname, args=args)


def _admin_url_if_permitted(user, viewname, permission_codename, *, args=None):
    return admin_url_if_permitted(user, viewname, permission_codename, args=args)


def _reportlab_bold_font_name():
    """Register a Unicode-capable bold font for PDF exports.

    Docker images should provide DejaVu Sans.  Keep a fallback to ReportLab's
    bundled Vera font so local dev/export paths still work when system fonts are
    missing, even though DejaVu remains the preferred runtime font for Vietnamese.
    """

    font_name = "SCMDReportBold"
    registered = getattr(pdfmetrics, "_fonts", {})
    if font_name in registered:
        return font_name

    candidate_paths = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path(rl_config.TTFSearchPath[0]) / "VeraBd.ttf" if getattr(rl_config, "TTFSearchPath", None) else None,
    ]
    for candidate in candidate_paths:
        if candidate and candidate.exists():
            pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
            return font_name

    return "Helvetica-Bold"

def get_nv(request):
    try: return request.user.nhan_vien
    except: return None

# ==============================================================================
# WEB DASHBOARD & TOOLS (CODE CÅ¨ GIá»® NGUYÃŠN)
# ==============================================================================

@dashboard_access_required("inspection:dashboard")
def dashboard_view(request):
    """Dashboard nghiá»‡p vá»¥ cho phÃ²ng Thanh tra & GiÃ¡m sÃ¡t.

    Má»¥c tiÃªu cá»§a mÃ n hÃ¬nh nÃ y lÃ  phá»¥c vá»¥ trÆ°á»Ÿng/phÃ³ phÃ²ng Thanh tra & GiÃ¡m sÃ¡t:
    Æ°u tiÃªn há»“ sÆ¡ cáº§n xá»­ lÃ½, má»¥c tiÃªu khÃ´ng Ä‘áº¡t, biÃªn báº£n vi pháº¡m, báº¥t thÆ°á»ng
    tuáº§n tra vÃ  lá»‹ch huáº¥n luyá»‡n. View váº«n giá»¯ cÃ¡c biáº¿n tuáº§n tra cÅ© Ä‘á»ƒ khÃ´ng lÃ m
    vá»¡ cÃ¡c thÃ nh pháº§n/template Ä‘ang phá»¥ thuá»™c.
    """
    today = timezone.localdate()
    now = timezone.now()
    period = request.GET.get('period', 'month')
    if period == 'today':
        date_from = today
        period_label = 'Hôm nay'
    elif period == '7d':
        date_from = today - timedelta(days=6)
        period_label = '7 ngày gần nhất'
    else:
        date_from = today.replace(day=1)
        period = 'month'
        period_label = 'Tháng này'
    start_week = today - timedelta(days=today.weekday())

    can_add_violation = request.user.has_perm('inspection.add_bienbanvipham')
    can_view_violation = request.user.has_perm('inspection.view_bienbanvipham')
    can_change_violation = request.user.has_perm('inspection.change_bienbanvipham')
    can_add_inspection = request.user.has_perm('inspection.add_dotthanhtra')
    can_view_inspection = request.user.has_perm('inspection.view_dotthanhtra')
    can_change_inspection = request.user.has_perm('inspection.change_dotthanhtra')
    can_add_training = request.user.has_perm('inspection.add_buoihuanluyen')
    can_view_training = request.user.has_perm('inspection.view_buoihuanluyen')
    can_change_training = request.user.has_perm('inspection.change_buoihuanluyen')
    can_view_routes = request.user.has_perm('inspection.view_loaituantra')

    add_violation_url = _admin_url_if_permitted(request.user, 'admin:inspection_bienbanvipham_add', 'inspection.add_bienbanvipham') if can_add_violation else None
    add_inspection_url = _admin_url_if_permitted(request.user, 'admin:inspection_dotthanhtra_add', 'inspection.add_dotthanhtra') if can_add_inspection else None
    add_training_url = _admin_url_if_permitted(request.user, 'admin:inspection_buoihuanluyen_add', 'inspection.add_buoihuanluyen') if can_add_training else None
    violation_changelist_url = _admin_url_if_permitted(request.user, 'admin:inspection_bienbanvipham_changelist', 'inspection.view_bienbanvipham') if can_view_violation else None
    inspection_changelist_url = _admin_url_if_permitted(request.user, 'admin:inspection_dotthanhtra_changelist', 'inspection.view_dotthanhtra') if can_view_inspection else None
    training_changelist_url = _admin_url_if_permitted(request.user, 'admin:inspection_buoihuanluyen_changelist', 'inspection.view_buoihuanluyen') if can_view_training else None
    route_changelist_url = _admin_url_if_permitted(request.user, 'admin:inspection_loaituantra_changelist', 'inspection.view_loaituantra') if can_view_routes else None

    total_routes = LoaiTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).count()
    today_patrols = LuotTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(thoi_gian_bat_dau__date=today)
    period_patrols = LuotTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(thoi_gian_bat_dau__date__gte=date_from)
    active_patrols = (
        LuotTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai='DANG_DI')
        .select_related('nhan_vien', 'loai_tuan_tra', 'loai_tuan_tra__muc_tieu')
        .prefetch_related('ghi_nhan', 'loai_tuan_tra__cac_diem')
        .order_by('-thoi_gian_bat_dau')
    )

    dang_di = today_patrols.filter(trang_thai='DANG_DI').count()
    hoan_thanh = today_patrols.filter(trang_thai='HOAN_THANH').count()
    bo_do = today_patrols.filter(trang_thai='BO_DO').count()
    tong_luot_hom_nay = today_patrols.count()
    ty_le = round((hoan_thanh / tong_luot_hom_nay) * 100) if tong_luot_hom_nay else 0

    inspections_today = DotThanhTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(thoi_gian_den__date=today)
    inspections_period = DotThanhTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(thoi_gian_den__date__gte=date_from)
    failed_inspections_today = inspections_today.filter(ket_qua='KHONG_DAT')
    failed_inspections_period = inspections_period.filter(ket_qua='KHONG_DAT')
    passed_inspections_period_count = inspections_period.filter(ket_qua='DAT').count()
    inspections_period_count = inspections_period.count()
    quality_rate = round((passed_inspections_period_count / inspections_period_count) * 100) if inspections_period_count else 0

    violations_period = BienBanViPham.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(ngay_vi_pham__date__gte=date_from)
    pending_violations = (
        BienBanViPham.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai='CHO_DUYET')
        .select_related('doi_tuong_vi_pham', 'nguoi_lap', 'muc_tieu')
        .order_by('-ngay_vi_pham')
    )
    pending_penalty_total = pending_violations.aggregate(total=Sum('so_tien_phat'))['total'] or 0
    approved_violations_count = violations_period.filter(trang_thai='DA_DUYET').count()

    anomaly_codes = ['CANH_BAO_XA', 'MAT_GPS', 'GIAN_LAN']
    patrol_anomalies_qs = GhiNhanTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(
        thoi_gian_quet__date__gte=date_from,
        ket_qua__in=anomaly_codes,
    )
    patrol_anomalies = patrol_anomalies_qs.count()
    skipped_patrols_count = period_patrols.filter(trang_thai='BO_DO').count()
    completed_patrols_count = period_patrols.filter(trang_thai='HOAN_THANH').count()

    upcoming_trainings_qs = (
        BuoiHuanLuyen.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(thoi_gian__gte=now)
        .select_related('nguoi_dao_tao')
        .annotate(so_hoc_vien=Count('danh_sach_tham_gia', distinct=True))
        .order_by('thoi_gian')
    )
    upcoming_trainings_count = upcoming_trainings_qs.count()
    upcoming_trainings = list(upcoming_trainings_qs[:6])
    training_participants_count = (
        BuoiHuanLuyen.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(thoi_gian__date__gte=date_from)
        .aggregate(total=Count('danh_sach_tham_gia', distinct=True))['total'] or 0
    )

    recent_failed_inspections = list(
        DotThanhTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(ket_qua='KHONG_DAT')
        .select_related('can_bo', 'muc_tieu')
        .order_by('-thoi_gian_den')[:6]
    )

    for item in recent_failed_inspections:
        item.dashboard_url = (
            _admin_url_if_permitted(request.user, 'admin:inspection_dotthanhtra_change', 'inspection.view_dotthanhtra', args=[item.pk])
            if can_view_inspection else None
        )

    top_violation_types = list(
        violations_period
        .values('loai_loi')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    violation_label_map = dict(BienBanViPham.LOAI_LOI)
    for item in top_violation_types:
        item['label'] = violation_label_map.get(item['loai_loi'], item['loai_loi'])
    max_violation_type_count = max([item['total'] for item in top_violation_types] or [1])

    top_failed_sites = list(
        failed_inspections_period
        .values('muc_tieu__ten_muc_tieu')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    week_end = start_week + timedelta(days=6)
    completed_patrols_by_day = {
        row['day']: row['total']
        for row in (
            LuotTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
            .filter(
                thoi_gian_bat_dau__date__gte=start_week,
                thoi_gian_bat_dau__date__lte=week_end,
                trang_thai='HOAN_THANH',
            )
            .annotate(day=TruncDate('thoi_gian_bat_dau'))
            .values('day')
            .annotate(total=Count('id'))
        )
    }
    inspections_by_day = {
        row['day']: row['total']
        for row in (
            DotThanhTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
            .filter(thoi_gian_den__date__gte=start_week, thoi_gian_den__date__lte=week_end)
            .annotate(day=TruncDate('thoi_gian_den'))
            .values('day')
            .annotate(total=Count('id'))
        )
    }
    violations_by_day = {
        row['day']: row['total']
        for row in (
            BienBanViPham.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
            .filter(ngay_vi_pham__date__gte=start_week, ngay_vi_pham__date__lte=week_end)
            .annotate(day=TruncDate('ngay_vi_pham'))
            .values('day')
            .annotate(total=Count('id'))
        )
    }

    chart_points = []
    chart_data = []
    chart_labels = []
    for i in range(7):
        day = start_week + timedelta(days=i)
        completed_count = completed_patrols_by_day.get(day, 0)
        inspection_count = inspections_by_day.get(day, 0)
        violation_count = violations_by_day.get(day, 0)
        chart_labels.append(day.strftime('%d/%m'))
        chart_data.append(completed_count)
        chart_points.append({
            'label': day.strftime('%d/%m'),
            'completed_patrols': completed_count,
            'inspections': inspection_count,
            'violations': violation_count,
        })
    max_chart_value = max([p['completed_patrols'] + p['inspections'] + p['violations'] for p in chart_points] or [1]) or 1
    for point in chart_points:
        total_value = point['completed_patrols'] + point['inspections'] + point['violations']
        point['total'] = total_value
        point['percent'] = round((total_value / max_chart_value) * 100) if max_chart_value else 0

    action_items = []
    for item in pending_violations[:5]:
        violation_url = _admin_url_if_permitted(request.user, 'admin:inspection_bienbanvipham_change', 'inspection.change_bienbanvipham', args=[item.pk]) if can_change_violation else None
        if violation_url:
            action_items.append({
                'priority': 'Cao',
                'type': 'Vi phạm chờ duyệt',
                'title': item.ma_bien_ban,
                'subject': item.doi_tuong_vi_pham.ho_ten if item.doi_tuong_vi_pham else 'Chưa rõ nhân viên',
                'site': item.muc_tieu.ten_muc_tieu if item.muc_tieu else 'Chưa gắn mục tiêu',
                'note': item.get_loai_loi_display(),
                'time': item.ngay_vi_pham,
                'url': violation_url,
                'cta': 'Duyệt hồ sơ',
                'tone': 'danger',
            })
    for item in recent_failed_inspections[:5]:
        inspection_url = _admin_url_if_permitted(request.user, 'admin:inspection_dotthanhtra_change', 'inspection.view_dotthanhtra', args=[item.pk]) if can_view_inspection else None
        if inspection_url:
            action_items.append({
                'priority': 'Cao',
                'type': 'Mục tiêu không đạt',
                'title': 'Thanh tra không đạt',
                'subject': item.muc_tieu.ten_muc_tieu if item.muc_tieu else 'Chưa rõ mục tiêu',
                'site': item.muc_tieu.ten_muc_tieu if item.muc_tieu else 'Chưa rõ mục tiêu',
                'note': item.danh_gia_chung or 'Cần kiểm tra checklist, quân số, sổ sách, đồng phục và công cụ hỗ trợ.',
                'time': item.thoi_gian_den,
                'url': inspection_url,
                'cta': 'Xem thanh tra',
                'tone': 'warning',
            })
    action_items = sorted(action_items, key=lambda x: x['time'], reverse=True)[:7]

    pending_violations_for_dashboard = list(pending_violations[:6])
    for item in pending_violations_for_dashboard:
        item.dashboard_url = (
            _admin_url_if_permitted(request.user, 'admin:inspection_bienbanvipham_change', 'inspection.change_bienbanvipham', args=[item.pk])
            if can_change_violation else None
        )
    for item in upcoming_trainings:
        item.dashboard_url = (
            _admin_url_if_permitted(request.user, 'admin:inspection_buoihuanluyen_change', 'inspection.view_buoihuanluyen', args=[item.pk])
            if can_view_training else None
        )

    health_cards = [
        {
            'label': 'Thanh tra kỳ này',
            'value': inspections_period_count,
            'note': f'{period_label}: {failed_inspections_period.count()} không đạt',
            'icon': 'fa-clipboard-check',
            'tone': 'blue',
            'url': inspection_changelist_url,
        },
        {
            'label': 'Chất lượng đạt',
            'value': f'{quality_rate}%',
            'note': f'{passed_inspections_period_count}/{inspections_period_count or 0} đợt đạt yêu cầu',
            'icon': 'fa-medal',
            'tone': 'green',
            'url': inspection_changelist_url,
        },
        {
            'label': 'Vi phạm chờ duyệt',
            'value': pending_violations.count(),
            'note': f'{approved_violations_count} hồ sơ đã duyệt trong kỳ',
            'icon': 'fa-user-shield',
            'tone': 'amber',
            'url': violation_changelist_url,
        },
        {
            'label': 'Phạt dự kiến',
            'value': pending_penalty_total,
            'note': 'Tổng tiền phạt của hồ sơ chờ duyệt',
            'icon': 'fa-coins',
            'tone': 'slate',
            'url': violation_changelist_url,
            'money': True,
        },
        {
            'label': 'Bất thường tuần tra',
            'value': patrol_anomalies + skipped_patrols_count,
            'note': f'{patrol_anomalies} GPS bất thường · {skipped_patrols_count} bỏ dở',
            'icon': 'fa-satellite-dish',
            'tone': 'orange',
            'url': route_changelist_url,
        },
        {
            'label': 'Đào tạo sắp tới',
            'value': upcoming_trainings_count,
            'note': f'{training_participants_count} lượt nhân sự trong kỳ',
            'icon': 'fa-graduation-cap',
            'tone': 'purple',
            'url': training_changelist_url,
        },
    ]
    health_cards = [card for card in health_cards if card.get('url')]
    live_patrols = list(active_patrols[:8])
    urgent_attention_total = pending_violations.count() + failed_inspections_period.count() + patrol_anomalies + skipped_patrols_count
    inspection_failure_rate = max(0, 100 - quality_rate) if inspections_period_count else 0
    focus_metrics = [
        {
            'label': 'Không đạt trong kỳ',
            'value': failed_inspections_period.count(),
            'note': 'Ưu tiên tái kiểm tra hoặc mở kế hoạch khắc phục.',
            'url': inspection_changelist_url,
        },
        {
            'label': 'Hồ sơ chờ duyệt',
            'value': pending_violations.count(),
            'note': 'Chốt bằng chứng và hướng xử lý trước khi quá hạn.',
            'url': violation_changelist_url,
        },
        {
            'label': 'Tuần tra đang diễn ra',
            'value': len(live_patrols),
            'note': 'Theo dõi phiên live để tránh bỏ dở hoặc thiếu mốc quét.',
            'url': route_changelist_url,
        },
        {
            'label': 'Lịch đào tạo sắp tới',
            'value': upcoming_trainings_count,
            'note': 'Giữ đủ giảng viên, học viên và địa điểm trước giờ học.',
            'url': training_changelist_url,
        },
    ]

    context = {
        # Biáº¿n cÅ©, giá»¯ tÆ°Æ¡ng thÃ­ch template vÃ  link Ä‘ang dÃ¹ng.
        'total_routes': total_routes,
        'active_patrols_count': active_patrols.count(),
        'active_patrols_list': active_patrols[:5],
        'chart_labels': chart_labels,
        'chart_data': chart_data,

        # Biáº¿n dashboard má»›i cho Thanh tra & GiÃ¡m sÃ¡t.
        'today': today,
        'period': period,
        'period_label': period_label,
        'dashboard_scope_label': 'Phạm vi tổ chức đã được cấp quyền',
        'dashboard_timeframe_label': f'Ngày {today.strftime("%d/%m/%Y")}',
        'urgent_attention_total': urgent_attention_total,
        'inspection_failure_rate': inspection_failure_rate,
        'date_from': date_from,
        'dang_di': dang_di,
        'hoan_thanh': hoan_thanh,
        'bo_do': bo_do,
        'ty_le': ty_le,
        'live_patrols': live_patrols,
        'live_patrols_count': len(live_patrols),
        'inspections_today_count': inspections_today.count(),
        'failed_inspections_today_count': failed_inspections_today.count(),
        'inspections_month_count': inspections_period_count,
        'failed_inspections_period_count': failed_inspections_period.count(),
        'pending_violations_count': pending_violations.count(),
        'pending_penalty_total': pending_penalty_total,
        'patrol_anomalies_count': patrol_anomalies,
        'skipped_patrols_count': skipped_patrols_count,
        'completed_patrols_count': completed_patrols_count,
        'quality_rate': quality_rate,
        'upcoming_trainings': upcoming_trainings,
        'upcoming_trainings_count': upcoming_trainings_count,
        'training_participants_count': training_participants_count,
        'recent_failed_inspections': recent_failed_inspections,
        'pending_violations': pending_violations_for_dashboard,
        'top_violation_types': top_violation_types,
        'max_violation_type_count': max_violation_type_count,
        'top_failed_sites': top_failed_sites,
        'chart_points': chart_points,
        'max_chart_value': max_chart_value,
        'action_items': action_items,
        'health_cards': health_cards,
        'focus_metrics': [item for item in focus_metrics if item.get('url')],
        'urls': {
            'add_violation': add_violation_url,
            'add_inspection': add_inspection_url,
            'add_training': add_training_url,
            'violations': violation_changelist_url,
            'inspections': inspection_changelist_url,
            'trainings': training_changelist_url,
            'routes': route_changelist_url,
        },
    }
    return render(request, 'inspection/dashboard.html', context)

@login_required
@has_permission_decorator('giao_ca_truc')
@export_audit_log(
    module="inspection",
    model_name="LoaiTuanTra",
    note="Export PDF QR loai tuan tra",
    object_id_resolver=lambda request, loai_id: loai_id,
    changes_resolver=lambda request, loai_id: {"loai_tuan_tra_id": loai_id},
)
def export_qr_pdf(request, loai_id):
    loai = get_object_or_404(LoaiTuanTra, pk=loai_id)
    diems = DiemTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(loai_tuan_tra=loai).order_by('thu_tu')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = _reportlab_bold_font_name()
    
    p.setFont(font_name, 16)
    p.drawCentredString(width/2, height - 2*cm, f"QR CODE: {loai.ten_loai}")
    
    x_start = 2*cm; y_start = height - 5*cm; w_cell = 5*cm; h_cell = 7*cm; cols = 3
    x, y, count = x_start, y_start, 0

    for diem in diems:
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(diem.ma_qr)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG"); img_buffer.seek(0)
        
        p.rect(x, y - h_cell, w_cell, h_cell, stroke=1, fill=0)
        p.drawImage(ImageReader(img_buffer), x + (w_cell-4*cm)/2, y - h_cell + 1.5*cm, width=4*cm, height=4*cm)
        p.setFont(font_name, 10)
        p.drawCentredString(x + w_cell/2, y - h_cell + 1*cm, f"{diem.thu_tu}. {diem.ten_diem}")
        
        count += 1
        if count % cols == 0:
            x = x_start; y -= h_cell + 1*cm
            if y < 2*cm: p.showPage(); y = height - 2*cm
        else: x += w_cell + 1*cm

    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

# ==============================================================================
# LEGACY MOBILE GUARD PATROL COMPATIBILITY WRAPPERS
# ==============================================================================

@login_required
def mobile_tuan_tra_list(request):
    """Legacy compatibility path. Canonical guard patrol route is operations:mobile_tuan_tra_list."""
    return redirect('operations:mobile_tuan_tra_list')

@login_required
@has_permission_decorator('gui_bao_cao_tuan_tra')
def bat_dau_tuan_tra(request, loai_id):
    # Legacy compatibility path. Canonical route: operations:bat_dau_tuan_tra.
    try:
        luot = StartPatrolSessionUseCase.execute(get_nv(request), loai_id)
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect('operations:mobile_tuan_tra_list')
    return redirect('operations:thuc_hien_tuan_tra', luot_id=luot.id)

@login_required
def thuc_hien_tuan_tra(request, luot_id):
    # Legacy compatibility path. Canonical route: operations:thuc_hien_tuan_tra.
    return redirect('operations:thuc_hien_tuan_tra', luot_id=luot_id)

# --- CORE LOGIC: Xá»¬ LÃ QUÃ‰T QR ---
@require_POST
@login_required
@has_permission_decorator('gui_bao_cao_tuan_tra')
def ghi_nhan_diem(request):
    # Legacy AJAX compatibility path. Canonical route: operations:xu_ly_quet_qr.
    luot_id = request.POST.get('luot_id') or request.POST.get('luot_tuan_tra_id')
    ma_qr = request.POST.get('ma_qr') or request.POST.get('qr_code')
    lat_req = request.POST.get('lat')  # Nháº­n GPS tá»« Client
    lng_req = request.POST.get('lng')
    hinh_anh = request.FILES.get('hinh_anh_xac_thuc')

    try:
        # Refactor: Delegated logic to RecordPatrolCheckpointUseCase.
        success, message, data = RecordPatrolCheckpointUseCase.execute(
            nhan_vien=get_nv(request),
            luot_id=luot_id,
            ma_qr=ma_qr,
            lat_req=lat_req,
            lng_req=lng_req,
            hinh_anh_xac_thuc=hinh_anh,
        )
    except (PermissionDenied, ValidationError) as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=403)

    response_data = {'success': success, 'message': message}
    response_data.update(data)
    return JsonResponse(response_data)

@login_required
@has_permission_decorator('gui_bao_cao_tuan_tra')
@require_POST
def hoan_thanh_tuan_tra(request, luot_id):
    # Legacy compatibility path. Canonical route: operations:hoan_thanh_tuan_tra.
    try:
        CompletePatrolSessionUseCase.execute(get_nv(request), luot_id)
        messages.success(request, "ÄÃ£ hoÃ n thÃ nh tuáº§n tra!")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect('operations:mobile_tuan_tra_list')

# --- THANH TRA VIEW ---
@login_required
@has_permission_decorator('lap_bien_ban_vi_pham')
def mobile_lap_bien_ban(request):
    nv = get_nv(request)
    if request.method == "POST":
        form = BienBanViPhamForm(request.POST, request.FILES)
        if form.is_valid():
            success, msg, _ = CreateViolationUseCase.execute(
                reporter_nv=nv,
                form_data=form.cleaned_data,
                files_data=request.FILES
            )
            if success:
                messages.success(request, msg)
                return redirect('operations:mobile_dashboard')
            else:
                messages.error(request, msg)
    else: form = BienBanViPhamForm()
    return render(request, 'inspection/mobile/lap_bien_ban.html', {'form': form})

@login_required
def mobile_dot_thanh_tra(request):
    return render(request, 'inspection/mobile/dot_thanh_tra.html', {})

