# -*- coding: utf-8 -*-
"""
SCMD Pro - Performance Benchmark Utility
------------------------------
Benchmark script for executive dashboard aggregation logic.
Simulates large datasets: 10k employees, 100k attendance, 5k incidents.
"""

import os
import time
import django
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from users.models import NhanVien, PhongBan, ChucDanh
from clients.models import KhachHangTiemNang, HopDong, MucTieu
from operations.models import PhanCongCaTruc, ChamCong, BaoCaoSuCo, ViTriChot, CaLamViec
from dashboard.application.executive_dashboard import GetExecutiveDashboardUseCase

def generate_mock_data():
    """Populates the database with benchmark volume data."""
    print("--- [Benchmark] Generating Mock Data ---")
    tenant_id = settings.SCMD_ORGANIZATION_ID
    today = timezone.now().date()

    with transaction.atomic():
        # 1. Base Setup
        pb = PhongBan.objects.create(ten_phong_ban="Operations")
        cd = ChucDanh.objects.create(ten_chuc_danh="Security Guard")
        ca = CaLamViec.objects.create(ten_ca="Shift 1", gio_bat_dau="06:00", gio_ket_thuc="18:00")
        kh = KhachHangTiemNang.objects.create(ten_cong_ty="Big Client Corp", sdt="0999")
        hd = HopDong.objects.create(
            so_hop_dong=f"HD-{int(time.time())}", 
            khach_hang_cu=kh, 
            ngay_hieu_luc=today, 
            ngay_het_han=today + timedelta(days=365), 
            gia_tri=50000000,
            trang_thai="HIEU_LUC"
        )
        mt = MucTieu.objects.create(hop_dong=hd, ten_muc_tieu="Main Site", vi_do=10.0, kinh_do=106.0)
        vt = ViTriChot.objects.create(muc_tieu=mt, ten_vi_tri="Gate A")

        # 2. Employees (10,000)
        print("Creating 10,000 employees...")
        employees = [
            NhanVien(
                ma_nhan_vien=f"EMP{i:05d}", 
                ho_ten=f"Guard {i}", 
                phong_ban=pb, 
                chuc_danh=cd, 
                trang_thai_lam_viec="CHINHTHUC"
            ) for i in range(10000)
        ]
        NhanVien.objects.bulk_create(employees)
        all_nv_ids = list(NhanVien.objects.values_list('id', flat=True))

        # 3. Shifts & Attendance (100,000 across history)
        print("Creating 100,000 attendance records...")
        shifts = []
        for i in range(100000):
            # Distribute over last 10 days
            day = today - timedelta(days=(i % 10))
            shifts.append(
                PhanCongCaTruc(
                    nhan_vien_id=all_nv_ids[i % 10000], 
                    vi_tri_chot=vt, 
                    ca_lam_viec=ca, 
                    ngay_truc=day,
                    tenant_id=tenant_id
                )
            )
        PhanCongCaTruc.objects.bulk_create(shifts)
        
        all_pc_ids = list(PhanCongCaTruc.objects.values_list('id', flat=True))
        attendance = [
            ChamCong(
                ca_truc_id=all_pc_ids[i], 
                thoi_gian_check_in=timezone.now(),
                tenant_id=tenant_id
            ) for i in range(len(all_pc_ids))
        ]
        ChamCong.objects.bulk_create(attendance)

        # 4. Incidents (5,000)
        print("Creating 5,000 incidents...")
        incidents = [
            BaoCaoSuCo(
                tieu_de=f"Incident {i}", 
                muc_tieu=mt, 
                muc_do="TB", 
                trang_thai="CHO_XU_LY",
                tenant_id=tenant_id
            ) for i in range(5000)
        ]
        BaoCaoSuCo.objects.bulk_create(incidents)

def run_benchmark():
    tenant_id = settings.SCMD_ORGANIZATION_ID
    print(f"--- [Benchmark] Starting Use Case Execution (Tenant: {tenant_id}) ---")
    
    start_time = time.perf_counter()
    result = GetExecutiveDashboardUseCase.execute(user=None, tenant_id=tenant_id)
    end_time = time.perf_counter()
    
    print(f"Aggregation finished in: {end_time - start_time:.4f} seconds")
    print(f"Incident count: {result['count_su_co']}")

if __name__ == "__main__":
    # generate_mock_data() # Uncomment once to seed data
    run_benchmark()
