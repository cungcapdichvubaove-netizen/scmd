# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
File: main/management/commands/seed_data.py
Author: Mr. Anh (CTO)
Description: Kịch bản khởi tạo dữ liệu Enterprise (V8.2 - Geo Fix).
             FIXED: Tương thích hoàn toàn với GeoDjango/PostGIS.
             - Sử dụng PointField thay cho DecimalField lat/long cũ.
             Usage: python manage.py seed_data --clear
"""

import os
import random
from datetime import timedelta, datetime, time as dt_time

from django.contrib.auth.models import User, Group
from django.contrib.gis.geos import Point
<<<<<<< HEAD
from django.core.management.base import BaseCommand, CommandError
=======
from django.core.management.base import BaseCommand
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.db import transaction
from django.utils import timezone
from faker import Faker

from clients.models import KhachHangTiemNang, HopDong, MucTieu
from config.bootstrap_credentials import get_seed_password
from inventory.models import LoaiVatTu
from operations.models import CaLamViec, ViTriChot, PhanCongCaTruc, BaoCaoSuCo, ChamCong
from users.models import NhanVien, ChucDanh, PhongBan, CauHinhMaNhanVien
from workflow.models import Proposal

fake = Faker("vi_VN")

# --- GEO IMPORT (QUAN TRỌNG) ---

# CẤU HÌNH MẬT KHẨU MẶC ĐỊNH
<<<<<<< HEAD
=======
DEFAULT_PASS = get_seed_password()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu Enterprise (500 NV, 3 Ca, Geo-enabled)"

    def add_arguments(self, parser):
<<<<<<< HEAD
        parser.add_argument("--clear", action="store_true", help="Xoa sach du lieu cu")
        parser.add_argument("--password", default=None, help="Password cho user seed (DEV only)")

    def handle(self, *args, **options):
        start_time = datetime.now()
        self.default_password = options["password"]
        if not self.default_password:
            try:
                self.default_password = get_seed_password()
            except RuntimeError as exc:
                raise CommandError(
                    "Thieu password seed. Truyen --password hoac cau hinh SCMD_SEED_PASS/SCMD_ADMIN_PASSWORD/DJANGO_SUPERUSER_PASSWORD."
                ) from exc

        self.stdout.write(self.style.WARNING("Password seed user da duoc cau hinh an toan qua bien moi truong hoac tham so CLI."))
=======
        parser.add_argument("--clear", action="store_true", help="Xóa sạch dữ liệu cũ")

    def handle(self, *args, **options):
        start_time = datetime.now()

        self.stdout.write(self.style.WARNING(f'🔑 Mật khẩu mặc định user: "{DEFAULT_PASS}"'))
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        if options["clear"]:
            self.stdout.write(self.style.WARNING("🗑️ Đang xóa sạch dữ liệu cũ..."))
            self.clean_database()

        self.stdout.write(self.style.HTTP_INFO("🚀 BẮT ĐẦU KHỞI TẠO DỮ LIỆU (GEO MODE)..."))

        try:
            with transaction.atomic():
                meta_data = self.seed_structure()
                nv_data = self.seed_mass_staff(meta_data)
                targets = self.seed_clients_targets(nv_data["managers"])

                # Hàm này đã được sửa để hỗ trợ PointField.
                self.seed_operations(nv_data["guards"], targets)

                self.seed_inventory(nv_data["all"])
                self.seed_workflow(nv_data["all"], targets, nv_data["managers"])

            duration = (datetime.now() - start_time).total_seconds()
            self.stdout.write(self.style.SUCCESS(f"✅ HOÀN TẤT SAU {duration:.2f} GIÂY!"))
            self.stdout.write(self.style.SUCCESS(f"👉 Tổng nhân sự: {NhanVien.objects.count()}"))
            self.stdout.write(self.style.SUCCESS(f"👉 Tổng ca trực: {PhanCongCaTruc.objects.count()}"))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"❌ LỖI NGHIÊM TRỌNG: {exc}"))
            import traceback

            traceback.print_exc()

    def clean_database(self):
        models_list = [
            Proposal,
            BaoCaoSuCo,
            ChamCong,
            PhanCongCaTruc,
            ViTriChot,
            CaLamViec,
            MucTieu,
            HopDong,
            KhachHangTiemNang,
            NhanVien,
            LoaiVatTu,
        ]
        for model in models_list:
            model.objects.all().delete()

        User.objects.filter(is_superuser=False).delete()
        CauHinhMaNhanVien.objects.all().update(so_hien_tai=0)

    def make_aware_dt(self, dt_obj):
        if timezone.is_naive(dt_obj):
            return timezone.make_aware(dt_obj)
        return dt_obj

    def jitter_gps(self, lat, lng, meters=50):
        if not lat or not lng:
            return None, None
        offset = (meters / 111000.0) * random.random()
        return float(lat) + offset, float(lng) + offset

    # --- 1. CẤU TRÚC ---
    def seed_structure(self):
        self.stdout.write("   1. Tạo Cơ cấu tổ chức...")
        pbs = {
            "BOD": "Ban Giám đốc",
            "HR": "HCNS & Đào tạo",
            "OPS": "Phòng Nghiệp vụ",
            "ACC": "Kế toán",
            "SALES": "Kinh doanh",
        }
        pb_objs = {}
        for code, name in pbs.items():
            pb_objs[code], _ = PhongBan.objects.get_or_create(
                ten_phong_ban=name,
                defaults={"mo_ta": code},
            )

        roles = [
            "Tổng Giám đốc",
            "Trưởng phòng",
            "Chỉ huy trưởng",
            "Đội trưởng",
            "Nhân viên Bảo vệ",
            "CSKH",
        ]
        cd_objs = {}
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role)
            cd_objs[role], _ = ChucDanh.objects.get_or_create(
                ten_chuc_danh=role,
                defaults={"nhom_quyen": group},
            )

        return {"pbs": pb_objs, "cds": cd_objs}

    # --- 2. NHÂN SỰ ---
    def seed_mass_staff(self, meta):
        self.stdout.write("   2. Tuyển dụng 500 Nhân sự...")
        pbs, cds = meta["pbs"], meta["cds"]
        conf, _ = CauHinhMaNhanVien.objects.get_or_create(
            defaults={"tien_to": "NV", "so_hien_tai": 0}
        )
        start_id = conf.so_hien_tai

        users_to_create = []
        profiles_to_create = []

        key_roles = [
            (1, "BOD", "Tổng Giám đốc", "tong_giam_doc"),
            (1, "OPS", "Trưởng phòng", "truong_phong_nv"),
            (20, "OPS", "Chỉ huy trưởng", "chi_huy"),
            (478, "OPS", "Nhân viên Bảo vệ", "bv"),
        ]

        current_id = start_id
        for count, pb_code, cd_name, prefix in key_roles:
            for i in range(count):
                current_id += 1
                ma_nv = f"NV{str(current_id).zfill(4)}"
                username = f"{prefix}_{i + 1}" if count > 1 else prefix

                user = User(username=username, email=f"{username}@scmd.vn", is_active=True)
<<<<<<< HEAD
                user.set_password(self.default_password)
=======
                user.set_password(DEFAULT_PASS)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                users_to_create.append(user)

                profiles_to_create.append(
                    {
                        "ma_nv": ma_nv,
                        "ho_ten": fake.name(),
                        "phong_ban": pbs[pb_code],
                        "chuc_danh": cds[cd_name],
                        "sdt": fake.phone_number(),
                        "status": "CHINHTHUC",
                    }
                )

        User.objects.bulk_create(users_to_create, batch_size=500, ignore_conflicts=True)
        created_users = User.objects.in_bulk(field_name="username")

        nv_objects = []
        for idx, user in enumerate(users_to_create):
            if user.username not in created_users:
                continue
            meta_item = profiles_to_create[idx]
            nv_objects.append(
                NhanVien(
                    user=created_users[user.username],
                    ma_nhan_vien=meta_item["ma_nv"],
                    ho_ten=meta_item["ho_ten"],
                    phong_ban=meta_item["phong_ban"],
                    chuc_danh=meta_item["chuc_danh"],
                    sdt_chinh=meta_item["sdt"],
                    trang_thai_lam_viec=meta_item["status"],
                    ngay_vao_lam=fake.date_between(start_date="-2y", end_date="today"),
                )
            )

        NhanVien.objects.bulk_create(nv_objects, batch_size=500, ignore_conflicts=True)
        conf.so_hien_tai = current_id
        conf.save()

        all_staff = list(NhanVien.objects.select_related("chuc_danh", "user"))
        guards = [
            staff
            for staff in all_staff
            if staff.chuc_danh and staff.chuc_danh.ten_chuc_danh == "Nhân viên Bảo vệ"
        ]
        managers = [
            staff
            for staff in all_staff
            if staff.chuc_danh and "Chỉ huy" in staff.chuc_danh.ten_chuc_danh
        ]

        return {"all": all_staff, "guards": guards, "managers": managers}

    # --- 3. KHÁCH HÀNG ---
    def seed_clients_targets(self, managers):
        self.stdout.write("   3. Thiết lập Mạng lưới Mục tiêu...")
        clients = [("Vingroup", 21.0300, 105.8400), ("Samsung", 21.0100, 105.8200)]
        targets = []
        manager = managers[0] if managers else None

        for name, lat, lng in clients:
            kh, _ = KhachHangTiemNang.objects.get_or_create(ten_cong_ty=name)
            hd, _ = HopDong.objects.get_or_create(
                so_hop_dong=f"HD-{name[:3]}",
                defaults={
                    "khach_hang_cu": kh,
                    "ngay_hieu_luc": timezone.now().date(),
                    "ngay_het_han": timezone.now().date() + timedelta(days=365),
                },
            )

            for i in range(1, 3):
                j_lat, j_lng = self.jitter_gps(lat, lng, meters=5000)
                mt, _ = MucTieu.objects.get_or_create(
                    ten_muc_tieu=f"{name} - Chốt {i}",
                    defaults={
                        "hop_dong": hd,
                        "quan_ly_muc_tieu": manager,
                        "vi_do": j_lat,
                        "kinh_do": j_lng,
                        "ban_kinh_cho_phep": 200,
                    },
                )
                targets.append(mt)
                for pos in ["Cổng Chính", "Tuần tra"]:
                    ViTriChot.objects.get_or_create(muc_tieu=mt, ten_vi_tri=pos)
        return targets

    # --- 4. VẬN HÀNH (GEO-ENABLED FIX) ---
    def seed_operations(self, guards, targets):
        self.stdout.write("   4. Vận hành: Xếp lịch & Chấm công (PostGIS)...")

        ca_sang, _ = CaLamViec.objects.get_or_create(
            ten_ca="Ca Sáng",
            defaults={"gio_bat_dau": dt_time(6, 0), "gio_ket_thuc": dt_time(14, 0)},
        )
        ca_chieu, _ = CaLamViec.objects.get_or_create(
            ten_ca="Ca Chiều",
            defaults={"gio_bat_dau": dt_time(14, 0), "gio_ket_thuc": dt_time(22, 0)},
        )

        shifts = [ca_sang, ca_chieu]
        today = timezone.now().date()
        all_positions = list(ViTriChot.objects.all())

        # Chỉ tạo dữ liệu cho 3 ngày gần nhất để nhanh.
        for day_offset in range(3):
            current_date = today - timedelta(days=day_offset)
            daily_guards = list(guards)
            random.shuffle(daily_guards)

            for ca in shifts:
                for pos in all_positions:
                    if not daily_guards:
                        break
                    nv = daily_guards.pop()

                    pc, _ = PhanCongCaTruc.objects.get_or_create(
                        vi_tri_chot=pos,
                        nhan_vien=nv,
                        ca_lam_viec=ca,
                        ngay_truc=current_date,
                    )

                    if current_date <= today:
                        start_std = datetime.combine(current_date, ca.gio_bat_dau)
                        end_std = datetime.combine(current_date, ca.gio_ket_thuc)

                        if self.make_aware_dt(start_std) > timezone.now():
                            continue
                        is_ongoing = (
                            current_date == today
                            and self.make_aware_dt(end_std) > timezone.now()
                        )

                        mt = pos.muc_tieu
                        lat_in, lng_in = self.jitter_gps(mt.vi_do, mt.kinh_do, meters=20)
                        lat_out, lng_out = self.jitter_gps(mt.vi_do, mt.kinh_do, meters=20)

                        pt_in = Point(lng_in, lat_in) if lat_in and lng_in else None
                        pt_out = Point(lng_out, lat_out) if lat_out and lng_out else None

                        ChamCong.objects.get_or_create(
                            ca_truc=pc,
                            defaults={
                                "thoi_gian_check_in": self.make_aware_dt(start_std),
                                "thoi_gian_check_out": None
                                if is_ongoing
                                else self.make_aware_dt(end_std),
                                "location_check_in": pt_in,
                                "location_check_out": pt_out if not is_ongoing else None,
                                "vi_tri_hop_le": True,
                                "ghi_chu": "Auto Seed",
                            },
                        )

    # --- 5. KHO & 6. WORKFLOW ---
    def seed_inventory(self, staff):
        LoaiVatTu.objects.get_or_create(ten_loai="Đồng phục")

    def seed_workflow(self, staff, targets, managers):
        if not targets:
            return
        BaoCaoSuCo.objects.create(
            tieu_de="Sự cố mẫu",
            muc_do="TB",
            nhan_vien_bao_cao=staff[0],
            muc_tieu=targets[0],
            thoi_gian_phat_hien=timezone.now(),
        )
<<<<<<< HEAD


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
