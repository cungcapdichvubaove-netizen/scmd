# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/management/commands/simulation.py
Author: Mr. Anh (CTO)
Created Date: 2025-12-10
Description: AI Engine giả lập hoạt động doanh nghiệp thời gian thực.
             FIXED: Tương thích với GeoDjango (Sử dụng PointField).
"""

import time
import random
import sys
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# GEO IMPORT (Quan trọng)
from django.contrib.gis.geos import Point

# Import Models
from users.models import NhanVien
from clients.models import MucTieu
from operations.models import PhanCongCaTruc, ChamCong, BaoCaoSuCo, ViTriChot, CaLamViec

fake = Faker('vi_VN')

class Command(BaseCommand):
    help = 'Chạy giả lập "Sự sống" cho hệ thống (Live Demo Mode) với chế độ Reset.'

    def handle(self, *args, **kwargs):
        self.print_banner()
        
        # 1. KIỂM TRA DỮ LIỆU NỀN
        if not NhanVien.objects.exists() or not MucTieu.objects.exists():
            self.stdout.write(self.style.ERROR("❌ LỖI: Chưa có dữ liệu Nhân viên hoặc Mục tiêu."))
            return

        # 2. THỰC HIỆN RESET DỮ LIỆU CŨ
        self.reset_daily_data()

        # 3. KHỞI TẠO CA TRỰC MỚI
        self.generate_shifts_today()

        # 4. BẮT ĐẦU VÒNG LẶP GIẢ LẬP
        self.start_simulation_loop()

    def print_banner(self):
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write(self.style.SUCCESS("   🚀 SCMD LIVE SIMULATION ENGINE - GEO ENABLED"))
        self.stdout.write(self.style.SUCCESS("="*60))

    def reset_daily_data(self):
        """Xóa dữ liệu vận hành của ngày hôm nay"""
        self.stdout.write(self.style.WARNING("\n[1/3] 🧹 Đang dọn dẹp dữ liệu cũ..."))
        today = timezone.now().date()
        BaoCaoSuCo.objects.filter(created_at__date=today).delete()
        ChamCong.objects.filter(thoi_gian_check_in__date=today).delete()
        self.stdout.write(self.style.SUCCESS(f"   ✅ Đã reset dữ liệu hôm nay."))

    def generate_shifts_today(self):
        """Đảm bảo hôm nay đã có lịch trực"""
        self.stdout.write(self.style.WARNING("\n[2/3] 📅 Đang thiết lập Ca trực hôm nay..."))
        today = timezone.now().date()
        if PhanCongCaTruc.objects.filter(ngay_truc=today).exists():
            self.stdout.write(self.style.SUCCESS("   ✅ Lịch trực hôm nay đã sẵn sàng."))
            return

        nhan_viens = list(NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC'))
        vi_tris = list(ViTriChot.objects.all())
        ca_lam_viecs = list(CaLamViec.objects.all())

        if not vi_tris or not ca_lam_viecs:
            self.stdout.write(self.style.ERROR("   ❌ Thiếu dữ liệu Vị trí hoặc Ca làm việc."))
            return

        count = 0
        for nv in nhan_viens[:50]:
            vt = random.choice(vi_tris)
            ca = random.choice(ca_lam_viecs)
            PhanCongCaTruc.objects.create(
                nhan_vien=nv, vi_tri_chot=vt, ca_lam_viec=ca, ngay_truc=today
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"   ✅ Đã phân công {count} ca trực mới."))

    def start_simulation_loop(self):
        """Vòng lặp sinh sự kiện"""
        self.stdout.write(self.style.WARNING("\n[3/3] 🎬 BẮT ĐẦU MÔ PHỎNG (Nhấn Ctrl+C để dừng)..."))
        today = timezone.now().date()
        layer = get_channel_layer()

        while True:
            try:
                # --- SCENARIO 1: CHECK-IN ---
                pending_shifts = PhanCongCaTruc.objects.filter(
                    ngay_truc=today,
                    chamcong__isnull=True
                )

                if pending_shifts.exists() and random.choice([True, False]):
                    pc = pending_shifts.first()
                    muc_tieu = pc.vi_tri_chot.muc_tieu
                    
                    # Giả lập tọa độ
                    try:
                        base_lat = float(muc_tieu.vi_do) if muc_tieu.vi_do else 21.0285
                        base_lng = float(muc_tieu.kinh_do) if muc_tieu.kinh_do else 105.8542
                    except:
                        base_lat, base_lng = 21.0285, 105.8542

                    my_lat = base_lat + random.uniform(-0.0005, 0.0005)
                    my_lng = base_lng + random.uniform(-0.0005, 0.0005)

                    # [FIX]: Tạo đối tượng Point cho GeoDjango
                    # Lưu ý: Point(longitude, latitude)
                    location_point = Point(my_lng, my_lat)

                    cc = ChamCong.objects.create(
                        ca_truc=pc,
                        thoi_gian_check_in=timezone.now(),
                        location_check_in=location_point, # Dùng trường PointField
                        vi_tri_hop_le=True,
                        thiet_bi_check_in="Simulated Device"
                    )
                    
                    msg = f"👉 [CHECK-IN] {pc.nhan_vien.ho_ten} tại {muc_tieu.ten_muc_tieu}"
                    self.stdout.write(self.style.SUCCESS(msg))
                    
                    # Gửi Socket (FE vẫn cần lat/lng rời để hiển thị bản đồ)
                    async_to_sync(layer.group_send)(
                        "notifications",
                        {
                            "type": "send_notification",
                            "payload": {
                                "event_type": "CHECK_IN",
                                "title": f"Check-in: {pc.nhan_vien.ho_ten}",
                                "message": f"Tại {muc_tieu.ten_muc_tieu}",
                                "status": "success",
                                "lat": my_lat,
                                "lng": my_lng
                            }
                        }
                    )

                # --- SCENARIO 2: SỰ CỐ ---
                if random.random() < 0.3: 
                    active_shifts = PhanCongCaTruc.objects.filter(
                        ngay_truc=today,
                        chamcong__thoi_gian_check_in__isnull=False
                    )
                    
                    if active_shifts.exists():
                        pc = random.choice(active_shifts)
                        tieu_de = random.choice(["Phát hiện người lạ", "Cửa kho mở", "Mất điện", "Khói lạ"])
                        muc_do = random.choice(['TB', 'CAO', 'NGUY_HIEM'])
                        
                        su_co = BaoCaoSuCo.objects.create(
                            tieu_de=tieu_de,
                            muc_tieu=pc.vi_tri_chot.muc_tieu,
                            nhan_vien_bao_cao=pc.nhan_vien,
                            ca_truc=pc,
                            muc_do=muc_do,
                            trang_thai='CHO_XU_LY',
                            thoi_gian_phat_hien=timezone.now()
                        )
                        
                        msg = f"🔥 [SỰ CỐ] {tieu_de} ({muc_do}) - {pc.nhan_vien.ho_ten}"
                        self.stdout.write(self.style.ERROR(msg))

                        # Gửi Socket
                        async_to_sync(layer.group_send)(
                            "notifications",
                            {
                                "type": "send_notification",
                                "payload": {
                                    "event_type": "INCIDENT",
                                    "title": f"Sự cố: {tieu_de}",
                                    "message": f"Mức độ: {muc_do} - {pc.vi_tri_chot.muc_tieu.ten_muc_tieu}",
                                    "status": "danger" if muc_do == 'NGUY_HIEM' else "warning",
                                    "level": muc_do
                                }
                            }
                        )

                time.sleep(random.randint(2, 5))

            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\n🛑 Đã dừng giả lập."))
                sys.exit()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ Lỗi: {str(e)}"))
                time.sleep(5)