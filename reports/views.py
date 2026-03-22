# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: reports/views.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Logic xử lý Báo cáo & Thống kê.
             UPDATED: Full logic cho Cá nhân, Mục tiêu, Sự cố.
             NEW FEATURE: Tích hợp Export PDF & Excel chuyên nghiệp.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import HttpResponse, FileResponse # [NEW] Import FileResponse
import csv
import calendar
from datetime import datetime, timedelta

from users.models import NhanVien
from operations.models import ChamCong, BaoCaoSuCo, PhanCongCaTruc
from clients.models import MucTieu
from .services import ReportService # [NEW] Import Service

@login_required
def report_dashboard(request):
    """Trang chủ Dashboard Báo cáo"""
    return render(request, "reports/dashboard.html")

# ==============================================================================
# 1. BÁO CÁO TỔNG HỢP (MA TRẬN) - GIỮ NGUYÊN
# ==============================================================================
@login_required
def tong_hop_cham_cong_thang_view(request):
    thang = int(request.GET.get('thang', timezone.now().month))
    nam = int(request.GET.get('nam', timezone.now().year))
    
    # Logic lấy ngày trong tháng
    _, num_days = calendar.monthrange(nam, thang)
    days_in_month = range(1, num_days + 1)
    
    nhan_vien_list = NhanVien.objects.filter(trang_thai_lam_viec='dang_lam_viec')
    report_data = []

    # Tối ưu query (đoạn này giữ nguyên logic của bạn, sau này có thể tối ưu thêm)
    for nv in nhan_vien_list:
        row = {'nhan_vien': nv, 'days': {}}
        total_cong = 0
        
        # Query chấm công của NV trong tháng
        cham_cong_qs = ChamCong.objects.filter(
            ca_truc__nhan_vien=nv,
            ca_truc__ngay_truc__month=thang,
            ca_truc__ngay_truc__year=nam
        ).select_related('ca_truc')
        
        # Map vào dict để tra cứu nhanh
        cc_map = {cc.ca_truc.ngay_truc.day: cc for cc in cham_cong_qs}

        for day in days_in_month:
            cc = cc_map.get(day)
            if cc:
                status = "X" # Mặc định có đi làm
                if cc.thoi_gian_check_in and cc.thoi_gian_check_out:
                    total_cong += 1 # Giả sử tính theo ca
                elif not cc.thoi_gian_check_out:
                    status = "NoOut"
                
                row['days'][day] = status
            else:
                row['days'][day] = ""
        
        row['total_cong'] = total_cong
        report_data.append(row)

    return render(request, "reports/tong_hop_cham_cong.html", {
        'report_data': report_data, 'days_in_month': days_in_month,
        'selected_thang': thang, 'selected_nam': nam, 'thang_range': range(1, 13)
    })

# ==============================================================================
# 2. BÁO CÁO CÁ NHÂN - GIỮ NGUYÊN
# ==============================================================================
@login_required
def bang_cham_cong_ca_nhan_view(request):
    thang = int(request.GET.get('thang', timezone.now().month))
    nam = int(request.GET.get('nam', timezone.now().year))
    nhan_vien_id = request.GET.get('nhan_vien_id')
    
    report_data = None
    selected_nv = None
    
    if nhan_vien_id:
        selected_nv = NhanVien.objects.get(id=nhan_vien_id)
        report_data = ChamCong.objects.filter(
            ca_truc__nhan_vien_id=nhan_vien_id,
            ca_truc__ngay_truc__month=thang,
            ca_truc__ngay_truc__year=nam
        ).order_by('ca_truc__ngay_truc')

    return render(request, "reports/cham_cong_ca_nhan.html", {
        'nhan_vien_list': NhanVien.objects.all(), 'selected_nv': selected_nv,
        'report_data': report_data, 'thang_range': range(1, 13), 'selected_thang': thang, 'selected_nam': nam
    })

# ==============================================================================
# 3. BÁO CÁO MỤC TIÊU - GIỮ NGUYÊN
# ==============================================================================
@login_required
def bang_cham_cong_muc_tieu_view(request):
    thang = int(request.GET.get('thang', timezone.now().month))
    nam = int(request.GET.get('nam', timezone.now().year))
    muc_tieu_id = request.GET.get('muc_tieu_id')
    
    report_data = None
    if muc_tieu_id:
        report_data = ChamCong.objects.filter(
            ca_truc__vi_tri_chot__muc_tieu_id=muc_tieu_id,
            ca_truc__ngay_truc__month=thang,
            ca_truc__ngay_truc__year=nam
        ).order_by('ca_truc__ngay_truc', 'ca_truc__nhan_vien__ho_ten')

    return render(request, "reports/cham_cong_muc_tieu.html", {
        'muc_tieu_list': MucTieu.objects.all(), 'selected_muc_tieu': MucTieu.objects.filter(id=muc_tieu_id).first() if muc_tieu_id else None,
        'report_data': report_data, 'thang_range': range(1, 13), 'selected_thang': thang, 'selected_nam': nam
    })

# ==============================================================================
# 4. BÁO CÁO SỰ CỐ - GIỮ NGUYÊN
# ==============================================================================
@login_required
def bao_cao_su_co_view(request):
    thang = int(request.GET.get('thang', timezone.now().month))
    nam = int(request.GET.get('nam', timezone.now().year))
    data = BaoCaoSuCo.objects.filter(created_at__month=thang, created_at__year=nam).select_related('muc_tieu', 'nhan_vien_bao_cao').order_by('-created_at')
    
    # Logic xuất CSV cũ của bạn
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="SuCo_T{thang}_{nam}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Thời gian', 'Tiêu đề', 'Mục tiêu', 'Mức độ', 'Trạng thái'])
        for sc in data:
            writer.writerow([
                sc.created_at.strftime('%d/%m/%Y %H:%M'),
                sc.tieu_de,
                sc.muc_tieu.ten_muc_tieu if sc.muc_tieu else "",
                sc.get_muc_do_display(),
                sc.get_trang_thai_display()
            ])
        return response

    return render(request, "reports/bao_cao_su_co.html", {
        'data': data, 'thang_range': range(1, 13), 'selected_thang': thang, 'selected_nam': nam
    })

# ==============================================================================
# 5. [NEW] CÁC HÀM EXPORT NÂNG CAO (PDF / EXCEL)
# ==============================================================================

@login_required
def export_incident_pdf(request, pk):
    """
    Xuất biên bản sự cố ra PDF (Chức năng mới)
    """
    pdf_buffer, filename = ReportService.generate_incident_pdf(pk, request)
    
    if not pdf_buffer:
        return HttpResponse("Không tìm thấy sự cố hoặc lỗi tạo PDF", status=404)
        
    response = FileResponse(pdf_buffer, as_attachment=True, filename=filename)
    return response

@login_required
def export_attendance_excel(request):
    """
    Xuất bảng công tháng ra Excel chuyên nghiệp (Chức năng mới)
    """
    try:
        month = int(request.GET.get('month', timezone.now().month))
        year = int(request.GET.get('year', timezone.now().year))
        muc_tieu_id = request.GET.get('muc_tieu')
        
        if muc_tieu_id == 'all' or not muc_tieu_id:
            muc_tieu_id = None
        else:
            muc_tieu_id = int(muc_tieu_id)
            
        excel_buffer, filename = ReportService.generate_attendance_excel(month, year, muc_tieu_id)
        
        response = FileResponse(
            excel_buffer, 
            as_attachment=True, 
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response
        
    except ValueError:
        return HttpResponse("Tham số không hợp lệ", status=400)