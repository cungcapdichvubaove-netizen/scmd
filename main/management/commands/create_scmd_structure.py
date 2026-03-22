# -*- coding: utf-8 -*-
"""
create_scmd_structure_improved.py
Cải tiến từ create_scmd_structure.py (gốc). Mục tiêu: idempotent, configurable, realistic demo users.
Tham chiếu file gốc: original create_scmd_structure.py. :contentReference[oaicite:10]{index=10}
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.utils.text import slugify
from users.models import PhongBan, ChucDanh, NhanVien, CauHinhMaNhanVien

DEFAULT_PASSWORD = "ScmdDemo2025!"  # DEV ONLY - allow CLI override

POSITION_BLOCKS = [
    ("Hội đồng Quản trị & Ban TGĐ", "BOARD", [
        ("Chủ tịch Hội đồng Quản trị", "chairman"),
        ("Tổng Giám đốc", "ceo"),
        ("Phó TGĐ Nghiệp vụ", "d_ceo_ops"),
    ]),
    ("Khối Nghiệp vụ An ninh", "OPS", [
        ("Giám đốc Nghiệp vụ", "ops_director"),
        ("Trưởng phòng Nghiệp vụ", "ops_manager"),
        ("Giám sát Khu vực", "supervisor"),
        ("Cán bộ Điều lệnh", "commander"),
        ("Cán bộ Đào tạo", "trainer"),
        ("Chỉ huy trưởng", "team_leader"),
        ("Nhân viên Bảo vệ", "guard"),
        ("Nhân viên Cơ động (IRT)", "irt"),
    ]),
    ("Trung tâm Giám sát 24/7", "MONITOR", [
        ("Trưởng ca trực 24/7", "monitor_lead"),
        ("Nhân viên Monitoring", "monitor_staff"),
    ]),
    ("Khối Kinh doanh & CSKH", "BIZ", [
        ("Giám đốc Kinh doanh", "sales_director"),
        ("Chuyên viên Kinh doanh", "sales_exec"),
        ("Chăm sóc Khách hàng", "client_care"),
    ]),
    ("Khối Văn phòng & Hậu cần", "BO", [
        ("Trưởng phòng Nhân sự", "hr_manager"),
        ("Chuyên viên Tuyển dụng", "recruiter"),
        ("Kế toán trưởng", "chief_accountant"),
        ("Kế toán lương", "payroll"),
        ("Hành chính - Kho", "admin_asset"),
        ("IT Support", "it_support"),
    ]),
]

def safe_username(base, maxlen=150):
    base = slugify(base).replace('-', '')
    if len(base) > maxlen - 5:
        base = base[: maxlen - 5]
    # if already taken, append random suffix (keeps idempotent behavior via get_or_create with same username)
    return base

class Command(BaseCommand):
    help = 'Khởi tạo cấu trúc tổ chức SCMD (idempotent, realistic demo users)'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Password cho user demo (DEV only)')
        parser.add_argument('--create-superuser', action='store_true', help='Tạo superuser demo admin')

    def handle(self, *args, **options):
        pwd = options['password']
        self.stdout.write(self.style.WARNING('🔨 ĐANG XÂY DỰNG CẤU TRÚC TỔ CHỨC SCMD (IMPROVED)...'))

        with transaction.atomic():
            # ensure config
            cfg, _ = CauHinhMaNhanVien.objects.get_or_create(tien_to="SCMD", defaults={'do_dai_so':4, 'so_hien_tai':0})
            self.stdout.write(f"  ➜ Config mã nhân viên: {cfg.tien_to}")

            for block_name, block_code, roles in POSITION_BLOCKS:
                pb, _ = PhongBan.objects.get_or_create(ten_phong_ban=block_name, defaults={'mo_ta': f"Mã khối: {block_code}"})
                for role_name, role_code in roles:
                    group_name = role_name
                    group, _ = Group.objects.get_or_create(name=group_name)
                    cd, _ = ChucDanh.objects.get_or_create(ten_chuc_danh=role_name, defaults={'nhom_quyen': group, 'mo_ta': f"Vị trí {role_code}"})

                    # build username based on block + role, ensure uniqueness via suffix index
                    base_user = f"{block_code.lower()}_{role_code}"
                    username = safe_username(base_user) 
                    # guarantee uniqueness deterministically: try suffixes
                    suffix = 0
                    uname = username
                    while User.objects.filter(username=uname).exists():
                        suffix += 1
                        uname = f"{username}{suffix}"
                    username = uname

                    user, created = User.objects.get_or_create(username=username, defaults={
                        'email': f"{username}@scmd.local",
                        'is_active': True,
                        'is_staff': True if 'director' in role_code or 'ceo' in role_code else False
                    })
                    if created:
                        user.set_password(pwd)
                        user.save()

                    # create or update NhanVien
                    nv_defaults = {
                        'ho_ten': f"[DEMO] {role_name}",
                        'phong_ban': pb,
                        'chuc_danh': cd,
                        'trang_thai_lam_viec': 'CHINHTHUC',
                        'sdt_chinh': f"09{random.randint(10000000,99999999)}"
                    }
                    NhanVien.objects.update_or_create(user=user, defaults=nv_defaults)

                    user.groups.add(group)

            if options['create_superuser']:
                admin_username = "admin_scmd"
                if not User.objects.filter(username=admin_username).exists():
                    admin = User.objects.create_superuser(username=admin_username, email="admin@scmd.local", password=pwd)
                    self.stdout.write(self.style.SUCCESS(f"✅ Superuser {admin_username} created."))
                else:
                    self.stdout.write(self.style.WARNING("⚠️ Superuser already exists."))

        self.stdout.write(self.style.SUCCESS('✅ HOÀN TẤT: CẤU TRÚC ĐÃ ĐƯỢC THIẾT LẬP.'))
