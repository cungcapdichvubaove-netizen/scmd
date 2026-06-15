"""Patrol and attendance factories."""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from inspection.models import DiemTuanTra, GhiNhanTuanTra, LoaiTuanTra, LuotTuanTra
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc
from seed.orchestrator.utils import aware, jitter, point_from_lat_lng

SHIFT_DEFS = [("Ca ngày 06-18", time(6, 0), time(18, 0)), ("Ca đêm 18-06", time(18, 0), time(6, 0)), ("Ca hành chính", time(8, 0), time(17, 0))]


def seed_patrol_and_attendance(ctx, hr, site_data):
    shifts = []
    for name, start, end in SHIFT_DEFS:
        shift, _ = CaLamViec.objects.get_or_create(ten_ca=name, defaults={"gio_bat_dau": start, "gio_ket_thuc": end})
        shifts.append(shift)

    guards = [s for s in hr["staff"] if s.chuc_danh and s.chuc_danh.ten_chuc_danh == "Guard"] or hr["staff"]
    assignments = []
    days = min(90, max(10, ctx.scale.finance_months * 10))
    total_assignments = min(max(100, len(guards) * 3), max(500, ctx.scale.patrol_history // 3))
    for i in range(1, total_assignments + 1):
        guard = guards[(i - 1) % len(guards)]
        post = site_data["posts"][(i - 1) % len(site_data["posts"])]
        shift = shifts[i % len(shifts)]
        duty_date = date.today() - timedelta(days=i % days)
        try:
            assignment, _ = PhanCongCaTruc.objects.get_or_create(
                nhan_vien=guard,
                ngay_truc=duty_date,
                ca_lam_viec=shift,
                defaults={"vi_tri_chot": post},
            )
            assignments.append(assignment)
            lat, lng = jitter(post.muc_tieu.vi_do or 21.0, post.muc_tieu.kinh_do or 105.8, meters=40)
            check_in = aware(datetime.combine(duty_date, shift.gio_bat_dau) + timedelta(minutes=random.randint(-10, 20)))
            check_out_date = duty_date + timedelta(days=1 if shift.is_night_shift else 0)
            check_out = aware(datetime.combine(check_out_date, shift.gio_ket_thuc) + timedelta(minutes=random.randint(-20, 25)))
            ChamCong.objects.get_or_create(
                ca_truc=assignment,
                defaults={
                    "thoi_gian_check_in": check_in,
                    "thoi_gian_check_out": check_out,
                    "location_check_in": point_from_lat_lng(lat, lng),
                    "location_check_out": point_from_lat_lng(lat, lng),
                    "vi_tri_hop_le": True,
                    "khoang_cach_check_in": random.uniform(1, 80),
                    "thuc_lam_gio": 12.0 if shift.is_night_shift or "12" in shift.ten_ca else 8.0,
                    "di_muon_phut": max(0, random.randint(-5, 20)),
                    "ve_som_phut": max(0, random.randint(-10, 15)),
                    "ghi_chu": "Digital Twin attendance",
                },
            )
        except IntegrityError:
            continue

    routes = []
    checkpoints = []
    for i in range(1, ctx.scale.patrol_routes + 1):
        site = site_data["sites"][(i - 1) % len(site_data["sites"])]
        route, _ = LoaiTuanTra.objects.get_or_create(
            muc_tieu=site,
            ten_loai=ctx.code("ROUTE", i),
            defaults={"mo_ta": "Digital Twin patrol route", "thoi_gian_quy_dinh": random.choice([30, 45, 60]), "yeu_cau_gps": True},
        )
        routes.append(route)
        per_route = max(3, ctx.scale.checkpoints // max(1, ctx.scale.patrol_routes))
        for j in range(1, per_route + 1):
            lat, lng = jitter(site.vi_do or 21.0, site.kinh_do or 105.8, meters=250)
            point, _ = DiemTuanTra.objects.get_or_create(
                loai_tuan_tra=route,
                ma_qr=f"{route.ten_loai}-CP-{j:03d}",
                defaults={
                    "ten_diem": f"Checkpoint {j:03d}",
                    "thu_tu": j,
                    "vi_do": Decimal(str(round(lat, 8))),
                    "kinh_do": Decimal(str(round(lng, 8))),
                    "ban_kinh_cho_phep": random.choice([30, 50, 80]),
                },
            )
            checkpoints.append(point)

    patrols_to_make = ctx.scale.patrol_history
    existing_patrols = LuotTuanTra.objects.filter(loai_tuan_tra__in=routes).count()
    base_start = aware(datetime(2023, 1, 1, 6, 0))
    for i in range(existing_patrols + 1, patrols_to_make + 1):
        route = routes[(i - 1) % len(routes)]
        guard = guards[(i - 1) % len(guards)]
        start_at = base_start + timedelta(minutes=i * 37)
        patrol, _ = LuotTuanTra.objects.get_or_create(
            nhan_vien=guard,
            loai_tuan_tra=route,
            thoi_gian_bat_dau=start_at,
            defaults={"thoi_gian_ket_thuc": start_at + timedelta(minutes=route.thoi_gian_quy_dinh), "trang_thai": random.choice(["HOAN_THANH", "DANG_DI"]),},
        )
        if i <= min(patrols_to_make, 10000):
            for checkpoint in list(route.cac_diem.all()[:3]):
                GhiNhanTuanTra.objects.get_or_create(
                    luot_tuan_tra=patrol,
                    diem_tuan_tra=checkpoint,
                    defaults={
                        "lat_thuc_te": checkpoint.vi_do,
                        "lng_thuc_te": checkpoint.kinh_do,
                        "khoang_cach": random.uniform(0, 25),
                        "ket_qua": "HOP_LE",
                        "toa_do": f"{checkpoint.vi_do},{checkpoint.kinh_do}",
                        "ghi_chu": "Digital Twin patrol evidence",
                    },
                )
    ctx.count("shifts", len(shifts))
    ctx.count("assignments", len(assignments))
    ctx.count("patrol_routes", len(routes))
    ctx.count("checkpoints", len(checkpoints))
    ctx.count("patrol_sessions_target", patrols_to_make)
    return {"shifts": shifts, "assignments": assignments, "routes": routes, "checkpoints": checkpoints}
