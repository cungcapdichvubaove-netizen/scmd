# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/views.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: Views xử lý logic người dùng (Nhân sự).
             UPDATED: Mobile Feature Set (Update Profile, Change Password, Salary Detail).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from datetime import timedelta
from pathlib import Path
from weasyprint import HTML
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import NhanVien, BangCapChungChi
from .forms import UserProfileForm
from operations.models import PhanCongCaTruc
from accounting.models import ChiTietLuong

# ==============================================================================
# 1. DASHBOARD NHÂN SỰ (HR)
# ==============================================================================
@login_required
def dashboard_view(request):
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year

    total_staff = NhanVien.objects.count()
    new_staff = NhanVien.objects.filter(ngay_vao_lam__month=current_month, ngay_vao_lam__year=current_year).count()
    probation_staff = NhanVien.objects.filter(trang_thai_lam_viec='THUVIEC').count()
    
    next_30_days = today + timedelta(days=30)
    expiring_certs = BangCapChungChi.objects.filter(ngay_het_han__range=[today, next_30_days]).select_related('nhan_vien')

    context = {
        "total_staff": total_staff,
        "new_staff": new_staff,
        "probation_staff": probation_staff,
        "expiring_certs": expiring_certs,
    }
    return render(request, "users/dashboard_hr.html", context)

# ==============================================================================
# 2. HỒ SƠ CÁ NHÂN (DESKTOP - ALL IN ONE)
# ==============================================================================
@login_required
def profile_view(request):
    try:
        nhan_vien = request.user.nhan_vien
    except AttributeError:
        messages.warning(request, "Tài khoản chưa được liên kết với hồ sơ nhân viên.")
        return redirect('main:homepage')

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=nhan_vien)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật hồ sơ thành công!")
            return redirect("users:profile")
    else:
        form = UserProfileForm(instance=nhan_vien)
    
    today = timezone.now().date()
    attendance_logs = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien,
        ngay_truc__lte=today
    ).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong').order_by('-ngay_truc')[:30]

    salary_logs = ChiTietLuong.objects.filter(
        nhan_vien=nhan_vien
    ).select_related('bang_luong').order_by('-bang_luong__nam', '-bang_luong__thang')[:6]

    context = {
        "form": form,
        "nhan_vien": nhan_vien,
        "attendance_logs": attendance_logs,
        "salary_logs": salary_logs,
    }
    return render(request, "users/profile.html", context)

# ==============================================================================
# 3. MOBILE FEATURES (NÂNG CẤP)
# ==============================================================================

@login_required
def mobile_profile_view(request):
    """
    Mobile Profile: Xem & Cập nhật thông tin, Chấm công, Lương
    """
    try:
        nhan_vien = request.user.nhan_vien
    except AttributeError:
        messages.warning(request, "Tài khoản chưa liên kết hồ sơ nhân viên.")
        return redirect('operations:mobile_dashboard')

    # Xử lý Cập nhật thông tin (POST)
    if request.method == "POST" and 'update_profile' in request.POST:
        form = UserProfileForm(request.POST, request.FILES, instance=nhan_vien)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật thông tin thành công!")
            return redirect('users:mobile_profile')
        else:
            messages.error(request, "Lỗi cập nhật. Vui lòng kiểm tra lại.")
    else:
        form = UserProfileForm(instance=nhan_vien)

    today = timezone.now().date()
    ca_truc_thang = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien, 
        ngay_truc__month=today.month, 
        ngay_truc__year=today.year
    ).count()

    attendance_logs = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien, ngay_truc__lte=today
    ).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong').order_by('-ngay_truc')[:30]

    salary_logs = ChiTietLuong.objects.filter(
        nhan_vien=nhan_vien
    ).select_related('bang_luong').order_by('-bang_luong__nam', '-bang_luong__thang')[:6]

    context = {
        'nhan_vien': nhan_vien,
        'form': form,
        'ca_truc_thang': ca_truc_thang,
        'attendance_logs': attendance_logs,
        'salary_logs': salary_logs,
        'now': timezone.now()
    }
    return render(request, "users/mobile/profile.html", context)

@login_required
def mobile_password_change_view(request):
    """
    View đổi mật khẩu dành riêng cho Mobile
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Giữ đăng nhập
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('users:mobile_profile')
        else:
            messages.error(request, 'Mật khẩu không khớp hoặc quá yếu.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/mobile/password_change.html', {'form': form})

@login_required
def mobile_salary_detail_view(request, luong_id):
    """
    View xem chi tiết phiếu lương Mobile
    """
    salary = get_object_or_404(ChiTietLuong, id=luong_id, nhan_vien__user=request.user)
    return render(request, 'users/mobile/salary_detail.html', {'salary': salary})

# ==============================================================================
# 4. EXPORT PDF
# ==============================================================================
@login_required
def export_ly_lich_options_view(request, nhan_vien_id):
    nhan_vien = get_object_or_404(NhanVien, pk=nhan_vien_id)
    return render(request, "users/ly_lich_options.html", {"nhan_vien": nhan_vien})

@login_required
@permission_required('users.view_nhanvien', raise_exception=True)
def export_ly_lich_pdf(request, nhan_vien_id):
    nhan_vien = get_object_or_404(NhanVien, pk=nhan_vien_id)
    options = {
        "bao_gom_anh_the": request.POST.get("bao_gom_anh_the") == "on",
        "bao_gom_thong_tin_ca_nhan": request.POST.get("bao_gom_thong_tin_ca_nhan") == "on",
        "bao_gom_bang_cap": request.POST.get("bao_gom_bang_cap") == "on",
        "bao_gom_lich_su_cong_tac": request.POST.get("bao_gom_lich_su_cong_tac") == "on",
    }
    avatar_uri = ""
    if options["bao_gom_anh_the"] and nhan_vien.anh_the:
        try:
            avatar_path = Path(nhan_vien.anh_the.path)
            if avatar_path.exists(): avatar_uri = avatar_path.as_uri()
        except: pass
    
    html_string = render_to_string("users/ly_lich_pdf.html", {
        "nhan_vien": nhan_vien, 
        "options": options, 
        "avatar_uri": avatar_uri
    })
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="ly_lich_{nhan_vien.ma_nhan_vien}.pdf"'
    return response