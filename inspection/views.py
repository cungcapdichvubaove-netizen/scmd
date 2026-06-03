# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: inspection/views.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: Views module Thanh tra.
             MERGED: Giữ logic cũ + Tích hợp Hybrid Trust (GPS check).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import math

# Models & Forms
from .models import LoaiTuanTra, LuotTuanTra, DiemTuanTra, GhiNhanTuanTra, BienBanViPham, DotThanhTra
from users.models import NhanVien
from operations.models import PhanCongCaTruc, ChamCong
from .forms import BienBanViPhamForm, DotThanhTraForm

# Libs for PDF
import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

def get_nv(request):
    try: return request.user.nhan_vien
    except: return None

# --- HELPER: TÍNH KHOẢNG CÁCH (HAVERSINE) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """Tính khoảng cách giữa 2 tọa độ (trả về mét)"""
    if not all([lat1, lon1, lat2, lon2]): return None
    try:
        R = 6371000 # Bán kính trái đất (m)
        phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return None

# ==============================================================================
# WEB DASHBOARD & TOOLS (CODE CŨ GIỮ NGUYÊN)
# ==============================================================================

@login_required
def dashboard_view(request):
    total_routes = LoaiTuanTra.objects.count()
    active_patrols = LuotTuanTra.objects.filter(trang_thai='DANG_DI')
    
    today = timezone.now().date()
    start_week = today - timezone.timedelta(days=today.weekday())
    chart_labels = []
    chart_data = []
    
    for i in range(7):
        day = start_week + timezone.timedelta(days=i)
        chart_labels.append(day.strftime('%d/%m'))
        count = LuotTuanTra.objects.filter(thoi_gian_bat_dau__date=day, trang_thai='HOAN_THANH').count()
        chart_data.append(count)

    context = {
        'total_routes': total_routes,
        'active_patrols_count': active_patrols.count(),
        'active_patrols_list': active_patrols[:5],
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'inspection/dashboard.html', context)

@login_required
def export_qr_pdf(request, loai_id):
    loai = get_object_or_404(LoaiTuanTra, pk=loai_id)
    diems = DiemTuanTra.objects.filter(loai_tuan_tra=loai).order_by('thu_tu')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
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
        p.setFont("Helvetica-Bold", 10)
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
# MOBILE APP LOGIC (ĐÃ NÂNG CẤP)
# ==============================================================================

@login_required
def mobile_tuan_tra_list(request):
    nv = get_nv(request)
    if not nv: return redirect('operations:mobile_dashboard')
    
    ca_hien_tai = PhanCongCaTruc.objects.filter(nhan_vien=nv, ngay_truc=timezone.now().date()).first()
    lo_trinhs = []
    if ca_hien_tai:
        lo_trinhs = LoaiTuanTra.objects.filter(muc_tieu=ca_hien_tai.vi_tri_chot.muc_tieu)
    
    luot_dang_di = LuotTuanTra.objects.filter(nhan_vien=nv, trang_thai='DANG_DI').first()
    return render(request, 'inspection/mobile/tuan_tra_list.html', {'lo_trinhs': lo_trinhs, 'luot_dang_di': luot_dang_di})

@login_required
def bat_dau_tuan_tra(request, loai_id):
    nv = get_nv(request)
    loai = get_object_or_404(LoaiTuanTra, id=loai_id)
    luot, _ = LuotTuanTra.objects.get_or_create(nhan_vien=nv, trang_thai='DANG_DI', defaults={'loai_tuan_tra': loai})
    return redirect('inspection:thuc_hien_tuan_tra', luot_id=luot.id)

@login_required
def thuc_hien_tuan_tra(request, luot_id):
    luot = get_object_or_404(LuotTuanTra, id=luot_id, nhan_vien=request.user.nhan_vien)
    cac_diem = DiemTuanTra.objects.filter(loai_tuan_tra=luot.loai_tuan_tra).order_by('thu_tu')
    da_quet_ids = GhiNhanTuanTra.objects.filter(luot_tuan_tra=luot).values_list('diem_tuan_tra_id', flat=True)
    return render(request, 'inspection/mobile/tuan_tra.html', {'luot_tuan_tra': luot, 'cac_diem': cac_diem, 'da_quet_ids': da_quet_ids})

# --- CORE LOGIC: XỬ LÝ QUÉT QR ---
@require_POST
@login_required
def ghi_nhan_diem(request):
    if request.method == "POST":
        luot_id = request.POST.get('luot_id')
        ma_qr = request.POST.get('ma_qr')
        lat_req = request.POST.get('lat') # Nhận GPS từ Client
        lng_req = request.POST.get('lng')

        luot = get_object_or_404(LuotTuanTra, id=luot_id, nhan_vien=request.user.nhan_vien)
        diem = DiemTuanTra.objects.filter(loai_tuan_tra=luot.loai_tuan_tra, ma_qr=ma_qr).first()
        
        if not diem:
            return JsonResponse({'success': False, 'message': 'Mã QR không hợp lệ!'})
        
        if GhiNhanTuanTra.objects.filter(luot_tuan_tra=luot, diem_tuan_tra=diem).exists():
            return JsonResponse({'success': False, 'message': 'Đã quét điểm này rồi!'})

        # LOGIC HYBRID TRUST
        trang_thai = 'HOP_LE'
        khoang_cach = 0.0
        msg_warning = ""

        # Case 1: Mất GPS (Hầm/Trong nhà)
        if not lat_req or not lng_req or lat_req == 'null':
            trang_thai = 'MAT_GPS'
            msg_warning = " (Mất GPS - Đã ghi nhận)"
        else:
            # Case 2: Có GPS -> Tính khoảng cách
            dist = calculate_distance(diem.vi_do, diem.kinh_do, lat_req, lng_req)
            if dist is not None:
                khoang_cach = dist
                limit = diem.ban_kinh_cho_phep # 50m
                
                if dist <= limit:
                    trang_thai = 'HOP_LE'
                elif dist <= 200: # Cho phép sai số máy cùi
                    trang_thai = 'CANH_BAO_XA'
                    msg_warning = f" (Hơi xa {int(dist)}m - Đã ghi nhận)"
                else:
                    return JsonResponse({'success': False, 'message': f'Vị trí quá xa ({int(dist)}m)! Hãy lại gần điểm quét.'})

        GhiNhanTuanTra.objects.create(
            luot_tuan_tra=luot,
            diem_tuan_tra=diem,
            lat_thuc_te=lat_req if lat_req and lat_req != 'null' else None,
            lng_thuc_te=lng_req if lng_req and lng_req != 'null' else None,
            khoang_cach=khoang_cach,
            ket_qua=trang_thai,
            ghi_chu=msg_warning.strip()
        )
        return JsonResponse({'success': True, 'ten_diem': diem.ten_diem, 'message': 'Thành công' + msg_warning})

    return JsonResponse({'success': False, 'message': 'Lỗi hệ thống'}, status=400)

@login_required
def hoan_thanh_tuan_tra(request, luot_id):
    luot = get_object_or_404(LuotTuanTra, id=luot_id, nhan_vien=request.user.nhan_vien)
    luot.trang_thai = 'HOAN_THANH'; luot.thoi_gian_ket_thuc = timezone.now(); luot.save()
    messages.success(request, "Đã hoàn thành tuần tra!")
    return redirect('inspection:mobile_tuan_tra_list')

# --- THANH TRA VIEW ---
@login_required
def mobile_lap_bien_ban(request):
    nv = get_nv(request)
    if request.method == "POST":
        form = BienBanViPhamForm(request.POST, request.FILES)
        if form.is_valid():
            bb = form.save(commit=False); bb.nguoi_lap = nv
            ca = PhanCongCaTruc.objects.filter(nhan_vien=bb.doi_tuong_vi_pham, ngay_truc=timezone.now().date()).first()
            if ca: bb.muc_tieu = ca.vi_tri_chot.muc_tieu
            
            if not bb.muc_tieu: 
                messages.error(request, "Không tìm thấy ca trực của NV này!"); 
            else:
                bb.save(); messages.success(request, "Lập biên bản thành công!"); return redirect('operations:mobile_dashboard')
    else: form = BienBanViPhamForm()
    return render(request, 'inspection/mobile/lap_bien_ban.html', {'form': form})

@login_required
def mobile_dot_thanh_tra(request):
    return render(request, 'inspection/mobile/dot_thanh_tra.html', {})
