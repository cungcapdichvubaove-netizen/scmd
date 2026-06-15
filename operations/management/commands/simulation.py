# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/management/commands/simulation.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-24
Description: AI Engine giả lập hoạt động trên toàn quốc (National Scale Demo).
             UPGRADE PHASE 12.3: 
             - Hỗ trợ tạo dữ liệu mục tiêu giả lập toàn quốc (HN, ĐN, HCM).
             - Tự động Seed dữ liệu nếu DB trống.
             - Tối ưu hóa hiển thị tọa độ trên bản đồ Real-time.
"""

import time
import random
import sys
import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.gis.geos import Point
from faker import Faker
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Import Models
from users.models import NhanVien
from clients.models import MucTieu
from operations.models import PhanCongCaTruc, ChamCong, BaoCaoSuCo, ViTriChot, CaLamViec

logger = logging.getLogger(__name__)
fake = Faker('vi_VN')

# Tọa độ các trung tâm kinh tế lớn để làm mốc demo
VIETNAM_HUBS = {
    "Hà Nội": (21.0285, 105.8542),
    "Đà Nẵng": (16.0544, 108.2022),
    "TP. Hồ Chí Minh": (10.8231, 106.6297),
    "Cần Thơ": (10.0371, 105.7882),
    "Hải Phòng": (20.8449, 106.6881)
}

class Command(BaseCommand):
    help = 'Chạy giả lập "Sự sống" quy mô toàn quốc cho SCMD Erp.'

    def handle(self, *args, **kwargs):
        self.print_banner()
        
        # 1. KIỂM TRA & TẠO DỮ LIỆU MẪU TOÀN QUỐC
        self.ensure_national_data()

        # 2. THỰC HIỆN RESET DỮ LIỆU VẬN HÀNH
        self.reset_daily_data()

        # 3. THIẾT LẬP CA TRỰC
        self.generate_shifts_today()

        # 4. BẮT ĐẦU VÒNG LẶP
        self.start_simulation_loop()

    def print_banner(self):
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write(self.style.SUCCESS("   🚀 SCMD NATIONAL SIMULATION ENGINE - V12.3"))
        self.stdout.write(self.style.SUCCESS("   Coverage: North, Central, South Vietnam"))
        self.stdout.write(self.style.SUCCESS("="*60))

    def ensure_national_data(self):
        """Đảm bảo có ít nhất một vài mục tiêu trên toàn quốc để demo đẹp hơn"""
        if not NhanVien.objects.exists():
            self.stdout.write(self.style.WARNING("! Đang tạo nhân viên mẫu..."))
            for _ in range(20):
                NhanVien.objects.create(
                    ho_ten=fake.name(),
                    ma_nhan_vien=f"NV{random.randint(1000,9999)}",
                    trang_thai_lam_viec='CHINHTHUC'
                )

        if not MucTieu.objects.exists():
            self.stdout.write(self.style.WARNING("! Đang tạo mục tiêu demo trên toàn quốc..."))
            for city, coords in VIETNAM_HUBS.items():
                mt = MucTieu.objects.create(
                    ten_muc_tieu=f"Vingroup Center - {city}",
                    dia_chi=f"Khu vực trung tâm {city}",
                    vi_do=coords[0],
                    kinh_do=coords[1]
                )
                # Tạo ít nhất 1 vị trí chốt cho mỗi mục tiêu
                ViTriChot.objects.create(ten_vi_tri="Chốt Cổng Chính", muc_tieu=mt)

        if not CaLamViec.objects.exists():
            CaLamViec.objects.create(ten_ca="Ca Hành Chính", gio_bat_dau="08:00", gio_ket_thuc="17:00")

    def reset_daily_data(self):
        self.stdout.write(self.style.WARNING("\n[1/3] 🧹 Resetting operational data..."))
        today = timezone.localdate()
        start_at = timezone.make_aware(datetime.combine(today, datetime.min.time()), timezone.get_current_timezone())
        end_at = start_at + timedelta(days=1)
        BaoCaoSuCo.objects.filter(created_at__gte=start_at, created_at__lt=end_at).delete()
        ChamCong.objects.filter(thoi_gian_check_in__gte=start_at, thoi_gian_check_in__lt=end_at).delete()
        self.stdout.write(self.style.SUCCESS("   ✅ Data cleaned."))

    def generate_shifts_today(self):
        self.stdout.write(self.style.WARNING("\n[2/3] 📅 Lập lịch trực toàn quốc..."))
        today = timezone.now().date()
        
        nhan_viens = list(NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC'))
        vi_tris = list(ViTriChot.objects.select_related('muc_tieu').all())
        ca_lam_viecs = list(CaLamViec.objects.all())

        count = 0
        for nv in nhan_viens[:30]:
            if not PhanCongCaTruc.objects.filter(nhan_vien=nv, ngay_truc=today).exists():
                vt = random.choice(vi_tris)
                ca = random.choice(ca_lam_viecs)
                PhanCongCaTruc.objects.create(
                    nhan_vien=nv, vi_tri_chot=vt, ca_lam_viec=ca, ngay_truc=today
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"   ✅ Đã phân bổ {count} nhân sự trực tại 3 miền."))

    def _safe_send_notification(self, layer, payload):
        if layer:
            try:
                async_to_sync(layer.group_send)(
                    "notifications", {"type": "send_notification", "payload": payload}
                )
            except: pass

    def start_simulation_loop(self):
        self.stdout.write(self.style.WARNING("\n[3/3] 🎬 LIVE DEMO STARTING (National View)..."))
        today = timezone.now().date()
        
        while True:
            layer = get_channel_layer()
            try:
                # 1. GIẢ LẬP CHECK-IN
                pending = PhanCongCaTruc.objects.select_related('nhan_vien', 'vi_tri_chot__muc_tieu').filter(
                    ngay_truc=today, chamcong__isnull=True
                )

                if pending.exists() and random.random() < 0.4:
                    pc = pending.first()
                    mt = pc.vi_tri_chot.muc_tieu
                    
                    # Tọa độ thông minh quanh Hub
                    lat = float(mt.vi_do) + random.uniform(-0.01, 0.01)
                    lng = float(mt.kinh_do) + random.uniform(-0.01, 0.01)
                    
                    ChamCong.objects.create(
                        ca_truc=pc, thoi_gian_check_in=timezone.now(),
                        location_check_in=Point(lng, lat), vi_tri_hop_le=True
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"📍 [TOÀN QUỐC] {pc.nhan_vien.ho_ten} check-in tại {mt.ten_muc_tieu}"))
                    
                    self._safe_send_notification(layer, {
                        "event_type": "CHECK_IN",
                        "title": f"Mục tiêu: {mt.ten_muc_tieu}",
                        "message": f"NV: {pc.nhan_vien.ho_ten} đã vào ca.",
                        "status": "success", "lat": lat, "lng": lng
                    })

                # 2. GIẢ LẬP SỰ CỐ TOÀN CẦU
                if random.random() < 0.15:
                    active = PhanCongCaTruc.objects.filter(ngay_truc=today, chamcong__isnull=False)
                    if active.exists():
                        pc = random.choice(active)
                        tieu_de = random.choice(["Xâm nhập trái phép", "Hệ thống báo cháy kích hoạt", "Mất kết nối Camera"])
                        
                        BaoCaoSuCo.objects.create(
                            tieu_de=tieu_de, muc_tieu=pc.vi_tri_chot.muc_tieu,
                            nhan_vien_bao_cao=pc.nhan_vien, ca_truc=pc,
                            muc_do='CAO', trang_thai='CHO_XU_LY', thoi_gian_phat_hien=timezone.now()
                        )
                        
                        self.stdout.write(self.style.ERROR(f"🚨 [KHẨN CẤP] {tieu_de} tại {pc.vi_tri_chot.muc_tieu.ten_muc_tieu}"))
                        
                        self._safe_send_notification(layer, {
                            "event_type": "INCIDENT",
                            "title": "CẢNH BÁO AN NINH",
                            "message": f"{tieu_de} - Khu vực: {pc.vi_tri_chot.muc_tieu.ten_muc_tieu}",
                            "status": "danger"
                        })

                time.sleep(random.randint(2, 5))

            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\n🛑 Đã dừng giả lập."))
                sys.exit()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ Error: {e}"))
                time.sleep(5)