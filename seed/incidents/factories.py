"""Incident history factories."""

import random
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from operations.models import BaoCaoSuCo

INCIDENT_TYPES = [
    ("Mất cắp", 0.10, "CAO"),
    ("Xâm nhập", 0.08, "CAO"),
    ("Cháy nổ", 0.02, "NGUY_HIEM"),
    ("Vi phạm nội quy", 0.45, "TB"),
    ("Tai nạn lao động", 0.05, "CAO"),
    ("Mất điện", 0.30, "THAP"),
]


def _weighted_type():
    r = random.random()
    acc = 0
    for name, weight, severity in INCIDENT_TYPES:
        acc += weight
        if r <= acc:
            return name, severity
    return INCIDENT_TYPES[-1][0], INCIDENT_TYPES[-1][2]


def seed_incidents(ctx, hr, site_data, patrol_data):
    guards = [s for s in hr["staff"] if s.chuc_danh and s.chuc_danh.ten_chuc_danh == "Guard"] or hr["staff"]
    assignments = patrol_data.get("assignments") or []
    created = 0
    for i in range(1, ctx.scale.incidents + 1):
        incident_type, severity = _weighted_type()
        site = site_data["sites"][(i - 1) % len(site_data["sites"])]
        reporter = guards[(i - 1) % len(guards)]
        code = ctx.code("INC", i)
        if BaoCaoSuCo.objects.filter(ma_su_co=code).exists():
            continue
        detected_at = timezone.now() - timedelta(days=random.randint(0, 36 * 30), minutes=random.randint(0, 1440))
        ca_truc = assignments[(i - 1) % len(assignments)] if assignments and i % 3 != 0 else None
        BaoCaoSuCo.objects.create(
            ma_su_co=code,
            tieu_de=f"{incident_type} tại {site.ten_muc_tieu}",
            nhan_vien_bao_cao=reporter,
            muc_tieu=site,
            ca_truc=ca_truc,
            thoi_gian_phat_hien=detected_at,
            mo_ta_chi_tiet=f"Digital Twin incident: {incident_type}. Dữ liệu giả lập phục vụ QA/UAT/AI testing.",
            muc_do=severity,
            trang_thai=random.choice(["CHO_XU_LY", "DANG_XU_LY", "DA_XU_LY", "HOAN_TAT"]),
            tong_thiet_hai=Decimal(str(random.choice([0, 500000, 1500000, 5000000, 20000000]))),
            cong_ty_chi_tra=Decimal("0"),
            nguoi_xu_ly=site.quan_ly_muc_tieu,
            ghi_chu_quan_ly="Digital Twin incident trail",
        )
        created += 1
    ctx.count("incidents_created", created)
    return {"incident_types": INCIDENT_TYPES}
