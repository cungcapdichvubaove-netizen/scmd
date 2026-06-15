# -*- coding: utf-8 -*-
"""Seed the KTC Việt Nam Security Group demo scenario for SCMD Pro.

The command intentionally stays inside the existing single-organization
architecture. Branches are represented as business units/regions in seeded data,
not as tenants, schemas, databases, or services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from itertools import cycle
import random
from typing import Iterable

from django.contrib.auth.models import Group, Permission, User
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rolepermissions.checkers import has_permission, has_role
from rolepermissions.roles import assign_role

from accounting.models import BangLuongThang, ChiTietLuong, KhoanKhauTruNhanVien, TamUngLuong
from clients.access_policies import SiteVisibilityPolicy
from clients.models import CoHoiKinhDoanh, HopDong, KhachHangTiemNang, MucTieu
from config.bootstrap_credentials import get_seed_password
from inspection.models import DiemTuanTra, GhiNhanTuanTra, LoaiTuanTra, LuotTuanTra
from inventory.models import ChiTietPhieuNhap, ChiTietPhieuXuat, LoaiVatTu, PhieuNhap, PhieuXuat, VatTu
from main.models import CompanyInfo
from operations.models import BaoCaoSuCo, CaLamViec, ChamCong, KiemTraQuanSo, PhanCongCaTruc, ViTriChot
from users.models import CauHinhMaNhanVien, ChucDanh, HopDongLaoDong, LichSuCongTac, NhanVien, PhongBan
from users.models_assignment import NhanVienRegionAssignment, Region


SCENARIO_CODE = "KTCVN"
SCENARIO_NAME = "KTC Việt Nam Security Group"
DEFAULT_SCENARIO_KEY = "ktc_viet_nam_security_group"
SUPPORTED_SCENARIO_KEYS = {DEFAULT_SCENARIO_KEY}
DEMO_PREFIX = "[DEMO-KTCVN]"
LEGACY_DEMO_PREFIXES = ("[DEMO-DNSG]",)
COMPANY_PROFILE = {
    "ten_cong_ty": "KTC VIỆT NAM PRO.,JSC",
    "ten_phap_ly": "CÔNG TY CỔ PHẦN DỊCH VỤ BẢO VỆ CHUYÊN NGHIỆP KTC VIỆT NAM",
    "ten_quoc_te": "KTC VIET NAM SECURITY SERVICES PROFESSIONAL JOINT STOCK COMPANY",
    "ma_so_thue": "0106004565",
    "dia_chi": "Số 67 đường Phan Đăng Lưu, Xã Phù Đổng, Thành phố Hà Nội, Việt Nam",
    "dia_chi_thue": "Số 67 đường Phan Đăng Lưu, Xã Phù Đổng, TP Hà Nội, Việt Nam",
    "dien_thoai": "02436983798",
    "nguoi_dai_dien": "NGUYỄN NGỌC THÀNH",
    "tinh_trang": "Đang hoạt động",
}
DEFAULT_PROFILE = "light"
DEFAULT_DEMO_PASSWORD = "Abcd@1234"
DEFAULT_GUARDS = 60
DEFAULT_DAYS = 21
DEFAULT_PAST_DAYS = 7


@dataclass(frozen=True)
class BranchSpec:
    key: str
    username_suffix: str
    guard_prefix: str
    employee_prefix: str
    label: str
    public_label: str
    guard_count: int
    site_count: int
    lat: float
    lng: float


BRANCHES: tuple[BranchSpec, ...] = (
    BranchSpec("hanoi", "hanoi", "hn", "HN", "Trụ sở Hà Nội", "Hà Nội / miền Bắc", 95, 16, 21.0278, 105.8342),
    BranchSpec("danang", "danang", "dn", "DN", "Chi nhánh Đà Nẵng", "Đà Nẵng / miền Trung", 45, 8, 16.0544, 108.2022),
    BranchSpec("saigon", "saigon", "sg", "SG", "Chi nhánh Sài Gòn", "Sài Gòn / miền Nam", 60, 11, 10.8231, 106.6297),
)


@dataclass(frozen=True)
class SeedProfile:
    key: str
    guards: int
    days: int
    past_days: int
    target_count: int
    incident_count: int
    headcount_checks: int
    inventory_issue_slips: int
    patrol_route_count: int
    patrol_record_cap: int
    payroll_periods: int
    description: str


PROFILE_SPECS: dict[str, SeedProfile] = {
    "light": SeedProfile(
        key="light",
        guards=60,
        days=21,
        past_days=7,
        target_count=24,
        incident_count=36,
        headcount_checks=72,
        inventory_issue_slips=16,
        patrol_route_count=12,
        patrol_record_cap=500,
        payroll_periods=1,
        description="Kịch bản nhẹ cho VM demo 1GB RAM + swap, đủ đa vai trò và đủ luồng nghiệp vụ.",
    ),
    "standard": SeedProfile(
        key="standard",
        guards=80,
        days=30,
        past_days=10,
        target_count=30,
        incident_count=60,
        headcount_checks=120,
        inventory_issue_slips=24,
        patrol_route_count=16,
        patrol_record_cap=800,
        payroll_periods=1,
        description="Kịch bản dày hơn cho demo dài hoặc VM từ 2GB RAM.",
    ),
    "full": SeedProfile(
        key="full",
        guards=200,
        days=45,
        past_days=15,
        target_count=35,
        incident_count=120,
        headcount_checks=300,
        inventory_issue_slips=35,
        patrol_route_count=20,
        patrol_record_cap=1500,
        payroll_periods=2,
        description="Kịch bản đầy đủ cho VM 4GB RAM+ hoặc benchmark nội bộ.",
    ),
}


ROLE_TO_GROUP_LABEL = {
    "ban_giam_doc": "Ban Giám đốc",
    "nhan_su": "Nhân sự",
    "ke_toan": "Kế toán",
    "thu_kho": "Kho vật tư",
    "nhan_vien_kinh_doanh": "Kinh doanh",
    "quan_ly_vung": "Quản lý vùng",
    "doi_truong": "Đội trưởng",
    "nhan_vien_bao_ve": "Nhân viên bảo vệ",
    "thanh_tra": "Thanh tra",
    "nghiep_vu": "Nghiệp vụ",
}


ROLE_PRIMARY_PERMISSIONS = {
    "ban_giam_doc": ("xem_dashboard_tong_the",),
    "nhan_su": ("xem_ho_so_nhan_su",),
    "ke_toan": ("xem_bang_luong_tong",),
    "thu_kho": ("xem_ton_kho",),
    "nhan_vien_kinh_doanh": ("quan_ly_khach_hang",),
    "quan_ly_vung": ("giao_ca_truc", "xem_so_truc_muc_tieu"),
    "doi_truong": ("giao_ca_truc", "xem_so_truc_muc_tieu"),
    "nhan_vien_bao_ve": ("xem_lich_truc_ca_nhan", "check_in_out"),
    "thanh_tra": ("lap_ke_hoach_thanh_tra",),
    "nghiep_vu": ("giao_ca_truc", "xem_so_truc_muc_tieu"),
}

SCHEDULE_MODEL_PERMISSIONS = (
    "operations.view_phancongcatruc",
    "operations.add_phancongcatruc",
    "operations.change_phancongcatruc",
    "operations.delete_phancongcatruc",
    "operations.view_chamcong",
    "operations.view_baocaosuco",
)

BRANCH_REGION_CODES = {
    "hanoi": "DEMO-KTCVN-HN",
    "danang": "DEMO-KTCVN-DN",
    "saigon": "DEMO-KTCVN-SG",
}

DASHBOARD_ACCOUNTS = [
    # username, full_name, title, department, rolepermissions role, staff flag, branch key/scope label
    ("tonggiamdoc.hanoi", "Nguyễn Minh Quân", "Tổng Giám đốc", "Ban Giám đốc", "ban_giam_doc", True, "hanoi"),
    ("phogiamdoc.vanhanh", "Trần Hữu Nam", "Phó Giám đốc Vận hành", "Phòng Vận hành Toàn quốc", "ban_giam_doc", True, "hanoi"),
    ("truongvanhanh.hanoi", "Phạm Đức Long", "Trưởng phòng Vận hành", "Phòng Vận hành Toàn quốc", "nghiep_vu", True, "hanoi"),
    ("dieuphoi.trungtam", "Lê Quốc Bảo", "Trực ban Trung tâm", "Trung tâm Điều phối", "nghiep_vu", False, "hanoi"),
    ("truongnhansu.hanoi", "Đỗ Thị Thanh Hà", "Trưởng phòng Nhân sự", "Phòng Nhân sự", "nhan_su", True, "hanoi"),
    ("nhansu.hanoi", "Vũ Thị Mai Anh", "Chuyên viên Nhân sự", "Phòng Nhân sự", "nhan_su", False, "hanoi"),
    ("ketoantruong.hanoi", "Hoàng Thị Thu Hương", "Kế toán trưởng", "Phòng Kế toán - Tài chính", "ke_toan", True, "hanoi"),
    ("luong.hanoi", "Nguyễn Thị Lan", "Chuyên viên Lương", "Phòng Kế toán - Tài chính", "ke_toan", False, "hanoi"),
    ("thukho.hanoi", "Bùi Văn Khánh", "Trưởng kho Tổng", "Kho Tổng Hà Nội", "thu_kho", True, "hanoi"),
    ("truongkinhdoanh.hanoi", "Đặng Anh Tuấn", "Trưởng phòng Kinh doanh", "Phòng Kinh doanh Toàn quốc", "nhan_vien_kinh_doanh", True, "hanoi"),
    ("thanhtra.hanoi", "Ngô Văn Sơn", "Trưởng phòng Kiểm tra chất lượng", "Phòng Kiểm tra chất lượng", "thanh_tra", True, "hanoi"),
    ("giamdocchinhanh.danang", "Nguyễn Văn Hải", "Giám đốc Chi nhánh Đà Nẵng", "Chi nhánh Đà Nẵng", "quan_ly_vung", True, "danang"),
    ("dieuphoi.danang", "Trần Văn Phúc", "Điều phối Chi nhánh Đà Nẵng", "Chi nhánh Đà Nẵng", "quan_ly_vung", False, "danang"),
    ("kinhdoanh.danang", "Lê Thị Kim Oanh", "Kinh doanh Chi nhánh Đà Nẵng", "Chi nhánh Đà Nẵng", "nhan_vien_kinh_doanh", False, "danang"),
    ("thukho.danang", "Phan Văn Lộc", "Kho Chi nhánh Đà Nẵng", "Chi nhánh Đà Nẵng", "thu_kho", False, "danang"),
    ("chihuy.dn01", "Võ Minh Trí", "Chỉ huy mục tiêu Đà Nẵng 01", "Chi nhánh Đà Nẵng", "doi_truong", False, "danang"),
    ("giamdocchinhanh.saigon", "Trần Quốc Việt", "Giám đốc Chi nhánh Sài Gòn", "Chi nhánh Sài Gòn", "quan_ly_vung", True, "saigon"),
    ("dieuphoi.saigon", "Nguyễn Hữu Phát", "Điều phối Chi nhánh Sài Gòn", "Chi nhánh Sài Gòn", "quan_ly_vung", False, "saigon"),
    ("kinhdoanh.saigon", "Mai Thị Ngọc Diệp", "Kinh doanh Chi nhánh Sài Gòn", "Chi nhánh Sài Gòn", "nhan_vien_kinh_doanh", False, "saigon"),
    ("thukho.saigon", "Lâm Văn Tài", "Kho Chi nhánh Sài Gòn", "Chi nhánh Sài Gòn", "thu_kho", False, "saigon"),
    ("chihuy.sg01", "Huỳnh Thanh Dũng", "Chỉ huy mục tiêu Sài Gòn 01", "Chi nhánh Sài Gòn", "doi_truong", False, "saigon"),
]

CLIENT_NAMES = [
    ("Công ty TNHH Sakura Manufacturing Việt Nam", "Nhà máy"),
    ("Công ty CP Khu công nghiệp Đại An", "Khu công nghiệp"),
    ("Capital Tower Hà Nội", "Tòa nhà văn phòng"),
    ("Lotus Office Center", "Tòa nhà văn phòng"),
    ("An Phú Residence", "Chung cư"),
    ("Green City Residence", "Chung cư"),
    ("Mekong Logistics", "Kho logistics"),
    ("Bắc Việt Warehouse", "Kho logistics"),
    ("Bệnh viện Minh Tâm", "Bệnh viện"),
    ("Trường Quốc tế Đông Á", "Trường học"),
    ("Ngân hàng Đông Dương", "Ngân hàng"),
    ("AutoWorld Showroom", "Showroom"),
    ("Bệnh viện Hải Châu", "Bệnh viện"),
    ("KCN Hòa Khánh", "Khu công nghiệp"),
    ("Đà Nẵng Riverside Tower", "Tòa nhà văn phòng"),
    ("Kho Logistics Cát Lái", "Kho logistics"),
    ("Nam Sài Gòn Plaza", "Trung tâm thương mại"),
    ("Khu đô thị Phú Mỹ Hưng", "Khu đô thị"),
]

POST_TEMPLATES = {
    "Nhà máy": ("Cổng chính", "Cổng phụ", "Kho nguyên liệu", "Kho thành phẩm", "Tuần tra hàng rào"),
    "Khu công nghiệp": ("Cổng số 1", "Cổng số 2", "Trạm cân", "Tuần tra nội khu", "Nhà điều hành"),
    "Tòa nhà văn phòng": ("Sảnh lễ tân", "Hầm xe B1", "Phòng camera", "Tuần tra tầng", "Cổng giao nhận"),
    "Chung cư": ("Sảnh chính", "Hầm xe", "Cổng cư dân", "Tuần tra tầng", "Phòng camera"),
    "Kho logistics": ("Cổng xe tải", "Kho hàng", "Bãi container", "Văn phòng kho", "Tuần tra hàng rào"),
    "Bệnh viện": ("Cổng chính", "Khu cấp cứu", "Nhà xe", "Sảnh tiếp đón", "Tuần tra khuôn viên"),
    "Trường học": ("Cổng trường", "Sân trường", "Nhà xe", "Khu hành chính", "Tuần tra lớp học"),
    "Ngân hàng": ("Sảnh giao dịch", "Cửa ATM", "Phòng camera", "Bãi xe"),
    "Showroom": ("Sảnh showroom", "Bãi xe", "Kho phụ tùng", "Phòng camera"),
    "Trung tâm thương mại": ("Sảnh chính", "Hầm xe", "Cửa giao nhận", "Phòng camera", "Tuần tra tầng"),
    "Khu đô thị": ("Cổng chính", "Cổng phụ", "Nhà sinh hoạt", "Tuần tra nội khu", "Phòng camera"),
}

SURNAME = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
MIDDLE = ["Văn", "Hữu", "Đức", "Minh", "Quốc", "Thành", "Thanh", "Xuân", "Công", "Anh"]
GIVEN = ["An", "Bình", "Cường", "Dũng", "Hải", "Hùng", "Khánh", "Long", "Nam", "Phúc", "Quang", "Sơn", "Thắng", "Tú", "Việt", "Vinh"]


def _demo_note(*parts: str) -> str:
    return " | ".join([DEMO_PREFIX, *[p for p in parts if p]])


class Command(BaseCommand):
    help = "Seed demo scenario KTC Việt Nam Security Group: HQ Hà Nội, branches Đà Nẵng/Sài Gòn, optimized for staging demo."

    def add_arguments(self, parser):
        parser.add_argument("--scenario", default=DEFAULT_SCENARIO_KEY, help="Scenario key. Use ktc_viet_nam_security_group.")
        parser.add_argument("--profile", choices=sorted(PROFILE_SPECS), default=DEFAULT_PROFILE, help="Seed scale profile. Default: light for the current demo VM.")
        parser.add_argument("--guards", type=int, default=None, help="Override total guards. Default comes from --profile; light=60.")
        parser.add_argument("--days", type=int, default=None, help="Override schedule window in days. Default comes from --profile; light=21.")
        parser.add_argument("--past-days", type=int, default=None, help="Override number of past days with attendance history. Default comes from --profile; light=7.")
        parser.add_argument("--password", default=None, help="Password for demo users. Default: staging demo password; can be overridden for private demos.")
        parser.add_argument("--create-admin", action="store_true", help="Create/synchronize demo superuser 'admin'.")
        parser.add_argument("--reset-demo", action="store_true", help="Delete previous DEMO-KTCVN data before seeding.")
        parser.add_argument("--update-company-info", action="store_true", help="Update an existing non-demo CompanyInfo profile with the KTC demo legal profile. Default only updates empty/default/demo profiles.")
        parser.add_argument("--confirm-reset", action="store_true", help="Required together with --reset-demo.")
        parser.add_argument("--dry-run", action="store_true", help="Print the seed plan without writing data.")

    def handle(self, *args, **options):
        scenario_key = options["scenario"]
        if scenario_key not in SUPPORTED_SCENARIO_KEYS:
            raise CommandError("Only --scenario ktc_viet_nam_security_group is supported.")

        profile = PROFILE_SPECS[options["profile"]]
        options["guards"] = profile.guards if options["guards"] is None else options["guards"]
        options["days"] = profile.days if options["days"] is None else options["days"]
        options["past_days"] = profile.past_days if options["past_days"] is None else options["past_days"]
        self.profile = profile
        self._verification_errors = []

        if options["guards"] < len(BRANCHES):
            raise CommandError(f"--guards must be >= {len(BRANCHES)} to keep all branches represented.")
        if options["days"] < 1 or options["past_days"] < 0:
            raise CommandError("--days must be >= 1 and --past-days must be >= 0.")
        if options["dry_run"]:
            self._print_plan(options)
            return

        password = options["password"]
        if not password:
            try:
                password = get_seed_password()
            except RuntimeError:
                password = DEFAULT_DEMO_PASSWORD

        random.seed(20260615)
        started = timezone.now()
        with transaction.atomic():
            if options["reset_demo"]:
                if not options["confirm_reset"]:
                    raise CommandError("--reset-demo requires --confirm-reset to avoid accidental data deletion.")
                self._reset_demo_data()

            if options["create_admin"]:
                self._create_admin(password)

            self._seed_company_profile(force=options["update_company_info"])
            refs = self._seed_structure()
            named_staff = self._seed_named_dashboard_users(refs, password)
            guards = self._seed_guards(refs, password, total_guards=options["guards"])
            self._seed_labor_contracts(list(named_staff.values()) + guards, named_staff)
            clients = self._seed_clients_and_contracts(named_staff)
            sites = self._seed_sites(clients, named_staff, refs)
            self._seed_region_assignments(refs, named_staff)
            shifts = self._seed_shifts()
            posts = self._seed_posts(sites)
            assignments = self._seed_assignments(guards, posts, shifts, days=options["days"], past_days=options["past_days"])
            self._seed_current_work_history(assignments, named_staff, sites, start_day=timezone.localdate() - timedelta(days=options["past_days"]))
            self._seed_attendance(assignments, past_days=options["past_days"])
            self._seed_patrols(sites, assignments)
            self._seed_incidents(assignments, named_staff)
            self._seed_inventory(named_staff, sites)
            self._seed_payroll(guards, named_staff)
            self._verify_demo_access_contract(named_staff, guards, sites)
            if self._verification_errors:
                raise CommandError("Demo seed verification failed:\n- " + "\n- ".join(self._verification_errors))

        elapsed = (timezone.now() - started).total_seconds()
        self.stdout.write(self.style.SUCCESS(f"Seed scenario {SCENARIO_NAME} profile={self.profile.key} completed in {elapsed:.1f}s."))
        self.stdout.write(self.style.SUCCESS("Demo users use Vietnamese usernames without accents. Default staging password is configured but not printed."))

    def _print_plan(self, options):
        profile = PROFILE_SPECS[options["profile"]]
        site_plan = self._allocate_sites(profile.target_count)
        self.stdout.write(self.style.HTTP_INFO(f"Scenario: {SCENARIO_NAME}"))
        self.stdout.write(f"  Profile: {profile.key} - {profile.description}")
        self.stdout.write(f"  Branches: {', '.join(branch.label for branch in BRANCHES)}")
        self.stdout.write(f"  Guards: {options['guards']} / Schedule days: {options['days']} / Past attendance days: {options['past_days']}")
        self.stdout.write(f"  Targets: {profile.target_count} ({site_plan}) / Incidents: {profile.incident_count} / Headcount checks: {profile.headcount_checks}")
        self.stdout.write(f"  Inventory issue slips: {profile.inventory_issue_slips} / Patrol routes: {profile.patrol_route_count} / Patrol records cap: {profile.patrol_record_cap}")
        self.stdout.write("  Demo password: default staging password is configured; value is intentionally not printed.")
        self.stdout.write("  Named dashboard accounts:")
        for username, _full_name, title, _department, role, _staff, branch_key in DASHBOARD_ACCOUNTS:
            self.stdout.write(f"    - {username:28s} {title} ({branch_key}, role={role})")

    def _create_admin(self, password):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@scmd.local", "is_active": True, "is_staff": True, "is_superuser": True},
        )
        admin.email = "admin@scmd.local"
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(password)
        admin.save()

    def _seed_company_profile(self, *, force: bool = False):
        """Seed CompanyInfo as SSOT for reports/contracts without unsafe overwrite."""
        values = {
            "ten_cong_ty": COMPANY_PROFILE["ten_cong_ty"],
            "ten_phap_ly": COMPANY_PROFILE["ten_phap_ly"],
            "ma_so_thue": COMPANY_PROFILE["ma_so_thue"],
            "dia_chi": COMPANY_PROFILE["dia_chi"],
            "dien_thoai": COMPANY_PROFILE["dien_thoai"],
            "hotline": COMPANY_PROFILE["dien_thoai"],
            "nguoi_dai_dien": COMPANY_PROFILE["nguoi_dai_dien"],
            "chuc_vu_nguoi_dai_dien": "Người đại diện theo pháp luật",
            "ghi_chu": _demo_note(
                "Hồ sơ pháp nhân demo KTC Việt Nam",
                f"Tên quốc tế: {COMPANY_PROFILE['ten_quoc_te']}",
                f"Địa chỉ thuế: {COMPANY_PROFILE['dia_chi_thue']}",
                f"Tình trạng: {COMPANY_PROFILE['tinh_trang']}",
                "Chi nhánh Đà Nẵng/Sài Gòn trong scenario là đơn vị nghiệp vụ nội bộ, không phải tenant riêng.",
            ),
        }
        profile = CompanyInfo.objects.first()
        if profile is None:
            CompanyInfo.objects.create(**values)
            return

        safe_to_update = (
            force
            or profile.ma_so_thue == COMPANY_PROFILE["ma_so_thue"]
            or str(profile.ten_cong_ty).startswith("CÔNG TY DỊCH VỤ BẢO VỆ SCMD")
            or str(profile.ten_cong_ty).startswith(COMPANY_PROFILE["ten_cong_ty"])
            or DEMO_PREFIX in (profile.ghi_chu or "")
            or any(prefix in (profile.ghi_chu or "") for prefix in LEGACY_DEMO_PREFIXES)
        )
        if not safe_to_update:
            self.stdout.write(
                self.style.WARNING(
                    "Skip CompanyInfo update because an existing non-demo company profile is present. "
                    "Use --update-company-info only in an isolated demo/staging database."
                )
            )
            return

        for field, value in values.items():
            setattr(profile, field, value)
        profile.save(update_fields=[*values.keys(), "updated_at"])

    def _seed_structure(self):
        departments = {}
        positions = {}
        groups = {}

        department_names = {
            "bod": "Ban Giám đốc",
            "ops_hq": "Phòng Vận hành Toàn quốc",
            "control": "Trung tâm Điều phối",
            "hr": "Phòng Nhân sự",
            "acc": "Phòng Kế toán - Tài chính",
            "warehouse_hq": "Kho Tổng Hà Nội",
            "sales_hq": "Phòng Kinh doanh Toàn quốc",
            "qa": "Phòng Kiểm tra chất lượng",
            "danang": "Chi nhánh Đà Nẵng",
            "saigon": "Chi nhánh Sài Gòn",
            "guard": "Khối Bảo vệ Hiện trường",
        }
        position_names = [
            "Tổng Giám đốc",
            "Phó Giám đốc Vận hành",
            "Trưởng phòng Vận hành",
            "Trực ban Trung tâm",
            "Trưởng phòng Nhân sự",
            "Chuyên viên Nhân sự",
            "Kế toán trưởng",
            "Chuyên viên Lương",
            "Trưởng kho Tổng",
            "Trưởng phòng Kinh doanh",
            "Trưởng phòng Kiểm tra chất lượng",
            "Giám đốc Chi nhánh Đà Nẵng",
            "Điều phối Chi nhánh Đà Nẵng",
            "Kinh doanh Chi nhánh Đà Nẵng",
            "Kho Chi nhánh Đà Nẵng",
            "Chỉ huy mục tiêu Đà Nẵng 01",
            "Giám đốc Chi nhánh Sài Gòn",
            "Điều phối Chi nhánh Sài Gòn",
            "Kinh doanh Chi nhánh Sài Gòn",
            "Kho Chi nhánh Sài Gòn",
            "Chỉ huy mục tiêu Sài Gòn 01",
            "Quản lý vùng",
            "Chỉ huy mục tiêu",
            "Ca trưởng",
            "Nhân viên cơ động",
            "Nhân viên bảo vệ",
        ]

        for role, group_label in ROLE_TO_GROUP_LABEL.items():
            groups[role], _ = Group.objects.get_or_create(name=group_label)

        for key, name in department_names.items():
            # Demo seed must not rewrite existing organization reference data.
            # If a real department/title already exists, reuse it as-is.
            departments[key], _ = PhongBan.objects.get_or_create(
                ten_phong_ban=name,
                defaults={"mo_ta": _demo_note("Đơn vị seed demo", name)},
            )

        for name in position_names:
            group = self._group_for_position(name, groups)
            position, created = ChucDanh.objects.get_or_create(
                ten_chuc_danh=name,
                defaults={"mo_ta": _demo_note("Chức danh seed demo"), "nhom_quyen": group},
            )
            # Idempotency for v1 demo data: correct only reference rows that
            # were created by this demo seed. Do not rewrite shared production
            # titles that happen to have the same Vietnamese name.
            if not created and DEMO_PREFIX in (position.mo_ta or "") and position.nhom_quyen_id != group.id:
                position.nhom_quyen = group
                position.save(update_fields=["nhom_quyen"])
            positions[name] = position

        regions = {}
        for branch in BRANCHES:
            regions[branch.key], _ = Region.objects.update_or_create(
                ma_vung=BRANCH_REGION_CODES[branch.key],
                defaults={
                    "ten_vung": f"{DEMO_PREFIX} {branch.public_label}",
                    "mo_ta": _demo_note("Vùng vận hành demo", branch.label),
                },
            )

        CauHinhMaNhanVien.objects.get_or_create(tien_to="KTCVN", defaults={"do_dai_so": 4, "so_hien_tai": 0})
        return {"departments": departments, "positions": positions, "groups": groups, "regions": regions}

    def _group_for_position(self, name: str, groups: dict[str, Group]):
        lowered = name.lower()
        if "giám đốc chi nhánh" in lowered:
            return groups["quan_ly_vung"]
        if "tổng giám" in lowered or "phó giám đốc" in lowered or "ban giám" in lowered:
            return groups["ban_giam_doc"]
        if "nhân sự" in lowered:
            return groups["nhan_su"]
        if "lương" in lowered or "kế toán" in lowered:
            return groups["ke_toan"]
        if "kho" in lowered:
            return groups["thu_kho"]
        if "kinh doanh" in lowered:
            return groups["nhan_vien_kinh_doanh"]
        if "chỉ huy" in lowered or "ca trưởng" in lowered:
            return groups["doi_truong"]
        if "bảo vệ" in lowered or "cơ động" in lowered:
            return groups["nhan_vien_bao_ve"]
        if "thanh tra" in lowered or "kiểm tra" in lowered:
            return groups["thanh_tra"]
        return groups["nghiep_vu"]

    def _seed_named_dashboard_users(self, refs, password):
        result = {}
        for idx, (username, full_name, title, department, role, is_staff, branch_key) in enumerate(DASHBOARD_ACCOUNTS, start=1):
            user = self._upsert_user(username, password, is_staff=is_staff, email=f"{username}@demo.scmd.local")
            employee_code = f"KTCVN-QL-{idx:03d}"
            department_obj = self._department_for_label(refs, department, branch_key)
            position_obj = refs["positions"][title]
            employee, _ = NhanVien.objects.update_or_create(
                user=user,
                defaults={
                    "ma_nhan_vien": employee_code,
                    "user": user,
                    "ho_ten": full_name,
                    "phong_ban": department_obj,
                    "chuc_danh": position_obj,
                    "sdt_chinh": f"09{idx:08d}"[-10:],
                    "email": f"{username}@demo.scmd.local",
                    "ngay_vao_lam": timezone.localdate() - timedelta(days=900 + idx),
                    "trang_thai_lam_viec": NhanVien.TrangThaiLamViec.CHINH_THUC,
                    "dia_chi_tam_tru": f"{DEMO_PREFIX} {department}",
                },
            )
            self._assign_business_role(user, role)
            if user.is_staff != is_staff:
                user.is_staff = is_staff
                user.save(update_fields=["is_staff"])
            result[username] = employee
        return result

    def _department_for_label(self, refs, department: str, branch_key: str):
        if department == "Chi nhánh Đà Nẵng":
            return refs["departments"]["danang"]
        if department == "Chi nhánh Sài Gòn":
            return refs["departments"]["saigon"]
        mapping = {
            "Ban Giám đốc": "bod",
            "Phòng Vận hành Toàn quốc": "ops_hq",
            "Trung tâm Điều phối": "control",
            "Phòng Nhân sự": "hr",
            "Phòng Kế toán - Tài chính": "acc",
            "Kho Tổng Hà Nội": "warehouse_hq",
            "Phòng Kinh doanh Toàn quốc": "sales_hq",
            "Phòng Kiểm tra chất lượng": "qa",
        }
        return refs["departments"].get(mapping.get(department, branch_key), refs["departments"].get(branch_key, refs["departments"]["guard"]))

    def _seed_guards(self, refs, password, total_guards: int):
        guards = []
        branch_plan = self._allocate_guards(total_guards)
        sequence_global = 0
        for branch in BRANCHES:
            count = branch_plan[branch.key]
            for i in range(1, count + 1):
                sequence_global += 1
                username = f"baove.{branch.guard_prefix}{i:03d}"
                user = self._upsert_user(username, password, is_staff=False, email=f"{username}@demo.scmd.local")
                full_name = self._demo_person_name(sequence_global)
                employee_code = f"KTCVN-{branch.employee_prefix}-BV{i:03d}"
                employee, _ = NhanVien.objects.update_or_create(
                    user=user,
                    defaults={
                        "ma_nhan_vien": employee_code,
                        "user": user,
                        "ho_ten": full_name,
                        "phong_ban": refs["departments"]["guard"],
                        "chuc_danh": refs["positions"]["Nhân viên bảo vệ"],
                        "sdt_chinh": f"08{sequence_global:08d}"[-10:],
                        "email": f"{username}@demo.scmd.local",
                        "ngay_vao_lam": timezone.localdate() - timedelta(days=120 + sequence_global),
                        "trang_thai_lam_viec": self._guard_status(sequence_global),
                        "dia_chi_tam_tru": f"{DEMO_PREFIX} {branch.public_label}",
                    },
                )
                self._assign_business_role(user, "nhan_vien_bao_ve")
                if user.is_staff:
                    user.is_staff = False
                    user.save(update_fields=["is_staff"])
                employee._demo_branch_key = branch.key
                employee._demo_branch = branch
                guards.append(employee)
        return guards

    def _allocate_guards(self, total_guards: int) -> dict[str, int]:
        base_total = sum(branch.guard_count for branch in BRANCHES)
        allocated = {branch.key: max(1, int(total_guards * branch.guard_count / base_total)) for branch in BRANCHES}
        remainder = total_guards - sum(allocated.values())
        for branch in BRANCHES[:remainder]:
            allocated[branch.key] += 1
        return allocated

    def _allocate_sites(self, total_sites: int) -> dict[str, int]:
        base_total = sum(branch.site_count for branch in BRANCHES)
        allocated = {branch.key: max(1, int(total_sites * branch.site_count / base_total)) for branch in BRANCHES}
        remainder = total_sites - sum(allocated.values())
        for branch in BRANCHES[:remainder]:
            allocated[branch.key] += 1
        return allocated

    def _upsert_user(self, username: str, password: str, *, is_staff: bool, email: str) -> User:
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_active": True, "is_staff": is_staff, "is_superuser": False},
        )
        user.email = email
        user.is_active = True
        user.is_staff = is_staff
        if not user.is_superuser:
            user.is_superuser = False
        user.set_password(password)
        user.save()
        return user

    def _assign_business_role(self, user: User, role: str):
        try:
            assign_role(user, role)
        except Exception as exc:
            message = f"assign_role({user.username}, {role}) failed: {exc.__class__.__name__}: {exc}"
            self._verification_errors.append(message)
            raise CommandError(message) from exc

        group_label = ROLE_TO_GROUP_LABEL.get(role)
        if group_label:
            demo_role_group_names = list(ROLE_TO_GROUP_LABEL.values())
            user.groups.remove(*Group.objects.filter(name__in=demo_role_group_names).exclude(name=group_label))
            group, _ = Group.objects.get_or_create(name=group_label)
            user.groups.add(group)
        self._grant_minimal_model_permissions(user, role)
        self._verify_assigned_role_permissions(user, role)

    def _verify_assigned_role_permissions(self, user: User, role: str):
        user.refresh_from_db()
        if not has_role(user, role):
            self._verification_errors.append(f"{user.username}: has_role({role}) returned False after assign_role")
        for permission_key in ROLE_PRIMARY_PERMISSIONS.get(role, ()):
            if not has_permission(user, permission_key):
                self._verification_errors.append(f"{user.username}: missing role permission {permission_key}")

    def _grant_minimal_model_permissions(self, user: User, role: str):
        schedule_perms = list(SCHEDULE_MODEL_PERMISSIONS)
        perms_by_role = {
            "nhan_vien_kinh_doanh": [
                "clients.view_khachhangtiemnang", "clients.add_khachhangtiemnang", "clients.change_khachhangtiemnang",
                "clients.view_cohoikinhdoanh", "clients.add_cohoikinhdoanh", "clients.change_cohoikinhdoanh",
                "clients.view_hopdong", "clients.add_hopdong", "clients.change_hopdong",
            ],
            "thu_kho": [
                "inventory.view_vattu", "inventory.view_loaivattu",
                "inventory.view_congcutaimuctieu",
                "inventory.add_phieuxuat", "inventory.view_phieuxuat", "inventory.change_phieuxuat",
                "inventory.add_phieunhap", "inventory.view_phieunhap", "inventory.change_phieunhap",
                "inventory.add_phieuthuhoi", "inventory.view_phieuthuhoi", "inventory.change_phieuthuhoi",
            ],
            "nhan_su": [
                "users.view_nhanvien", "users.add_nhanvien", "users.change_nhanvien",
                "users.view_hopdonglaodong", "users.add_hopdonglaodong", "users.change_hopdonglaodong",
                "users.view_donnghiphep", "users.add_donnghiphep", "users.change_donnghiphep",
                "users.view_quyetdinhnghiviec",
            ],
            "ke_toan": [
                "accounting.view_bangluongthang", "accounting.change_bangluongthang",
                "accounting.view_chitietluong",
                "accounting.add_tamungluong", "accounting.view_tamungluong", "accounting.change_tamungluong",
                "accounting.add_khoankhautrunhanvien", "accounting.view_khoankhautrunhanvien", "accounting.change_khoankhautrunhanvien",
            ],
            "nghiep_vu": [*schedule_perms, "clients.view_muctieu"],
            "quan_ly_vung": [*schedule_perms, "clients.view_muctieu"],
            "doi_truong": [*schedule_perms, "clients.view_muctieu"],
            # Product decision for demo seed: BGĐ sees the weekly schedule but does not mutate it.
            "ban_giam_doc": ["clients.view_hopdong", "clients.view_muctieu", "operations.view_phancongcatruc", "operations.view_chamcong", "operations.view_baocaosuco", "accounting.view_bangluongthang", "inventory.view_vattu", "users.view_nhanvien"],
            "thanh_tra": [
                "inspection.view_dotthanhtra", "inspection.add_dotthanhtra", "inspection.change_dotthanhtra",
                "inspection.view_bienbanthanhtra", "inspection.add_bienbanthanhtra", "inspection.change_bienbanthanhtra",
                "inspection.view_bienbanvipham", "inspection.add_bienbanvipham", "inspection.change_bienbanvipham",
                "inspection.view_buoihuanluyen", "inspection.add_buoihuanluyen", "inspection.change_buoihuanluyen",
                "inspection.view_loaituantra", "inspection.view_ghinhantuantra",
                "operations.view_baocaosuco",
            ],
        }
        for perm_code in perms_by_role.get(role, []):
            app_label, codename = perm_code.split(".", 1)
            permission = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if permission:
                user.user_permissions.add(permission)
            else:
                self._verification_errors.append(f"{user.username}: Django permission not found: {perm_code}")

    def _demo_person_name(self, sequence: int) -> str:
        return f"{SURNAME[sequence % len(SURNAME)]} {MIDDLE[sequence % len(MIDDLE)]} {GIVEN[sequence % len(GIVEN)]}"

    def _guard_status(self, sequence: int) -> str:
        if sequence in {18, 77, 141}:
            return NhanVien.TrangThaiLamViec.THU_VIEC
        if sequence in {199, 200}:
            return NhanVien.TrangThaiLamViec.TAM_HOAN
        return NhanVien.TrangThaiLamViec.CHINH_THUC


    def _seed_labor_contracts(self, employees, named_staff):
        today = timezone.localdate()
        hr_approver = named_staff.get("truongnhansu.hanoi")
        for idx, employee in enumerate(employees, start=1):
            expiring = idx in {7, 18, 31, 44, 58, 79, 101, 143}
            terminated = idx in {len(employees) - 1, len(employees)}
            status = HopDongLaoDong.TrangThai.TERMINATED if terminated else HopDongLaoDong.TrangThai.EXPIRING if expiring else HopDongLaoDong.TrangThai.ACTIVE
            effective = today - timedelta(days=365 + idx)
            end_date = today + timedelta(days=20 + idx % 7) if expiring else today + timedelta(days=365 - idx % 90)
            if terminated:
                end_date = today - timedelta(days=idx % 12 + 1)
            HopDongLaoDong.objects.update_or_create(
                so_hop_dong=f"DEMO-KTCVN-HDLD-{idx:04d}",
                defaults={
                    "nhan_vien": employee,
                    "loai_hop_dong": NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN,
                    "ngay_ky": effective - timedelta(days=3),
                    "ngay_hieu_luc": effective,
                    "ngay_het_han": end_date,
                    "trang_thai": status,
                    "muc_luong_co_ban": Decimal(7_500_000),
                    "phu_cap": Decimal(500_000 if idx % 5 == 0 else 0),
                    "nguon_ho_so": HopDongLaoDong.NguonHoSo.HR_ADMIN,
                    "nguoi_duyet": hr_approver.user if hr_approver and hr_approver.user_id else None,
                    "ngay_duyet": timezone.now(),
                    "ghi_chu": _demo_note("Hợp đồng lao động demo", employee.ma_nhan_vien),
                },
            )

    def _seed_clients_and_contracts(self, named_staff):
        sales_staff = {
            "hanoi": named_staff["truongkinhdoanh.hanoi"],
            "danang": named_staff["kinhdoanh.danang"],
            "saigon": named_staff["kinhdoanh.saigon"],
        }
        clients_by_branch = {branch.key: [] for branch in BRANCHES}
        client_cycle = cycle(CLIENT_NAMES)
        for branch in BRANCHES:
            client_count = 7 if branch.key == "hanoi" else 5 if branch.key == "danang" else 6
            for i in range(1, client_count + 1):
                client_name, sector = next(client_cycle)
                kh, _ = KhachHangTiemNang.objects.update_or_create(
                    ten_cong_ty=f"{DEMO_PREFIX} {client_name} - {branch.public_label}",
                    defaults={
                        "nguoi_lien_he": f"Đầu mối {branch.public_label}",
                        "sdt": f"07{len(clients_by_branch[branch.key]) + i:08d}"[-10:],
                        "email": f"khachhang.{branch.guard_prefix}{i}@demo.scmd.local",
                        "dia_chi": f"{branch.public_label} - dữ liệu demo {sector}",
                        "nguon": "GIOI_THIEU",
                        "trang_thai": "CHOT_HOP_DONG" if i <= client_count - 1 else "BAO_GIA",
                        "ghi_chu": _demo_note("Khách hàng demo", branch.label, sector),
                    },
                )
                clients_by_branch[branch.key].append((kh, sector, sales_staff[branch.key]))
        return clients_by_branch

    def _seed_sites(self, clients_by_branch, named_staff, refs):
        sites = []
        branch_site_counter = {branch.key: 0 for branch in BRANCHES}
        site_total = 0
        site_plan = self._allocate_sites(self.profile.target_count)
        for branch in BRANCHES:
            regional_manager = named_staff.get(f"giamdocchinhanh.{branch.username_suffix}") or named_staff["truongvanhanh.hanoi"]
            client_specs = clients_by_branch[branch.key]
            for i in range(1, site_plan[branch.key] + 1):
                kh, sector, sales_staff = client_specs[(i - 1) % len(client_specs)]
                site_total += 1
                branch_site_counter[branch.key] += 1
                opp, _ = CoHoiKinhDoanh.objects.update_or_create(
                    ten_co_hoi=f"{DEMO_PREFIX} Gói bảo vệ {sector} {branch.public_label} {i:02d}",
                    khach_hang_tiem_nang=kh,
                    defaults={
                        "gia_tri_uoc_tinh": Decimal(120_000_000 + i * 5_000_000),
                        "trang_thai": CoHoiKinhDoanh.TrangThai.THANH_CONG,
                        "nguoi_phu_trach": sales_staff,
                        "region": refs["regions"].get(branch.key),
                    },
                )
                contract, _ = HopDong.objects.update_or_create(
                    so_hop_dong=f"DEMO-KTCVN-{branch.employee_prefix}-HD{i:03d}",
                    defaults={
                        "co_hoi": opp,
                        "khach_hang_cu": kh,
                        "ngay_ky": timezone.localdate() - timedelta(days=120 + i),
                        "ngay_hieu_luc": timezone.localdate() - timedelta(days=90 + i),
                        "ngay_het_han": timezone.localdate() + timedelta(days=280 - i),
                        "gia_tri": Decimal(95_000_000 + i * 3_500_000),
                        "trang_thai": "SAP_HET_HAN" if i in {2, 5, 9} else "HIEU_LUC",
                    },
                )
                site_name = f"{DEMO_PREFIX} {sector} {branch.public_label} {i:02d}"
                site, _ = MucTieu.objects.update_or_create(
                    ten_muc_tieu=site_name,
                    defaults={
                        "hop_dong": contract,
                        "dia_chi": f"{branch.public_label} - địa chỉ mục tiêu demo số {i}",
                        "vi_do": round(branch.lat + (i * 0.004), 6),
                        "kinh_do": round(branch.lng + (i * 0.004), 6),
                        "ban_kinh_cho_phep": 120,
                        "luong_khoan_bao_ve": Decimal(7_500_000),
                        "so_gio_mot_ngay": Decimal("12.00"),
                        "tien_chuyen_can": Decimal(1_000_000),
                        "nguoi_lien_he": "Đại diện khách hàng demo",
                        "sdt_lien_he": f"06{site_total:08d}"[-10:],
                        "so_luong_nhan_vien": self._site_headcount(branch.key, i),
                        "quan_ly_muc_tieu": self._site_commander_for(branch.key, i, named_staff),
                        "quan_ly_vung": regional_manager,
                    },
                )
                site._demo_branch_key = branch.key
                site._demo_sector = sector
                sites.append(site)
        return sites

    def _site_commander_for(self, branch_key: str, site_index: int, named_staff):
        if branch_key == "danang" and site_index == 1:
            return named_staff.get("chihuy.dn01")
        if branch_key == "saigon" and site_index == 1:
            return named_staff.get("chihuy.sg01")
        if branch_key == "hanoi":
            return named_staff.get("truongvanhanh.hanoi")
        return None

    def _seed_region_assignments(self, refs, named_staff):
        today = timezone.localdate()
        NhanVienRegionAssignment.objects.filter(
            nhan_vien__in=list(named_staff.values()),
            reason__contains=DEMO_PREFIX,
        ).delete()
        # NhanVienRegionAssignment is intentionally one-active-region per staff.
        # Branch managers/operators get their branch. Central operations users
        # (Phòng Vận hành Toàn quốc / Trung tâm Điều phối) resolve nationwide
        # scope through RegionVisibilityPolicy, not through fake overlapping
        # per-region assignment rows.
        assignments_by_username = {
            "giamdocchinhanh.danang": [refs["regions"]["danang"]],
            "dieuphoi.danang": [refs["regions"]["danang"]],
            "giamdocchinhanh.saigon": [refs["regions"]["saigon"]],
            "dieuphoi.saigon": [refs["regions"]["saigon"]],
        }
        for username, regions in assignments_by_username.items():
            staff = named_staff.get(username)
            if staff is None:
                continue
            for region in regions:
                assignment, _ = NhanVienRegionAssignment.objects.update_or_create(
                    nhan_vien=staff,
                    region=region,
                    starts_at=today - timedelta(days=365),
                    defaults={
                        "ends_at": None,
                        "status": NhanVienRegionAssignment.Status.ACTIVE,
                        "assigned_by": named_staff.get("truongvanhanh.hanoi"),
                        "reason": _demo_note("Phân vùng demo KTC", username),
                    },
                )
                try:
                    assignment.full_clean()
                except Exception as exc:
                    self._verification_errors.append(f"{username}: invalid region assignment {region.ma_vung}: {exc}")

    def _seed_current_work_history(self, assignments, named_staff, sites, *, start_day):
        LichSuCongTac.objects.filter(nhan_vien__ma_nhan_vien__startswith="KTCVN-").delete()
        site_by_key_and_index = {}
        for site in sites:
            branch_key = getattr(site, "_demo_branch_key", self._branch_key_from_site_name(site.ten_muc_tieu))
            branch_sites = [item for item in sites if getattr(item, "_demo_branch_key", "") == branch_key]
            try:
                site_index = branch_sites.index(site) + 1
            except ValueError:
                site_index = 1
            site_by_key_and_index[(branch_key, site_index)] = site

        commander_pairs = (
            ("chihuy.dn01", site_by_key_and_index.get(("danang", 1))),
            ("chihuy.sg01", site_by_key_and_index.get(("saigon", 1))),
        )
        for username, site in commander_pairs:
            staff = named_staff.get(username)
            if staff is not None and site is not None:
                LichSuCongTac.objects.get_or_create(
                    nhan_vien=staff,
                    muc_tieu=site,
                    ngay_bat_dau=start_day,
                    defaults={
                        "quan_ly_truc_tiep": site.quan_ly_vung,
                        "chuc_danh_kiem_nhiem": staff.chuc_danh,
                        "ngay_ket_thuc": None,
                    },
                )

        current_pairs_by_staff = {}
        today = timezone.localdate()
        for assignment in sorted(assignments, key=lambda item: (item.ngay_truc, item.pk or 0)):
            site = getattr(getattr(assignment, "vi_tri_chot", None), "muc_tieu", None)
            if site is None or assignment.ngay_truc < today:
                continue
            current_pairs_by_staff.setdefault(assignment.nhan_vien_id, site.pk)
        if not current_pairs_by_staff:
            for assignment in sorted(assignments, key=lambda item: (item.ngay_truc, item.pk or 0)):
                site = getattr(getattr(assignment, "vi_tri_chot", None), "muc_tieu", None)
                if site is not None:
                    current_pairs_by_staff.setdefault(assignment.nhan_vien_id, site.pk)

        current_pairs = set(current_pairs_by_staff.items())
        staff_by_id = {staff.pk: staff for staff in NhanVien.objects.filter(pk__in=[sid for sid, _site_id in current_pairs]).select_related("chuc_danh")}
        site_by_id = {site.pk: site for site in MucTieu.objects.filter(pk__in=[site_id for _sid, site_id in current_pairs]).select_related("quan_ly_muc_tieu", "quan_ly_vung")}
        for staff_id, site_id in current_pairs:
            staff = staff_by_id.get(staff_id)
            site = site_by_id.get(site_id)
            if staff is None or site is None:
                continue
            LichSuCongTac.objects.get_or_create(
                nhan_vien=staff,
                muc_tieu=site,
                ngay_bat_dau=start_day,
                defaults={
                    "quan_ly_truc_tiep": site.quan_ly_muc_tieu or site.quan_ly_vung,
                    "chuc_danh_kiem_nhiem": staff.chuc_danh,
                    "ngay_ket_thuc": None,
                },
            )

    def _branch_key_from_site_name(self, value: str) -> str:
        value = value or ""
        if "Đà Nẵng" in value or "Da Nang" in value:
            return "danang"
        if "Sài Gòn" in value or "Sai Gon" in value:
            return "saigon"
        return "hanoi"

    def _site_headcount(self, branch_key: str, idx: int) -> int:
        if branch_key == "hanoi":
            return 5 + (idx % 3)
        if branch_key == "danang":
            return 4 + (idx % 2)
        return 5 + (idx % 2)

    def _seed_shifts(self):
        specs = [
            (f"{DEMO_PREFIX} Ca ngày 12h", time(6, 0), time(18, 0)),
            (f"{DEMO_PREFIX} Ca đêm 12h", time(18, 0), time(6, 0)),
            (f"{DEMO_PREFIX} Ca hành chính", time(8, 0), time(17, 0)),
            (f"{DEMO_PREFIX} Ca tuần tra đêm", time(22, 0), time(6, 0)),
        ]
        shifts = []
        for name, start, end in specs:
            # Use demo-prefixed shifts to avoid overwriting real operational shifts.
            shift, _ = CaLamViec.objects.get_or_create(
                ten_ca=name,
                defaults={"gio_bat_dau": start, "gio_ket_thuc": end},
            )
            shifts.append(shift)
        return shifts

    def _seed_posts(self, sites: Iterable[MucTieu]):
        posts = []
        for site in sites:
            sector = getattr(site, "_demo_sector", "Nhà máy")
            for post_name in POST_TEMPLATES.get(sector, POST_TEMPLATES["Nhà máy"]):
                post, _ = ViTriChot.objects.update_or_create(muc_tieu=site, ten_vi_tri=post_name, defaults={})
                post._demo_branch_key = getattr(site, "_demo_branch_key", "hanoi")
                posts.append(post)
        return posts

    def _seed_assignments(self, guards, posts, shifts, *, days: int, past_days: int):
        if not guards or not posts or not shifts:
            return []
        posts_by_branch = {
            branch.key: [post for post in posts if getattr(post, "_demo_branch_key", branch.key) == branch.key]
            for branch in BRANCHES
        }
        posts_by_site = {}
        sites_by_branch = {branch.key: [] for branch in BRANCHES}
        for post in posts:
            site = post.muc_tieu
            posts_by_site.setdefault(site.pk, []).append(post)
            branch_key = getattr(post, "_demo_branch_key", self._branch_key_from_site_name(site.ten_muc_tieu))
            if site not in sites_by_branch.setdefault(branch_key, []):
                sites_by_branch[branch_key].append(site)

        start_day = timezone.localdate() - timedelta(days=past_days)
        today = timezone.localdate()
        # Idempotency for v2: rebuild future demo rosters so current work
        # history and shift plans stay aligned. Past rows are kept for payroll,
        # attendance and audit demo history.
        PhanCongCaTruc.objects.filter(
            nhan_vien__in=guards,
            ngay_truc__gte=today,
        ).delete()

        assignments = []
        day_shift = shifts[0]
        night_shift = shifts[1]
        branch_sequences = {branch.key: 0 for branch in BRANCHES}
        guard_home_site = {}
        for guard in guards:
            branch_key = self._branch_key_from_employee(guard)
            branch_sites = sites_by_branch.get(branch_key) or []
            if branch_sites:
                home_site = branch_sites[branch_sequences.get(branch_key, 0) % len(branch_sites)]
                branch_sequences[branch_key] = branch_sequences.get(branch_key, 0) + 1
                guard_home_site[guard.pk] = home_site

        for day_offset in range(days):
            current_day = start_day + timedelta(days=day_offset)
            for idx, guard in enumerate(guards):
                branch_key = self._branch_key_from_employee(guard)
                home_site = guard_home_site.get(guard.pk)
                site_posts = posts_by_site.get(getattr(home_site, "pk", None)) or posts_by_branch.get(branch_key) or posts
                post = site_posts[(idx + day_offset) % len(site_posts)]
                shift = day_shift if (idx + day_offset) % 2 == 0 else night_shift
                assignment, created = PhanCongCaTruc.objects.get_or_create(
                    nhan_vien=guard,
                    ngay_truc=current_day,
                    ca_lam_viec=shift,
                    defaults={"vi_tri_chot": post},
                )
                if not created and assignment.vi_tri_chot_id != post.id and current_day >= today:
                    assignment.vi_tri_chot = post
                    assignment.save(update_fields=["vi_tri_chot"])
                assignments.append(assignment)
        return assignments

    def _branch_key_from_employee(self, employee: NhanVien) -> str:
        code = employee.ma_nhan_vien or ""
        if "-DN-" in code:
            return "danang"
        if "-SG-" in code:
            return "saigon"
        return "hanoi"

    def _seed_attendance(self, assignments, *, past_days: int):
        today = timezone.localdate()
        eligible = [assignment for assignment in assignments if assignment.ngay_truc <= today]
        for idx, assignment in enumerate(eligible):
            if idx % 17 == 0:
                continue  # vắng/thiếu check-in demo
            start_dt = timezone.make_aware(datetime.combine(assignment.ngay_truc, assignment.ca_lam_viec.gio_bat_dau))
            end_date = assignment.ngay_truc + timedelta(days=1 if assignment.ca_lam_viec.is_night_shift else 0)
            end_dt = timezone.make_aware(datetime.combine(end_date, assignment.ca_lam_viec.gio_ket_thuc))
            late_minutes = 0
            valid_location = True
            distance = 0.0
            if idx % 13 == 0:
                late_minutes = 22
            elif idx % 9 == 0:
                late_minutes = 8
            if idx % 29 == 0:
                valid_location = False
                distance = 380.0
            target = assignment.vi_tri_chot.muc_tieu
            point = Point(float(target.kinh_do or 105.8342) + (0.003 if not valid_location else 0), float(target.vi_do or 21.0278) + (0.003 if not valid_location else 0), srid=4326)
            ChamCong.objects.get_or_create(
                ca_truc=assignment,
                defaults={
                    "thoi_gian_check_in": start_dt + timedelta(minutes=late_minutes),
                    "thoi_gian_check_out": None if idx % 41 == 0 else end_dt - timedelta(minutes=5 if idx % 31 == 0 else 0),
                    "location_check_in": point,
                    "location_check_out": point,
                    "ip_check_in": "10.0.0.10",
                    "ip_check_out": "10.0.0.10",
                    "thiet_bi_check_in": "DEMO-MOBILE",
                    "thiet_bi_check_out": "DEMO-MOBILE",
                    "vi_tri_hop_le": valid_location,
                    "khoang_cach_check_in": distance,
                    "thuc_lam_gio": 12.0,
                    "di_muon_phut": late_minutes,
                    "ve_som_phut": 5 if idx % 31 == 0 else 0,
                    "ghi_chu": _demo_note("Chấm công seed", "wrong_gps" if not valid_location else "ok"),
                },
            )

    def _seed_patrols(self, sites, assignments):
        routes = []
        for site in sites[: self.profile.patrol_route_count]:
            route, _ = LoaiTuanTra.objects.update_or_create(
                muc_tieu=site,
                ten_loai=f"{DEMO_PREFIX} Tuyến tuần tra {site.ten_muc_tieu[-2:]}",
                defaults={"mo_ta": _demo_note("Tuyến tuần tra demo"), "thoi_gian_quy_dinh": 30, "yeu_cau_gps": True},
            )
            for order in range(1, 6):
                DiemTuanTra.objects.update_or_create(
                    loai_tuan_tra=route,
                    ma_qr=f"DEMO-KTCVN-{site.pk or 'SITE'}-{order}",
                    defaults={
                        "ten_diem": f"Điểm kiểm soát {order}",
                        "thu_tu": order,
                        "vi_do": Decimal(str((site.vi_do or 21.0278) + order * 0.0001)),
                        "kinh_do": Decimal(str((site.kinh_do or 105.8342) + order * 0.0001)),
                        "ban_kinh_cho_phep": 50,
                    },
                )
            routes.append(route)
        if not routes:
            return
        for idx, assignment in enumerate(assignments[: self.profile.patrol_record_cap]):
            if assignment.ngay_truc > timezone.localdate():
                continue
            route = routes[idx % len(routes)]
            patrol, created = LuotTuanTra.objects.get_or_create(
                phan_cong_ca_truc=assignment,
                loai_tuan_tra=route,
                defaults={
                    "nhan_vien": assignment.nhan_vien,
                    "trang_thai": "BO_DO" if idx % 19 == 0 else "HOAN_THANH",
                    "trang_thai_doi_soat": "MISSED" if idx % 19 == 0 else "COMPLETED_VALID",
                    "thoi_gian_ket_thuc": timezone.now() - timedelta(hours=idx % 24),
                    "so_diem_bat_buoc": 5,
                    "so_diem_da_quet": 4 if idx % 19 == 0 else 5,
                    "so_diem_canh_bao": 1 if idx % 23 == 0 else 0,
                },
            )
            if created:
                points = list(route.cac_diem.order_by("thu_tu"))[: 4 if idx % 19 == 0 else 5]
                for point in points:
                    GhiNhanTuanTra.objects.get_or_create(
                        luot_tuan_tra=patrol,
                        diem_tuan_tra=point,
                        defaults={
                            "lat_thuc_te": point.vi_do,
                            "lng_thuc_te": point.kinh_do,
                            "khoang_cach": 12.0,
                            "ket_qua": "CANH_BAO_XA" if idx % 23 == 0 else "HOP_LE",
                            "toa_do": f"{point.vi_do},{point.kinh_do}",
                            "ghi_chu": _demo_note("Quét điểm tuần tra demo"),
                        },
                    )

    def _seed_incidents(self, assignments, named_staff):
        if not assignments:
            return
        severities = ["THAP", "TB", "CAO", "NGUY_HIEM"]
        statuses = ["CHO_XU_LY", "DANG_XU_LY", "DA_XU_LY", "HOAN_TAT", "CHO_DEN_BU"]
        handlers = [named_staff["truongvanhanh.hanoi"], named_staff["dieuphoi.trungtam"]]
        for i in range(1, self.profile.incident_count + 1):
            assignment = assignments[(i * 7) % len(assignments)]
            ratio = i / max(1, self.profile.incident_count)
            severity = severities[0 if ratio <= 0.38 else 1 if ratio <= 0.75 else 2 if ratio <= 0.92 else 3]
            status = statuses[i % len(statuses)]
            BaoCaoSuCo.objects.update_or_create(
                ma_su_co=f"DEMO-KTCVN-SC-{i:04d}",
                defaults={
                    "tieu_de": f"{DEMO_PREFIX} Sự cố demo {i:03d}",
                    "nhan_vien_bao_cao": assignment.nhan_vien,
                    "muc_tieu": assignment.vi_tri_chot.muc_tieu,
                    "ca_truc": assignment,
                    "thoi_gian_phat_hien": timezone.now() - timedelta(days=i % 20, hours=i % 12),
                    "mo_ta_chi_tiet": _demo_note("Tình huống sự cố hiện trường phục vụ demo"),
                    "muc_do": severity,
                    "trang_thai": status,
                    "tong_thiet_hai": Decimal(2_000_000 if severity in {"CAO", "NGUY_HIEM"} else 0),
                    "nhan_vien_co_loi": assignment.nhan_vien if i % 15 == 0 else None,
                    "phai_thu_nhan_vien": Decimal(500_000 if i % 15 == 0 else 0),
                    "nguoi_xu_ly": handlers[i % len(handlers)],
                    "ghi_chu_quan_ly": _demo_note("SLA/biên bản xử lý demo"),
                },
            )
        for assignment in assignments[: self.profile.headcount_checks]:
            KiemTraQuanSo.objects.get_or_create(
                ca_truc=assignment,
                defaults={
                    "thoi_gian_phan_hoi": timezone.now() if assignment.pk % 8 else None,
                    "toa_do_xac_thuc": "21.0278,105.8342",
                    "device_id_xac_thuc": "DEMO-DEVICE",
                    "trang_thai": "MISSED" if assignment.pk % 13 == 0 else "LATE" if assignment.pk % 9 == 0 else "OK",
                },
            )

    def _seed_inventory(self, named_staff, sites):
        warehouse_staff = [named_staff["thukho.hanoi"], named_staff["thukho.danang"], named_staff["thukho.saigon"]]
        category, _ = LoaiVatTu.objects.update_or_create(ten_loai=f"{DEMO_PREFIX} Quân tư trang", defaults={"mo_ta": _demo_note("Danh mục quân tư trang demo")})
        items = [
            ("Bộ đàm", "Cái", 1_200_000, 1_500_000, 180),
            ("Gậy bảo vệ", "Cái", 180_000, 250_000, 220),
            ("Đèn pin tuần tra", "Cái", 240_000, 320_000, 160),
            ("Áo phản quang", "Cái", 85_000, 120_000, 250),
            ("Đồng phục bảo vệ", "Bộ", 420_000, 550_000, 500),
            ("Mũ bảo hộ", "Cái", 95_000, 130_000, 120),
            ("NFC tag tuần tra", "Cái", 45_000, 60_000, 60),
        ]
        vat_tu_objs = []
        for name, unit, cost, sell, stock in items:
            item, _ = VatTu.objects.update_or_create(
                ten_vat_tu=f"{DEMO_PREFIX} {name}",
                defaults={"loai_vat_tu": category, "don_vi_tinh": unit, "gia_nhap": cost, "gia_ban": sell, "so_luong_ton": stock, "muc_canh_bao": max(10, stock // 10)},
            )
            vat_tu_objs.append(item)
        for idx, staff in enumerate(warehouse_staff, start=1):
            receipt, _ = PhieuNhap.objects.get_or_create(
                ma_phieu=f"DEMO-KTCVN-PN-{idx:03d}",
                defaults={"nguoi_nhap": staff, "ghi_chu": _demo_note("Nhập kho demo", staff.ho_ten)},
            )
            if receipt.trang_thai == PhieuNhap.TrangThai.DRAFT:
                for item in vat_tu_objs:
                    ChiTietPhieuNhap.objects.get_or_create(phieu_nhap=receipt, vat_tu=item, defaults={"so_luong": max(20, item.so_luong_ton // 3), "don_gia": item.gia_nhap})
        for idx, site in enumerate(sites[: self.profile.inventory_issue_slips], start=1):
            item = vat_tu_objs[idx % len(vat_tu_objs)]
            issue, _ = PhieuXuat.objects.get_or_create(
                ma_phieu=f"DEMO-KTCVN-PX-{idx:03d}",
                defaults={"loai_xuat": "CONG_CU", "muc_tieu_nhan": site, "ghi_chu": _demo_note("Cấp phát công cụ cho mục tiêu")},
            )
            if issue.trang_thai == PhieuXuat.TrangThai.DRAFT:
                ChiTietPhieuXuat.objects.get_or_create(phieu_xuat=issue, vat_tu=item, defaults={"so_luong": 2 + (idx % 4), "don_gia_ban": item.gia_ban})

    def _seed_payroll(self, guards, named_staff):
        today = timezone.localdate()
        previous_month = today.month - 1 or 12
        previous_year = today.year if today.month > 1 else today.year - 1
        if self.profile.payroll_periods <= 1:
            periods = [
                (today.month, today.year, BangLuongThang.TrangThai.CALCULATED, "Kỳ lương tháng hiện tại đang tính"),
            ]
        else:
            periods = [
                (previous_month, previous_year, BangLuongThang.TrangThai.LOCKED, "Kỳ lương tháng trước đã khóa"),
                (today.month, today.year, BangLuongThang.TrangThai.CALCULATED, "Kỳ lương tháng hiện tại đang tính"),
            ]
        payroll_manager = named_staff["ketoantruong.hanoi"]
        for month, year, status, label in periods:
            payroll_name = f"{DEMO_PREFIX} {label} {month:02d}/{year}"
            existing_payroll = BangLuongThang.objects.filter(thang=month, nam=year).first()
            if existing_payroll and not str(existing_payroll.ten_bang_luong).startswith(DEMO_PREFIX):
                self.stdout.write(
                    self.style.WARNING(
                        f"Skip demo payroll {month:02d}/{year}: real payroll period exists ({existing_payroll.ten_bang_luong})."
                    )
                )
                continue
            if existing_payroll:
                payroll = existing_payroll
                payroll.ten_bang_luong = payroll_name
                payroll.ngay_chot_cong = timezone.localdate()
                payroll.trang_thai = status
                payroll.nguoi_duyet = payroll_manager
                payroll.tong_chi_tra = Decimal(0)
                payroll.tong_gio_cong = 0
                payroll.save(update_fields=["ten_bang_luong", "ngay_chot_cong", "trang_thai", "nguoi_duyet", "tong_chi_tra", "tong_gio_cong"])
            else:
                payroll = BangLuongThang.objects.create(
                    thang=month,
                    nam=year,
                    ten_bang_luong=payroll_name,
                    ngay_chot_cong=timezone.localdate(),
                    trang_thai=status,
                    nguoi_duyet=payroll_manager,
                    tong_chi_tra=Decimal(0),
                    tong_gio_cong=0,
                )
            if status == BangLuongThang.TrangThai.LOCKED:
                continue
            for idx, guard in enumerate(guards, start=1):
                base = Decimal(7_500_000)
                allowance = Decimal(500_000 if idx % 5 == 0 else 0)
                penalty = Decimal(150_000 if idx % 8 == 0 else 0)
                uniform = Decimal(250_000 if idx % 37 == 0 else 0)
                net = base + allowance - penalty - uniform
                ChiTietLuong.objects.update_or_create(
                    bang_luong=payroll,
                    nhan_vien=guard,
                    defaults={
                        "tong_gio_lam": 180.0,
                        "so_ngay_nghi": 1 if idx % 17 == 0 else 0,
                        "luong_chinh": base,
                        "thuong_chuyen_can": Decimal(800_000 if idx % 11 else 0),
                        "phu_cap_khac": allowance,
                        "ung_luong": Decimal(1_000_000 if idx % 23 == 0 else 0),
                        "phat_vi_pham": penalty,
                        "tien_dong_phuc": uniform,
                        "tien_den_bu": Decimal(0),
                        "bao_hiem": Decimal(650_000),
                        "phi_cong_doan": Decimal(50_000),
                        "thuc_lanh": net - Decimal(700_000),
                        "ghi_chu": _demo_note("Phiếu lương demo"),
                        "nguon_du_lieu_snapshot": {"scenario": "ktc_viet_nam_security_group", "guard_username": guard.user.username if guard.user_id else ""},
                    },
                )
            payroll.update_totals()
        for idx, guard in enumerate(guards[::12][:35], start=1):
            TamUngLuong.objects.update_or_create(
                so_phieu=f"DEMO-KTCVN-TU-{idx:03d}",
                defaults={"nhan_vien": guard, "so_tien": Decimal(1_000_000), "trang_thai": TamUngLuong.TrangThai.APPROVED, "ly_do": _demo_note("Tạm ứng demo"), "nguoi_duyet": payroll_manager.user},
            )
        for idx, guard in enumerate(guards[::41][:5], start=1):
            KhoanKhauTruNhanVien.objects.update_or_create(
                so_chung_tu=f"DEMO-KTCVN-KT-{idx:03d}",
                defaults={"nhan_vien": guard, "loai_khau_tru": KhoanKhauTruNhanVien.LoaiKhauTru.DONG_PHUC, "so_tien": Decimal(550_000), "trang_thai": KhoanKhauTruNhanVien.TrangThai.APPROVED, "ly_do": _demo_note("Mất/hỏng quân tư trang demo"), "nguoi_duyet": payroll_manager.user},
            )

    def _verify_demo_access_contract(self, named_staff, guards, sites):
        expected_roles = {username: role for username, _full_name, _title, _department, role, _staff, _branch in DASHBOARD_ACCOUNTS}
        for username, role in expected_roles.items():
            user = User.objects.filter(username=username).first()
            if user is None:
                self._verification_errors.append(f"{username}: user not created")
                continue
            if not user.has_usable_password():
                self._verification_errors.append(f"{username}: unusable password")
            if not has_role(user, role):
                self._verification_errors.append(f"{username}: expected role {role} not active")
            for permission_key in ROLE_PRIMARY_PERMISSIONS.get(role, ()):
                if not has_permission(user, permission_key):
                    self._verification_errors.append(f"{username}: expected role permission {permission_key} missing")

        for username in ("chihuy.dn01", "chihuy.sg01"):
            user = User.objects.filter(username=username).first()
            if user is None:
                continue
            for perm_code in SCHEDULE_MODEL_PERMISSIONS:
                if not user.has_perm(perm_code):
                    self._verification_errors.append(f"{username}: expected Django permission {perm_code} missing")

        for guard in guards:
            user = guard.user
            if user and not has_role(user, "nhan_vien_bao_ve"):
                self._verification_errors.append(f"{user.username}: expected guard role missing")

        dn_commander = named_staff.get("chihuy.dn01")
        sg_commander = named_staff.get("chihuy.sg01")
        if dn_commander:
            count = MucTieu.objects.filter(quan_ly_muc_tieu=dn_commander).count()
            if count != 1:
                self._verification_errors.append(f"chihuy.dn01: expected exactly 1 managed site, got {count}")
        if sg_commander:
            count = MucTieu.objects.filter(quan_ly_muc_tieu=sg_commander).count()
            if count != 1:
                self._verification_errors.append(f"chihuy.sg01: expected exactly 1 managed site, got {count}")

        if not Region.objects.filter(ma_vung__in=BRANCH_REGION_CODES.values()).count() == len(BRANCH_REGION_CODES):
            self._verification_errors.append("Region scope: missing one or more demo regions")
        if CoHoiKinhDoanh.objects.filter(ten_co_hoi__startswith=DEMO_PREFIX, region__isnull=True).exists():
            self._verification_errors.append("Region scope: demo opportunities missing CoHoiKinhDoanh.region")
        if not LichSuCongTac.objects.filter(nhan_vien__ma_nhan_vien__startswith="KTCVN-", muc_tieu__isnull=False, ngay_ket_thuc__isnull=True).exists():
            self._verification_errors.append("Work history scope: no current LichSuCongTac generated for demo staff")

        bgd_group_name = ROLE_TO_GROUP_LABEL["ban_giam_doc"]
        region_group_name = ROLE_TO_GROUP_LABEL["quan_ly_vung"]
        for username in ("giamdocchinhanh.danang", "giamdocchinhanh.saigon"):
            user = User.objects.filter(username=username).select_related("nhan_vien__chuc_danh__nhom_quyen").first()
            if user is None:
                continue
            group_names = set(user.groups.values_list("name", flat=True))
            title_group = getattr(getattr(getattr(user, "nhan_vien", None), "chuc_danh", None), "nhom_quyen", None)
            if bgd_group_name in group_names or (title_group is not None and title_group.name == bgd_group_name):
                self._verification_errors.append(f"{username}: branch director must not be mapped to Ban Giám đốc")
            if region_group_name not in group_names:
                self._verification_errors.append(f"{username}: branch director missing Quản lý vùng group")

        for username in ("truongvanhanh.hanoi", "dieuphoi.trungtam"):
            user = User.objects.filter(username=username).first()
            if user is None:
                continue
            names = list(SiteVisibilityPolicy.managed_sites(user).values_list("ten_muc_tieu", flat=True))
            for branch_label in ("Hà Nội", "Đà Nẵng", "Sài Gòn"):
                if not any(branch_label in name for name in names):
                    self._verification_errors.append(f"{username}: central operations scope missing {branch_label}")
            if NhanVienRegionAssignment.objects.filter(
                nhan_vien=user.nhan_vien,
                reason__contains=DEMO_PREFIX,
                status=NhanVienRegionAssignment.Status.ACTIVE,
            ).exists():
                self._verification_errors.append(f"{username}: central operations must not be faked as a single demo region assignment")

        duplicate_current_staff = (
            LichSuCongTac.objects.filter(
                nhan_vien__ma_nhan_vien__startswith="KTCVN-",
                nhan_vien__ma_nhan_vien__contains="-BV",
                ngay_ket_thuc__isnull=True,
            )
            .values("nhan_vien_id")
            .annotate(current_count=Count("id"))
            .filter(current_count__gt=1)
        )
        if duplicate_current_staff.exists():
            self._verification_errors.append("Work history scope: guard has multiple current LichSuCongTac rows")

    def _reset_demo_data(self):
        self.stdout.write(self.style.WARNING("Resetting previous DEMO-KTCVN data..."))
        # Delete objects in dependency order. Only DEMO-KTCVN tagged/prefixed data is targeted.
        # Legacy DEMO-DNSG data from the earlier draft scenario is also removed when easily identifiable.
        BaoCaoSuCo.objects.filter(ma_su_co__startswith="DEMO-KTCVN-").delete()
        GhiNhanTuanTra.objects.filter(ghi_chu__contains=DEMO_PREFIX).delete()
        LuotTuanTra.objects.filter(loai_tuan_tra__ten_loai__startswith=DEMO_PREFIX).delete()
        DiemTuanTra.objects.filter(ma_qr__startswith="DEMO-KTCVN-").delete()
        LoaiTuanTra.objects.filter(ten_loai__startswith=DEMO_PREFIX).delete()
        KiemTraQuanSo.objects.filter(ca_truc__nhan_vien__ma_nhan_vien__startswith="KTCVN-").delete()
        ChamCong.objects.filter(ghi_chu__contains=DEMO_PREFIX).delete()
        PhanCongCaTruc.objects.filter(nhan_vien__ma_nhan_vien__startswith="KTCVN-").delete()
        CaLamViec.objects.filter(ten_ca__startswith=DEMO_PREFIX).delete()
        ChiTietLuong.objects.filter(nhan_vien__ma_nhan_vien__startswith="KTCVN-").delete()
        HopDongLaoDong.objects.filter(so_hop_dong__startswith="DEMO-KTCVN-HDLD-").delete()
        BangLuongThang.objects.filter(ten_bang_luong__startswith=DEMO_PREFIX).delete()
        TamUngLuong.objects.filter(so_phieu__startswith="DEMO-KTCVN-").delete()
        KhoanKhauTruNhanVien.objects.filter(so_chung_tu__startswith="DEMO-KTCVN-").delete()
        ChiTietPhieuXuat.objects.filter(phieu_xuat__ma_phieu__startswith="DEMO-KTCVN-").delete()
        PhieuXuat.objects.filter(ma_phieu__startswith="DEMO-KTCVN-").delete()
        ChiTietPhieuNhap.objects.filter(phieu_nhap__ma_phieu__startswith="DEMO-KTCVN-").delete()
        PhieuNhap.objects.filter(ma_phieu__startswith="DEMO-KTCVN-").delete()
        VatTu.objects.filter(ten_vat_tu__startswith=DEMO_PREFIX).delete()
        LoaiVatTu.objects.filter(ten_loai__startswith=DEMO_PREFIX).delete()
        ViTriChot.objects.filter(muc_tieu__ten_muc_tieu__startswith=DEMO_PREFIX).delete()
        MucTieu.objects.filter(ten_muc_tieu__startswith=DEMO_PREFIX).delete()
        HopDong.objects.filter(so_hop_dong__startswith="DEMO-KTCVN-").delete()
        CoHoiKinhDoanh.objects.filter(ten_co_hoi__startswith=DEMO_PREFIX).delete()
        KhachHangTiemNang.objects.filter(ten_cong_ty__startswith=DEMO_PREFIX).delete()
        LichSuCongTac.objects.filter(nhan_vien__ma_nhan_vien__startswith="KTCVN-").delete()
        NhanVienRegionAssignment.objects.filter(reason__contains=DEMO_PREFIX).delete()
        Region.objects.filter(ma_vung__startswith="DEMO-KTCVN-").delete()
        NhanVien.objects.filter(ma_nhan_vien__startswith="KTCVN-").delete()
        User.objects.filter(username__in=[row[0] for row in DASHBOARD_ACCOUNTS]).delete()
        User.objects.filter(username__regex=r"^baove\.(hn|dn|sg)[0-9]{3}$").delete()
        # Best-effort cleanup for pre-V3 legacy draft data. These predicates are prefix-only and avoid touching real rows.
        NhanVien.objects.filter(ma_nhan_vien__startswith="DNSG-").delete()
        User.objects.filter(username__regex=r"^baove\.(hn|dn|sg)[0-9]{3}$").delete()
