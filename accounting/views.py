# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/views.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Views xử lý logic Kế toán & Lương.
             UPDATED: Bổ sung Data cho Dashboard KTT (KPIs, Charts).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
import json

from .models import BangLuongThang, ChiTietLuong
from .models_soquy import SoQuy
from .services.payroll import PayrollService

# --- WEB ADMIN VIEWS (KTT/KTV) ---

@login_required
def dashboard_accounting(request):
    """
    Dashboard Kế toán trưởng - The Financial Cockpit
    """
    today = timezone.now()
    first_day_month = today.replace(day=1)
    
    # 1. KPIs Tháng này
    tong_thu = SoQuy.objects.filter(
        loai_phieu='THU', ngay_lap__gte=first_day_month, trang_thai='DA_DUYET'
    ).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    
    tong_chi = SoQuy.objects.filter(
        loai_phieu='CHI', ngay_lap__gte=first_day_month, trang_thai='DA_DUYET'
    ).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    
    so_du_tam_tinh = tong_thu - tong_chi

    # 2. Pending Approvals (Cần duyệt ngay)
    phieu_cho_duyet = SoQuy.objects.filter(trang_thai='CHO_DUYET').count()
    luong_cho_phat_hanh = BangLuongThang.objects.filter(trang_thai='CHO_DUYET').count()

    # 3. Chart Data (6 tháng gần nhất) - Dòng tiền
    chart_labels = []
    data_thu = []
    data_chi = []
    
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=i*30)
        month = month_date.month
        year = month_date.year
        chart_labels.append(f"T{month}")
        
        thu = SoQuy.objects.filter(loai_phieu='THU', trang_thai='DA_DUYET', ngay_lap__month=month, ngay_lap__year=year).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        chi = SoQuy.objects.filter(loai_phieu='CHI', trang_thai='DA_DUYET', ngay_lap__month=month, ngay_lap__year=year).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        
        data_thu.append(float(thu))
        data_chi.append(float(chi))

    # 4. Danh sách Bảng lương
    bang_luongs = BangLuongThang.objects.all().order_by('-nam', '-thang')[:12]

    context = {
        'kpi_thu': tong_thu,
        'kpi_chi': tong_chi,
        'kpi_so_du': so_du_tam_tinh,
        'pending_phieu': phieu_cho_duyet,
        'pending_luong': luong_cho_phat_hanh,
        'chart_labels': json.dumps(chart_labels),
        'data_thu': json.dumps(data_thu),
        'data_chi': json.dumps(data_chi),
        'bang_luongs': bang_luongs,
        'today': today
    }
    return render(request, 'accounting/dashboard.html', context)

@login_required
def tinh_luong_view(request):
    if request.method == "POST":
        try:
            thang = int(request.POST.get('thang'))
            nam = int(request.POST.get('nam'))
            success, msg = PayrollService.tinh_luong_thang(thang, nam)
            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('accounting:dashboard')

@login_required
def chi_tiet_bang_luong(request, pk):
    bl = get_object_or_404(BangLuongThang, pk=pk)
    chi_tiet = ChiTietLuong.objects.filter(bang_luong=bl).select_related('nhan_vien')
    return render(request, 'accounting/bang_luong_detail.html', {'bang_luong': bl, 'chi_tiet': chi_tiet})

@login_required
def chot_luong_view(request, pk):
    bl = get_object_or_404(BangLuongThang, pk=pk)
    if bl.trang_thai != 'DA_PHAT_HANH':
        bl.trang_thai = 'DA_PHAT_HANH'
        bl.save()
        messages.success(request, f"Đã phát hành bảng lương tháng {bl.thang}/{bl.nam}")
    return redirect('accounting:dashboard')

# --- MOBILE VIEWS (CHO BẢO VỆ) ---

@login_required
def mobile_phieu_luong_list(request):
    try: nv = request.user.nhan_vien
    except: return redirect('operations:mobile_dashboard')
    
    phieu_luongs = ChiTietLuong.objects.filter(
        nhan_vien=nv, 
        bang_luong__trang_thai='DA_PHAT_HANH'
    ).select_related('bang_luong').order_by('-bang_luong__nam', '-bang_luong__thang')
    
    return render(request, 'accounting/mobile/phieu_luong_list.html', {'phieu_luongs': phieu_luongs})

@login_required
def mobile_phieu_luong_detail(request, pk):
    phieu = get_object_or_404(ChiTietLuong, pk=pk, nhan_vien=request.user.nhan_vien)
    return render(request, 'accounting/mobile/phieu_luong_detail.html', {'p': phieu})