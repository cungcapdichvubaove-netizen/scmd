# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: accounting/views.py
Author: Mr. Anh
Created Date: 2025-12-04
Updated Date: 2026-04-28
Version: v1.1.0
Description: Views xử lý logic Kế toán & Lương.
             UPDATED: Bổ sung Data cho Dashboard KTT (KPIs, Charts).
"""

from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from datetime import timedelta
import json
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font

from .models import BangLuongThang, ChiTietLuong
from .models_soquy import SoQuy
from inventory.models import PhieuXuat
from .services.payroll import PayrollService
from accounting.application.reports_use_cases import DeductionAuditUseCase
from django.conf import settings
from rolepermissions.checkers import has_role
from main.models import AuditLog

EXPORT_ALLOWED_ROLES = ['ban_giam_doc', 'ke_toan']


def _enforce_export_access(request):
    if request.user.is_superuser or has_role(request.user, EXPORT_ALLOWED_ROLES):
        return
    raise PermissionDenied("Ban khong co quyen xuat du lieu luong nhay cam.")


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _log_export(request, model_name, note, changes=None, object_id=None):
    AuditLog.objects.create(
        user=request.user,
        tenant_id=getattr(settings, 'SCMD_ORGANIZATION_ID', None),
        action=AuditLog.Action.EXECUTE,
        module='accounting',
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        changes=changes or {},
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        note=note,
        status='SUCCESS'
    )

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
    bang_luongs = (
        BangLuongThang.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .order_by('-nam', '-thang')[:12]
    )

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
        try:
            with transaction.atomic():
                bl.trang_thai = 'DA_PHAT_HANH'
                bl.save()

                success, msg = PayrollService.lock_related_records(bl)
                messages.success(request, f"Đã phát hành bảng lương tháng {bl.thang}/{bl.nam}. {msg}")
        except Exception as e:
            messages.error(request, f"Lỗi khi chốt lương: {str(e)}")
            
    return redirect('accounting:dashboard')

@login_required
def bao_cao_doi_soat_khau_tru(request, pk):
    """View hiển thị báo cáo đối soát khấu trừ lương vs Sổ quỹ"""
    tenant_id = getattr(settings, 'SCMD_ORGANIZATION_ID', None)
    report_data = DeductionAuditUseCase.execute(pk, tenant_id)
    
    return render(request, 'accounting/reports/deduction_audit.html', {'report': report_data})

@login_required
def export_doi_soat_khau_tru_excel(request, pk):
    """Xuất file Excel báo cáo đối soát khấu trừ lương"""
    _enforce_export_access(request)
    tenant_id = getattr(settings, 'SCMD_ORGANIZATION_ID', None)
    report = DeductionAuditUseCase.execute(pk, tenant_id)
    
    if report['status'] == 'error':
        messages.error(request, f"Lỗi xuất file: {report['message']}")
        return redirect('accounting:doi_soat_khau_tru', pk=pk)

    # Khởi tạo Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Doi Soat Khau Tru"

    # Định dạng header
    headers = ['STT', 'Nhân viên', 'Mã NV', 'Khấu trừ Lương (A)', 'Thực chi Sổ quỹ (B)', 'Chênh lệch (A-B)']
    ws.append([f"BÁO CÁO ĐỐI SOÁT: {report['bang_luong']}"])
    ws.append([f"Kỳ lương: {report['ky_luong']}"])
    ws.append([]) # Dòng trống
    ws.append(headers)

    # Định dạng cảnh báo cho sai lệch (Màu đỏ)
    warning_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    warning_font = Font(color='9C0006', bold=True)

    # Định dạng Accounting (VND) cho Excel
    currency_format = '#,##0" ₫"'
    # Tối ưu độ rộng các cột để hiển thị số tiền không bị che khuất
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 20

    # Thêm dữ liệu
    for i, item in enumerate(report['data'], 1):
        ws.append([
            i,
            item['nhan_vien'],
            item['ma_nv'],
            item['khau_tru_luong'],
            item['thuc_chi_so_quy'],
            item['chenh_lech']
        ])
        # Áp dụng định dạng tiền tệ cho các cột D, E, F (tương ứng index 4, 5, 6)
        for col_num in range(4, 7):
            ws.cell(row=ws.max_row, column=col_num).number_format = currency_format

        # Cảnh báo chênh lệch khác 0 (Cột F - Index 6)
        if item['chenh_lech'] != 0:
            cell = ws.cell(row=ws.max_row, column=6)
            cell.fill = warning_fill
            cell.font = warning_font

    # Thêm dòng tổng kết
    ws.append([])
    ws.append(['', '', 'TỔNG BIẾN ĐỘNG:', '', '', report['summary']['total_variance']])
    # Định dạng cho ô tổng chênh lệch ở cột F
    total_variance_cell = ws.cell(row=ws.max_row, column=6)
    total_variance_cell.number_format = currency_format
    
    # Nếu tổng biến động khác 0, cũng tô màu cảnh báo
    if report['summary']['total_variance'] != 0:
        total_variance_cell.fill = warning_fill
        total_variance_cell.font = warning_font
        total_variance_cell.font = Font(color='9C0006', bold=True, size=12) # Nhấn mạnh thêm cho dòng tổng

    # --- BẢO VỆ DỮ LIỆU (SECURITY BY DESIGN) ---
    # Khóa Sheet và đặt mật khẩu để đảm bảo tính toàn vẹn, ngăn chặn chỉnh sửa trái phép
    ws.protection.sheet = True
    ws.protection.set_password(settings.EXCEL_EXPORT_PASSWORD)

    # Thiết lập Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    filename = f"Doi_soat_luong_{report['ky_luong'].replace('/', '_')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    _log_export(
        request,
        'BangLuongThang',
        'Export Excel doi soat khau tru',
        changes={'bang_luong_id': pk, 'ky_luong': report.get('ky_luong')},
        object_id=pk,
    )
    return response

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
