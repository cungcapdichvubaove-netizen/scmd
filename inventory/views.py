# file: inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count, Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator

# Import đầy đủ các models cần thiết
from .models import VatTu, PhieuNhap, PhieuXuat, ChiTietPhieuXuat, CongCuTaiMucTieu, LoaiVatTu, ChiTietPhieuNhap

@login_required
def dashboard_view(request):
    """
    Dashboard Quản lý Kho & Vật tư
    """
    # 1. Thống kê tổng quan
    tong_loai = VatTu.objects.count()
    
    # --- SỬA LỖI TÍNH TỔNG GIÁ TRỊ TỒN KHO ---
    # Logic: Lấy giá nhập gần nhất của từng vật tư * Số lượng tồn hiện tại
    
    # Tạo subquery để lấy đơn giá từ phiếu nhập mới nhất
    gia_nhap_gan_nhat = ChiTietPhieuNhap.objects.filter(
        vat_tu=OuterRef('pk')
    ).order_by('-phieu_nhap__ngay_nhap').values('don_gia')[:1]

    # Gán giá vào danh sách vật tư và tính tổng (xử lý Python để an toàn)
    ds_vat_tu = VatTu.objects.annotate(
        gia_moi_nhat=Coalesce(Subquery(gia_nhap_gan_nhat), 0, output_field=DecimalField())
    )
    
    tong_gia_tri = 0
    for vt in ds_vat_tu:
        tong_gia_tri += vt.so_luong_ton * vt.gia_moi_nhat

    # 2. Cảnh báo tồn kho (Dùng so_luong_ton)
    # Lấy các vật tư có số lượng tồn <= mức cảnh báo
    sap_het_hang = VatTu.objects.filter(so_luong_ton__lte=F('muc_canh_bao')).order_by('so_luong_ton')
    
    # 3. Đếm số phiếu xuất trong tháng này
    this_month = timezone.now().month
    phieu_xuat_trong_thang = PhieuXuat.objects.filter(ngay_xuat__month=this_month).count()
    
    # 4. Lịch sử xuất kho mới nhất (10 phiếu)
    lich_su_xuat = PhieuXuat.objects.select_related('nhan_vien_nhan', 'muc_tieu_nhan').order_by('-ngay_xuat')[:10]

    context = {
        "title": "Quản lý Kho & Vật tư",
        "tong_loai": tong_loai,
        "tong_gia_tri": tong_gia_tri,
        "sap_het_hang": sap_het_hang,
        "phieu_xuat_trong_thang": phieu_xuat_trong_thang,
        "lich_su_xuat": lich_su_xuat,
    }
    return render(request, "inventory/dashboard_kho.html", context)

# --- VIEW CÔNG CỤ TẠI MỤC TIÊU ---
@login_required
def cong_cu_muc_tieu(request):
    """Xem mục tiêu nào đang giữ bao nhiêu công cụ"""
    cong_cu_list = CongCuTaiMucTieu.objects.select_related('muc_tieu', 'vat_tu').order_by('muc_tieu')
    
    context = {
        'cong_cu_list': cong_cu_list
    }
    return render(request, 'inventory/cong_cu_muc_tieu.html', context)

# --- VIEW BÁO CÁO TỒN KHO ---
@login_required
def bao_cao_ton_kho(request):
    """Báo cáo chi tiết tồn kho"""
    query = request.GET.get('q', '')
    loai_id = request.GET.get('loai', '')
    
    vat_tu_list = VatTu.objects.all().select_related('loai_vat_tu')
    
    if query:
        vat_tu_list = vat_tu_list.filter(ten_vat_tu__icontains=query)
    if loai_id:
        vat_tu_list = vat_tu_list.filter(loai_vat_tu_id=loai_id)
        
    # Phân trang
    paginator = Paginator(vat_tu_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'ds_loai': LoaiVatTu.objects.all(),
        'query': query,
        'selected_loai': int(loai_id) if loai_id else None
    }
    return render(request, 'inventory/bao_cao_ton_kho.html', context)

# --- VIEW IN ẤN ---
@login_required
def chi_tiet_phieu_nhap(request, pk):
    phieu = get_object_or_404(PhieuNhap, pk=pk)
    return render(request, 'inventory/print/phieu_nhap_detail.html', {'phieu': phieu})

@login_required
def chi_tiet_phieu_xuat(request, pk):
    phieu = get_object_or_404(PhieuXuat, pk=pk)
    return render(request, 'inventory/print/phieu_xuat_detail.html', {'phieu': phieu})