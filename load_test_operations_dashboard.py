# -*- coding: utf-8 -*-
"""
SCMD Pro - Load Test Utility: Operations Dashboard
-------------------------------------------------
Mô tả: Script đo lường hiệu năng Dashboard vận hành khi quy mô mục tiêu tăng lên N.
Tuân thủ: WHITEPAPER.md (Operational Truth & Performance SSOT).
"""

import os
import sys
import time
import django
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

# 1. Cấu hình môi trường Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

from users.models import NhanVien, PhongBan, ChucDanh
from clients.models import HopDong
from operations.models import MucTieu, ViTriChot, CaLamViec, PhanCongCaTruc, ChamCong, BaoCaoSuCo

def run_operations_load_test(n_targets: int):
    print(f"\n=== KHỞI CHẠY LOAD TEST: DASHBOARD VẬN HÀNH (N={n_targets}) ===")
    tenant_id = settings.SCMD_ORGANIZATION_ID
    today = timezone.now().date()
    
    # Đảm bảo có user để login
    admin_user, _ = User.objects.get_or_create(
        username='load_test_admin', 
        defaults={'is_superuser': True, 'is_staff': True, 'email': 'admin@scmd.vn'}
    )
    admin_user.set_password('password123')
    admin_user.save()

    # 2. TẠO DỮ LIỆU GIẢ LẬP TRONG TRANSACTION
    print(f"-> Đang khởi tạo dữ liệu cho {n_targets} mục tiêu...")
    start_gen = time.perf_counter()
    
    with transaction.atomic():
        # Tạo cấu hình nền
        pb, _ = PhongBan.objects.get_or_create(ten_phong_ban="Phòng Nghiệp vụ")
        cd, _ = ChucDanh.objects.get_or_create(ten_chuc_danh="Nhân viên Bảo vệ")
        ca, _ = CaLamViec.objects.get_or_create(ten_ca="Ca 12h", gio_bat_dau="06:00", gio_ket_thuc="18:00")
        hd, _ = HopDong.objects.get_or_create(so_hop_dong="HD-PERF-TEST", tenant_id=tenant_id)

        for i in range(n_targets):
            # Tạo mục tiêu & chốt
            mt = MucTieu.objects.create(
                hop_dong=hd, ten_muc_tieu=f"Mục tiêu Performance {i}",
                tenant_id=tenant_id, vi_do=10.7, kinh_do=106.6
            )
            vt = ViTriChot.objects.create(muc_tieu=mt, ten_vi_tri="Chốt chính", tenant_id=tenant_id)
            
            # Tạo nhân sự trực
            nv = NhanVien.objects.create(
                ho_ten=f"Bảo vệ Perf {i}", ma_nhan_vien=f"P{i:05d}",
                phong_ban=pb, chuc_danh=cd, tenant_id=tenant_id, trang_thai_lam_viec="CHINHTHUC"
            )
            
            # Phân công ca
            pc = PhanCongCaTruc.objects.create(
                nhan_vien=nv, vi_tri_chot=vt, ca_lam_viec=ca, 
                ngay_truc=today, tenant_id=tenant_id
            )
            
            # Giả lập 60% đã check-in
            if i % 10 < 6:
                ChamCong.objects.create(ca_truc=pc, thoi_gian_check_in=timezone.now(), tenant_id=tenant_id)
                
            # Giả lập 5% có sự cố mở
            if i % 20 == 0:
                BaoCaoSuCo.objects.create(
                    tieu_de=f"Sự cố kiểm thử {i}", muc_tieu=mt, 
                    muc_do="CAO", trang_thai="CHO_XU_LY", tenant_id=tenant_id
                )

    end_gen = time.perf_counter()
    print(f"✓ Hoàn tất tạo dữ liệu trong {end_gen - start_gen:.2f}s.")

    # 3. THỰC THI BENCHMARK
    client = Client()
    client.login(username='load_test_admin', password='password123')
    
    dashboard_url = reverse('operations:dashboard_vanhanh')
    print(f"-> Đang gọi dashboard tại {dashboard_url}...")
    
    start_req = time.perf_counter()
    response = client.get(dashboard_url)
    end_req = time.perf_counter()
    
    latency = end_req - start_req
    print(f"===> KẾT QUẢ: Latency = {latency:.4f} giây (Status: {response.status_code})")
    print("=========================================================\n")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_operations_load_test(n)