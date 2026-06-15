"""Protected-site and post factories."""

import random
from decimal import Decimal

from clients.models import MucTieu, MucTieuDonGiaHistory
from operations.models import ViTriChot
from users.models import LichSuCongTac
from seed.orchestrator.utils import CITY_COORDS, jitter, vn_phone

POST_NAMES = ["Cổng chính", "Cổng phụ", "Sảnh lễ tân", "Kho hàng", "Bãi xe", "Tuần tra vòng ngoài", "Phòng camera", "Khu kỹ thuật"]


def _role_pool(staff, role_name):
    return [s for s in staff if s.chuc_danh and s.chuc_danh.ten_chuc_danh == role_name]


def seed_sites(ctx, contract_data, hr):
    commanders = _role_pool(hr["staff"], "Site Commander") or hr["staff"][:20]
    regional = _role_pool(hr["staff"], "Regional Director") or hr["staff"][:5]
    sites = []
    posts = []
    city_keys = list(CITY_COORDS.keys())
    for i in range(1, ctx.scale.sites + 1):
        city = city_keys[(i - 1) % len(city_keys)]
        lat, lng = jitter(*CITY_COORDS[city], meters=18000)
        contract = contract_data["contracts"][(i - 1) % len(contract_data["contracts"])]
        site, _ = MucTieu.objects.get_or_create(
            hop_dong=contract,
            ten_muc_tieu=f"{ctx.code('SITE', i)} - Mục tiêu {city}",
            defaults={
                "dia_chi": f"Khu vực {city} - {ctx.fake.address()}",
                "vi_do": lat,
                "kinh_do": lng,
                "ban_kinh_cho_phep": random.choice([80, 100, 150, 200]),
                "luong_khoan_bao_ve": Decimal(str(random.randint(6, 10) * 1_000_000)),
                "so_gio_mot_ngay": Decimal("12.00"),
                "nguoi_lien_he": ctx.fake.name(),
                "sdt_lien_he": vn_phone(300000 + i),
                "so_luong_nhan_vien": random.randint(8, 42),
                "quan_ly_muc_tieu": commanders[(i - 1) % len(commanders)],
                "quan_ly_vung": regional[(i - 1) % len(regional)],
            },
        )
        sites.append(site)
        for j, post_name in enumerate(POST_NAMES[: random.randint(4, len(POST_NAMES))], start=1):
            post, _ = ViTriChot.objects.get_or_create(
                muc_tieu=site,
                ten_vi_tri=f"{post_name} {j}",
            )
            posts.append(post)
        MucTieuDonGiaHistory.objects.get_or_create(
            muc_tieu=site,
            ngay_hieu_luc=contract.ngay_hieu_luc,
            defaults={
                "luong_khoan_bao_ve": site.luong_khoan_bao_ve,
                "so_gio_mot_ngay": site.so_gio_mot_ngay,
                "ghi_chu": "Digital Twin baseline payroll rate",
            },
        )
        _seed_site_assignment_history(site, hr["staff"], i)
    ctx.count("sites", len(sites))
    ctx.count("guard_posts", len(posts))
    ctx.count("site_assignment_history", LichSuCongTac.objects.filter(muc_tieu__in=sites).count())
    return {"sites": sites, "posts": posts}


def _seed_site_assignment_history(site, staff, site_index):
    """Create a realistic protected-site command tree."""
    team_leaders = _role_pool(staff, "Team Leader") or staff[:10]
    guards = _role_pool(staff, "Guard") or staff
    commander = site.quan_ly_muc_tieu
    start = site.hop_dong.ngay_hieu_luc

    people = [(commander, commander.chuc_danh, site.quan_ly_vung)]
    for offset in range(2):
        leader = team_leaders[(site_index * 2 + offset) % len(team_leaders)]
        people.append((leader, leader.chuc_danh, commander))
    guard_count = max(6, min(24, site.so_luong_nhan_vien or 12))
    for offset in range(guard_count):
        guard = guards[(site_index * guard_count + offset) % len(guards)]
        leader = team_leaders[(site_index * 2 + offset % 2) % len(team_leaders)]
        people.append((guard, guard.chuc_danh, leader))

    for person, title, manager in people:
        LichSuCongTac.objects.get_or_create(
            nhan_vien=person,
            muc_tieu=site,
            ngay_bat_dau=start,
            defaults={
                "chuc_danh_kiem_nhiem": title,
                "quan_ly_truc_tiep": manager,
            },
        )
