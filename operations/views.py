# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/views.py
Author: Mr. Anh
Created Date: 2025-12-09
Description: Views xử lý logic Vận hành.
             UPDATED: dashboard_vanhanh_view chuyển sang render Skeleton (tối ưu hiệu năng).
             PRESERVED: Giữ nguyên toàn bộ logic Mobile Views và Xếp lịch từ file gốc.
"""

import os
import json
from datetime import datetime, timedelta, date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.cache import cache_control
from django.contrib import messages

from .models import PhanCongCaTruc, BaoCaoSuCo, ChamCong, KiemTraQuanSo, ViTriChot, CaLamViec, BaoCaoDeXuat
from users.models import NhanVien
from clients.models import MucTieu
from .forms import BaoCaoSuCoForm, BaoCaoDeXuatForm
from .services.attendance_service import AttendanceService

# --- HELPER ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for: return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_mobile_context(request):
    try: return request.user.nhan_vien
    except: return None

@login_required
def dashboard_vanhanh_view(request):
    """
    [OPTIMIZED] Render khung Dashboard "War Room".
    Dữ liệu sẽ được fetch async từ API /api/dashboard/data/
    """
    return render(request, "operations/dashboard_vanhanh.html")

# --- MOBILE VIEWS (Giữ nguyên logic gốc) ---
@login_required
def mobile_dashboard(request):
    nhan_vien = get_mobile_context(request)
    if not nhan_vien: return render(request, "operations/mobile/error_no_profile.html")
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    phan_congs = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, ngay_truc__range=[yesterday, today]).select_related('vi_tri_chot__muc_tieu', 'ca_lam_viec').order_by('ngay_truc', 'ca_lam_viec__gio_bat_dau')
    ca_truc_hom_nay = None
    trang_thai_checkin = False 

    # Logic tìm ca trực ưu tiên
    for pc in phan_congs:
        if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_in and not pc.chamcong.thoi_gian_check_out:
            ca_truc_hom_nay = pc; trang_thai_checkin = True; break
            
    if not ca_truc_hom_nay:
        current_dt = timezone.now()
        for pc in phan_congs:
            if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_out: continue 
            
            start_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_bat_dau))
            if pc.ca_lam_viec.is_night_shift:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc + timedelta(days=1), pc.ca_lam_viec.gio_ket_thuc))
            else:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_ket_thuc))
            
            if end_real > current_dt and start_real - timedelta(minutes=60) <= current_dt:
                ca_truc_hom_nay = pc; trang_thai_checkin = False; break
        
        if not ca_truc_hom_nay:
             ca_truc_hom_nay = phan_congs.filter(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=True).first()

    if not ca_truc_hom_nay:
        last_pc = phan_congs.last()
        if last_pc and hasattr(last_pc, 'chamcong') and last_pc.chamcong.thoi_gian_check_out:
             ca_truc_hom_nay = last_pc; trang_thai_checkin = "DONE" 

    alive_check_pending = None
    if ca_truc_hom_nay:
        alive_check_pending = KiemTraQuanSo.objects.filter(ca_truc=ca_truc_hom_nay, trang_thai='PENDING').first()

    local_now = timezone.localtime(timezone.now())
    greeting = "Chào buổi sáng" if 5 <= local_now.hour < 11 else "Chào buổi trưa" if 11 <= local_now.hour < 13 else "Chào buổi chiều" if 13 <= local_now.hour < 18 else "Chào buổi tối"

    return render(request, 'operations/mobile/dashboard.html', {
        'nhan_vien': nhan_vien,
        'ca_truc_hom_nay': ca_truc_hom_nay,
        'greeting': greeting,
        'trang_thai_checkin': trang_thai_checkin,
        'alive_check_pending': alive_check_pending,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    })

@login_required
def check_in_view(request, phan_cong_id):
    if request.method == 'POST':
        try:
            pc = PhanCongCaTruc.objects.get(id=phan_cong_id, nhan_vien=request.user.nhan_vien)
            note = request.POST.get('note', '')
            
            success, msg, _ = AttendanceService.process_check_in(
                phan_cong=pc,
                lat=request.POST.get('lat'),
                lng=request.POST.get('lng'),
                image=request.FILES.get('anh_check_in'),
                ip=get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', '')
            )
            
            if success and note and hasattr(pc, 'chamcong'):
                cc = pc.chamcong; cc.ghi_chu = (cc.ghi_chu or "") + " " + note; cc.save()
                
            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except PhanCongCaTruc.DoesNotExist: messages.error(request, "Ca trực không tồn tại.")
        except Exception as e: messages.error(request, f"Lỗi hệ thống: {str(e)}")
    return redirect('operations:mobile_dashboard')

@login_required
def check_out_view(request, phan_cong_id):
    if request.method == 'POST':
        try:
            pc = PhanCongCaTruc.objects.get(id=phan_cong_id, nhan_vien=request.user.nhan_vien)
            note = request.POST.get('note', '')

            success, msg, _ = AttendanceService.process_check_out(
                phan_cong=pc,
                lat=request.POST.get('lat'),
                lng=request.POST.get('lng'),
                image=request.FILES.get('anh_check_out'),
                ip=get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', '')
            )
            
            if success and note and hasattr(pc, 'chamcong'):
                cc = pc.chamcong; cc.ghi_chu = (cc.ghi_chu or "") + " " + note; cc.save()

            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except Exception as e: messages.error(request, f"Lỗi: {str(e)}")
    return redirect('operations:mobile_dashboard')

@login_required
def trigger_sos(request):
    if request.method == "POST":
        nhan_vien = get_mobile_context(request)
        if nhan_vien:
            lat, lng = request.POST.get('lat', ''), request.POST.get('lng', '')
            ca_truc = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=True).last()
            muc_tieu = ca_truc.vi_tri_chot.muc_tieu if ca_truc else None
            BaoCaoSuCo.objects.create(tieu_de=f"🆘 CẤP CỨU: {nhan_vien.ho_ten.upper()}", nhan_vien_bao_cao=nhan_vien, muc_do='NGUY_HIEM', trang_thai='CHO_XU_LY', thoi_gian_phat_hien=timezone.now(), muc_tieu=muc_tieu, ca_truc=ca_truc, mo_ta_chi_tiet=f"SOS từ Mobile. GPS: {lat}, {lng}")
            messages.warning(request, "ĐÃ GỬI TÍN HIỆU KHẨN CẤP!")
    return redirect('operations:mobile_dashboard')

@login_required
def mobile_cham_cong_view(request):
    if request.method == 'POST':
        try:
            nhan_vien = request.user.nhan_vien
            action = request.POST.get('action') 
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            note = request.POST.get('note', '')
            today = timezone.now().date(); yesterday = today - timedelta(days=1)
            phan_congs = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, ngay_truc__range=[yesterday, today]).order_by('ngay_truc', 'ca_lam_viec__gio_bat_dau')
            
            target_pc = None
            if action in ['OUT', 'check_out']:
                for pc in phan_congs:
                    if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_in and not pc.chamcong.thoi_gian_check_out: target_pc = pc; break
            else:
                for pc in phan_congs:
                    if not hasattr(pc, 'chamcong') or not pc.chamcong.thoi_gian_check_in: target_pc = pc; break
            
            if not target_pc: messages.error(request, "Không tìm thấy ca trực!"); return redirect('operations:mobile_dashboard')

            if action in ['IN', 'check_in']: success, msg, _ = AttendanceService.process_check_in(target_pc, lat, lng, request.FILES.get('anh_check_in'), get_client_ip(request), request.META.get('HTTP_USER_AGENT', ''))
            else: success, msg, _ = AttendanceService.process_check_out(target_pc, lat, lng, request.FILES.get('anh_check_out'), get_client_ip(request), request.META.get('HTTP_USER_AGENT', ''))
            
            if note and hasattr(target_pc, 'chamcong'): cc = target_pc.chamcong; cc.ghi_chu = (cc.ghi_chu or "") + " " + note; cc.save()
            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except Exception as e: messages.error(request, f"Lỗi: {str(e)}")
    return redirect('operations:mobile_dashboard')

@login_required
def mobile_lich_truc_view(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    today = timezone.now().date()
    return render(request, 'operations/mobile/lich_truc.html', {'danh_sach_ca_truc': PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, ngay_truc__gte=today, ngay_truc__lte=today+timedelta(days=7)).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu').order_by('ngay_truc')})

@login_required
def bao_cao_su_co_mobile_view(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    ca_truc = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=True).last()
    if request.method == "POST":
        form = BaoCaoSuCoForm(request.POST, request.FILES)
        if form.is_valid():
            bc = form.save(commit=False); bc.nhan_vien_bao_cao = nhan_vien
            if ca_truc: bc.muc_tieu = ca_truc.vi_tri_chot.muc_tieu
            bc.save(); messages.success(request, "Đã gửi báo cáo!"); return redirect("operations:mobile_dashboard")
    return render(request, "operations/mobile/bao_cao_su_co.html", {"form": BaoCaoSuCoForm(), "ca_truc": ca_truc})

@login_required
def xac_nhan_alive_check(request, check_id):
    if request.method == "POST":
        alive = get_object_or_404(KiemTraQuanSo, id=check_id)
        if alive.ca_truc.nhan_vien.user == request.user and request.FILES.get('anh_xac_thuc'):
            alive.anh_xac_thuc = request.FILES.get('anh_xac_thuc'); alive.thoi_gian_phan_hoi = timezone.now(); alive.trang_thai = 'OK'; alive.save()
            messages.success(request, "Đã điểm danh!"); 
    return redirect('operations:mobile_dashboard')

@login_required
def mobile_lich_su_cham_cong(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    today = timezone.now().date(); start_month = today.replace(day=1)
    lich_su = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien, ngay_truc__gte=start_month, ngay_truc__lte=today).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong').order_by('-ngay_truc')
    return render(request, 'operations/mobile/lich_su_cham_cong.html', {'lich_su': lich_su, 'tong_cong': lich_su.filter(chamcong__thoi_gian_check_out__isnull=False).count(), 'thang': today.month})

@login_required
def mobile_de_xuat_list(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    return render(request, 'operations/mobile/de_xuat_list.html', {'ds_de_xuat': BaoCaoDeXuat.objects.filter(nhan_vien=nhan_vien).order_by('-ngay_gui')})

@login_required
def mobile_de_xuat_create(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    if request.method == "POST":
        form = BaoCaoDeXuatForm(request.POST, request.FILES)
        if form.is_valid():
            dx = form.save(commit=False); dx.nhan_vien = nhan_vien
            dx.save(); messages.success(request, "Đã gửi đề xuất!"); return redirect('operations:mobile_de_xuat_list')
    return render(request, "operations/mobile/de_xuat_form.html", {"form": BaoCaoDeXuatForm()})

@login_required
def mobile_de_xuat_detail(request, pk):
    return render(request, "operations/mobile/de_xuat_detail.html", {"de_xuat": get_object_or_404(BaoCaoDeXuat, pk=pk, nhan_vien=request.user.nhan_vien)})

@login_required
def danh_sach_muc_tieu(request):
    return render(request, "operations/danh_sach_muc_tieu.html", {'muc_tieus': MucTieu.objects.select_related('quan_ly_muc_tieu').annotate(so_vi_tri=Count('vi_tri_chot'))})

@login_required
def chi_tiet_muc_tieu(request, pk):
    muc_tieu = get_object_or_404(MucTieu, pk=pk)
    return render(request, "operations/chi_tiet_muc_tieu.html", {'muc_tieu': muc_tieu, 'vi_tris': ViTriChot.objects.filter(muc_tieu=muc_tieu), 'nhan_viens': NhanVien.objects.filter(phancongcatruc__vi_tri_chot__muc_tieu=muc_tieu, phancongcatruc__ngay_truc=timezone.now().date()).distinct()})

@login_required
def xep_lich_view(request):
    date_str = request.GET.get('date')
    start_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    start_of_week = start_date - timedelta(days=start_date.weekday())
    days_of_week = [start_of_week + timedelta(days=i) for i in range(7)]
    muc_tieu_id = request.GET.get('muc_tieu')
    vi_tris = ViTriChot.objects.filter(muc_tieu_id=muc_tieu_id) if muc_tieu_id else ViTriChot.objects.all()[:10]
    phan_congs = PhanCongCaTruc.objects.filter(vi_tri_chot__in=vi_tris, ngay_truc__range=[start_of_week, days_of_week[-1]]).select_related('nhan_vien', 'ca_lam_viec')
    schedule_map = {vt: {day: [] for day in days_of_week} for vt in vi_tris}
    for pc in phan_congs:
        if pc.vi_tri_chot in schedule_map: schedule_map[pc.vi_tri_chot][pc.ngay_truc].append(pc)
    return render(request, "operations/xep_lich.html", {'days_of_week': days_of_week, 'vi_tris': vi_tris, 'schedule_map': schedule_map, 'muc_tieus': MucTieu.objects.all(), 'ca_lam_viecs': CaLamViec.objects.all(), 'nhan_viens': NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC'), 'prev_week': (start_of_week - timedelta(days=7)).strftime('%Y-%m-%d'), 'next_week': (start_of_week + timedelta(days=7)).strftime('%Y-%m-%d'), 'today': timezone.now().date()})

@login_required
def them_ca_form_view(request, vi_tri_id, ca_id, ngay):
    return render(request, "operations/partials/them_ca_form.html", {"vi_tri": get_object_or_404(ViTriChot, id=vi_tri_id), "ca": get_object_or_404(CaLamViec, id=ca_id), "ngay_truc": datetime.strptime(ngay, '%Y-%m-%d').date(), "nhan_vien_list": NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC')})

@login_required
def luu_ca_view(request):
    if request.method == "POST":
        if request.POST.get("delete_old"): PhanCongCaTruc.objects.filter(id=request.POST.get("delete_old")).delete()
        if request.POST.get("nhan_vien_id"): PhanCongCaTruc.objects.create(nhan_vien_id=request.POST.get("nhan_vien_id"), vi_tri_chot_id=request.POST.get("vi_tri_id"), ca_lam_viec_id=request.POST.get("ca_id"), ngay_truc=request.POST.get("ngay_truc"))
        return render(request, "operations/partials/ca_truc_cell.html", {"phan_congs": PhanCongCaTruc.objects.filter(vi_tri_chot_id=request.POST.get("vi_tri_id"), ca_lam_viec_id=request.POST.get("ca_id"), ngay_truc=request.POST.get("ngay_truc")), "vi_tri": get_object_or_404(ViTriChot, id=request.POST.get("vi_tri_id")), "ca": get_object_or_404(CaLamViec, id=request.POST.get("ca_id")), "day": datetime.strptime(request.POST.get("ngay_truc"), '%Y-%m-%d').date()})
    return redirect('operations:xep_lich')

@login_required
def sua_ca_form_view(request, phan_cong_id):
    return render(request, "operations/partials/sua_ca_form.html", {"phan_cong": get_object_or_404(PhanCongCaTruc, id=phan_cong_id), "nhan_vien_list": NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC')})

@login_required
def xoa_ca_view(request, phan_cong_id):
    pc = get_object_or_404(PhanCongCaTruc, id=phan_cong_id); vt, ca, day = pc.vi_tri_chot, pc.ca_lam_viec, pc.ngay_truc; pc.delete()
    return render(request, "operations/partials/ca_truc_cell.html", {"phan_congs": [], "vi_tri": vt, "ca": ca, "day": day})