"""HR Digital Twin factories."""

import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import transaction

from users.models import BangCapChungChi, HocVan, LichSuCongTac, NhanVien
from seed.orchestrator.utils import fake_cccd, get_user, internal_email, save_validated, vn_phone

ROLE_DISTRIBUTION = [
    ("CEO", 1),
    ("COO", 2),
    ("Regional Director", 6),
    ("Area Manager", 24),
    ("Site Commander", 100),
    ("Team Leader", 180),
]

CERTIFICATES = [
    "Chứng chỉ nghiệp vụ bảo vệ",
    "PCCC cơ bản",
    "Sơ cấp cứu tại hiện trường",
    "Vận hành bộ đàm",
    "Giám sát camera an ninh",
]


def _target_role(index: int, total: int) -> str:
    consumed = 0
    for role, count in ROLE_DISTRIBUTION:
        consumed += count
        if index <= consumed:
            return role
    if index % 17 == 0:
        return "Thủ kho"
    if index % 23 == 0:
        return "Kế toán"
    if index % 29 == 0:
        return "Điều phối SOC"
    return "Guard"


def seed_hr(ctx, master):
    departments = master["departments"]
    titles = master["titles"]
    staff = []

    ops_department = departments["Điều hành"]
    guard_department = departments["Điều hành"]
    finance_department = departments["Tài chính"]
    warehouse_department = departments["Kho vận"]
    soc_department = departments["SOC"]

    for i in range(1, ctx.scale.staff + 1):
        role = _target_role(i, ctx.scale.staff)
        username = ctx.code("USER", i).lower().replace("-", "_")
        email = internal_email("nhanvien", i)
        user = get_user(username, email)
        group = titles[role].nhom_quyen if titles[role].nhom_quyen_id else None
        if group and not user.groups.filter(pk=group.pk).exists():
            user.groups.add(group)
        profile = getattr(user, "nhan_vien", None)
        if profile is None:
            profile = NhanVien(user=user)
        profile.ho_ten = ctx.fake.name()
        profile.email = email
        profile.sdt_chinh = vn_phone(i)
        profile.so_cccd = fake_cccd(i)
        profile.ngay_sinh = date.today() - timedelta(days=random.randint(22 * 365, 55 * 365))
        profile.gioi_tinh = random.choice(["M", "F"])
        profile.ngay_vao_lam = date.today() - timedelta(days=random.randint(30, 12 * 365))
        profile.trang_thai_lam_viec = NhanVien.TrangThaiLamViec.CHINH_THUC
        profile.loai_hop_dong = random.choice(["XDTH", "KXDTH", "THOIVU"])
        profile.chuc_danh = titles[role]
        if role in {"Kế toán"}:
            profile.phong_ban = finance_department
        elif role in {"Thủ kho"}:
            profile.phong_ban = warehouse_department
        elif role in {"Điều phối SOC"}:
            profile.phong_ban = soc_department
        elif role == "Guard":
            profile.phong_ban = guard_department
        else:
            profile.phong_ban = ops_department
        save_validated(profile)
        staff.append(profile)

        if i <= max(20, ctx.scale.staff // 10):
            HocVan.objects.get_or_create(
                nhan_vien=profile,
                truong_dao_tao="Trung tâm đào tạo SCMD Digital Twin",
                chuyen_nganh="Nghiệp vụ bảo vệ chuyên nghiệp",
                trinh_do="Sơ cấp",
                tu_ngay=profile.ngay_vao_lam,
                defaults={"den_ngay": profile.ngay_vao_lam + timedelta(days=30)},
            )
        if i % 3 == 0:
            BangCapChungChi.objects.get_or_create(
                nhan_vien=profile,
                ten_bang_cap=random.choice(CERTIFICATES),
                noi_cap="SCMD Training Center",
                ngay_cap=profile.ngay_vao_lam + timedelta(days=30),
            )

    _seed_management_history(staff)
    ctx.count("staff", len(staff))
    ctx.count("work_history_records", LichSuCongTac.objects.filter(nhan_vien__in=staff).count())
    return {"staff": staff}


def _seed_management_history(staff):
    """Create deterministic organization-level work history and reporting tree.

    Site-level current assignments are created later by the sites factory once
    protected sites exist. This baseline history gives every synthetic employee
    a non-orphan work-history trail and a direct manager where appropriate.
    """
    if not staff:
        return

    by_role = {}
    for person in staff:
        role = person.chuc_danh.ten_chuc_danh if person.chuc_danh else "Guard"
        by_role.setdefault(role, []).append(person)

    ceo = by_role.get("CEO", [staff[0]])[0]
    coos = by_role.get("COO", [ceo])
    regionals = by_role.get("Regional Director", coos)
    areas = by_role.get("Area Manager", regionals)
    commanders = by_role.get("Site Commander", areas)
    leaders = by_role.get("Team Leader", commanders)

    def manager_for(index, role):
        if role == "CEO":
            return None
        if role == "COO":
            return ceo
        if role == "Regional Director":
            return coos[index % len(coos)]
        if role == "Area Manager":
            return regionals[index % len(regionals)]
        if role == "Site Commander":
            return areas[index % len(areas)]
        if role == "Team Leader":
            return commanders[index % len(commanders)]
        return leaders[index % len(leaders)]

    for index, person in enumerate(staff):
        role = person.chuc_danh.ten_chuc_danh if person.chuc_danh else "Guard"
        LichSuCongTac.objects.get_or_create(
            nhan_vien=person,
            muc_tieu=None,
            ngay_bat_dau=person.ngay_vao_lam or date.today(),
            defaults={
                "chuc_danh_kiem_nhiem": person.chuc_danh,
                "quan_ly_truc_tiep": manager_for(index, role),
            },
        )
        if role in {"COO", "Regional Director", "Area Manager", "Site Commander", "Team Leader"}:
            promotion_date = (person.ngay_vao_lam or date.today()) + timedelta(days=365)
            if promotion_date < date.today():
                LichSuCongTac.objects.get_or_create(
                    nhan_vien=person,
                    muc_tieu=None,
                    ngay_bat_dau=promotion_date,
                    defaults={
                        "chuc_danh_kiem_nhiem": person.chuc_danh,
                        "quan_ly_truc_tiep": manager_for(index, role),
                    },
                )
