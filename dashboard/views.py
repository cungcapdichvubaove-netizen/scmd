# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: dashboard/views.py
Author: Mr. Anh
Created Date: 2025-12-06
Description: Views cho Dashboard CEO.
             Cung cấp số liệu tổng quan cho Trung tâm Chỉ huy.
             Logic giữ nguyên: Sử dụng SoQuy, thống kê HR, CRM, OPS, Inventory.
"""

import json
from datetime import timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q

# IMPORT MODELS
from users.models import NhanVien
from clients.models import MucTieu, KhachHangTiemNang, HopDong
from operations.models import BaoCaoSuCo, PhanCongCaTruc
from inventory.models import VatTu
# --- FIX LỖI IMPORT: Dùng model SoQuy từ file mới ---
from accounting.models_soquy import SoQuy
from workflow.models import Proposal, Task 


@login_required
def dashboard_main(request):
    """
    EXECUTIVE DASHBOARD (CEO VIEW)
    Cung cấp số liệu thời gian thực cho Trung tâm chỉ huy SCMD.
    """
    # Khởi tạo các giá trị mặc định để tránh lỗi UnboundLocalError
    today = timezone.now().date()
    this_month = today.month
    this_year = today.year
    start_of_month = today.replace(day=1)
    
    try:
        # --- 1. NHÂN SỰ (HR) ---
        # Tối ưu: Đếm trực tiếp từ Database
        tong_nhan_vien = NhanVien.objects.count()
        nv_chinh_thuc = NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC').count()
        nv_thu_viec = NhanVien.objects.filter(trang_thai_lam_viec='THUVIEC').count()
        nv_moi = NhanVien.objects.filter(ngay_vao_lam__month=this_month, ngay_vao_lam__year=this_year).count()

        # --- 2. KINH DOANH (CRM) ---
        tong_khach_hang = KhachHangTiemNang.objects.count()
        khach_hang_moi = KhachHangTiemNang.objects.filter(ngay_tao__gte=start_of_month).count()
        
        # Tổng giá trị hợp đồng đang hiệu lực
        doanh_thu_du_kien = HopDong.objects.filter(
            trang_thai='HIEU_LUC'
        ).aggregate(total=Sum('gia_tri'))['total'] or 0

        # --- 3. TÀI CHÍNH (FINANCE - CASH FLOW) ---
        # FIX: Dùng SoQuy và trường 'ngay_lap'
        # Thêm kiểm tra năm để tránh lấy dữ liệu tháng này của năm trước
        thuc_thu = SoQuy.objects.filter(
            loai_phieu='THU', 
            ngay_lap__month=this_month,
            ngay_lap__year=this_year
        ).aggregate(total=Sum('so_tien'))['total'] or 0
        
        thuc_chi = SoQuy.objects.filter(
            loai_phieu='CHI', 
            ngay_lap__month=this_month,
            ngay_lap__year=this_year
        ).aggregate(total=Sum('so_tien'))['total'] or 0
        
        loi_nhuan_thuc = thuc_thu - thuc_chi

        # --- 4. VẬN HÀNH (OPS) ---
        # Tỷ lệ quân số đi làm hôm nay
        tong_ca = PhanCongCaTruc.objects.filter(ngay_truc=today).count()
        da_checkin = PhanCongCaTruc.objects.filter(
            ngay_truc=today, 
            chamcong__thoi_gian_check_in__isnull=False
        ).distinct().count() # Dùng distinct để tránh đếm lặp nếu có lỗi data tham chiếu
        
        ty_le_quan_so = int((da_checkin / tong_ca) * 100) if tong_ca > 0 else 0
        
        # Thống kê Sự cố
        su_co_moi = BaoCaoSuCo.objects.filter(trang_thai='CHO_XU_LY').count()
        su_co_nghiem_trong = BaoCaoSuCo.objects.filter(
            muc_do__in=['CAO', 'NGUY_HIEM'], 
            trang_thai__in=['CHO_XU_LY', 'DANG_XU_LY']
        ).count()
        
        # Danh sách sự cố nóng (Mới nhất)
        # Tối ưu: Sử dụng select_related để giảm query khi truy cập muc_tieu trong template
        ds_su_co = BaoCaoSuCo.objects.filter(
            trang_thai__in=['CHO_XU_LY', 'DANG_XU_LY']
        ).select_related('muc_tieu').order_by('-created_at')[:5]
        
        count_su_co = su_co_moi + BaoCaoSuCo.objects.filter(trang_thai='DANG_XU_LY').count()

        # --- 5. KHO (INVENTORY) ---
        canh_bao_kho = VatTu.objects.filter(so_luong_ton__lte=10).count()

        # --- 6. WORKFLOW (VIỆC CẦN LÀM) ---
        de_xuat_can_duyet = 0
        cong_viec_cua_toi = 0
        
        if hasattr(request.user, 'nhan_vien'):
            nv = request.user.nhan_vien
            de_xuat_can_duyet = Proposal.objects.filter(trang_thai__in=['MOI', 'DANG_XU_LY']).count()
            cong_viec_cua_toi = Task.objects.filter(
                nguoi_nhan=nv,
                trang_thai__in=['MOI', 'DANG_THUC_HIEN']
            ).count()

        # --- 7. BIỂU ĐỒ (CHART DATA) ---
        chart_labels = []
        data_su_co = []
        data_doanh_thu = [] 
        
        # Tối ưu query trong loop: Lấy dữ liệu gộp một lần nếu có thể, 
        # nhưng để giữ đúng logic nguyên bản của tác giả, ta tối ưu filter date.
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime('%d/%m'))
            
            # Sự cố trong ngày
            sc = BaoCaoSuCo.objects.filter(created_at__date=d).count()
            data_su_co.append(sc)
            
            # Demo doanh thu (Giữ nguyên logic demo cho biểu đồ đẹp)
            # Tối ưu: aggregate trả về dictionary, tránh truy vấn thừa
            daily_revenue = HopDong.objects.filter(ngay_ky=d).aggregate(val=Sum('gia_tri'))['val'] or 0
            data_doanh_thu.append(int(daily_revenue / 12) if daily_revenue else 0) 

    except Exception as e:
        # Ghi log lỗi nếu cần và thiết lập giá trị an toàn để giao diện không crash
        print(f"Error in Dashboard SCMD: {str(e)}")
        # (Trong môi trường production, nên dùng logging thay vì print)
        tong_nhan_vien = nv_chinh_thuc = nv_thu_viec = nv_moi = 0
        tong_khach_hang = khach_hang_moi = doanh_thu_du_kien = 0
        thuc_thu = thuc_chi = loi_nhuan_thuc = 0
        ty_le_quan_so = count_su_co = su_co_moi = su_co_nghiem_trong = 0
        canh_bao_kho = de_xuat_can_duyet = cong_viec_cua_toi = 0
        ds_su_co = []
        chart_labels = []
        data_su_co = []
        data_doanh_thu = []

    context = {
        'tong_nhan_vien': tong_nhan_vien,
        'nv_chinh_thuc': nv_chinh_thuc,
        'nv_thu_viec': nv_thu_viec,
        'nv_moi': nv_moi,
        'tong_khach_hang': tong_khach_hang,
        'khach_hang_moi': khach_hang_moi,
        'doanh_thu_du_kien': doanh_thu_du_kien,
        'loi_nhuan_thuc': loi_nhuan_thuc,
        'ty_le_quan_so': ty_le_quan_so,
        'count_su_co': count_su_co,
        'su_co_moi': su_co_moi,
        'su_co_nghiem_trong': su_co_nghiem_trong,
        'ds_su_co': ds_su_co,      
        'su_co_nong': ds_su_co,    
        'canh_bao_kho': canh_bao_kho,
        'can_duyet': de_xuat_can_duyet,        
        'de_xuat_can_duyet': de_xuat_can_duyet, 
        'cong_viec_cua_toi': cong_viec_cua_toi,
        'chart_labels': json.dumps(chart_labels),
        'data_su_co': json.dumps(data_su_co),
        'data_doanh_thu': json.dumps(data_doanh_thu),
    }
    
    return render(request, "dashboard/main.html", context)