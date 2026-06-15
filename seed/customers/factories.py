"""Customer and sales pipeline factories."""

import random
from decimal import Decimal

from clients.models import CoHoiKinhDoanh, KhachHangTiemNang
from seed.orchestrator.utils import INDUSTRIES, internal_email, vn_phone


def seed_customers(ctx, hr):
    sales_pool = [s for s in hr["staff"] if s.phong_ban and s.phong_ban.ten_phong_ban in {"Kinh doanh", "CSKH"}]
    if not sales_pool:
        sales_pool = hr["staff"][:10]
    customers = []
    opportunities = []
    for i in range(1, ctx.scale.customers + 1):
        industry = INDUSTRIES[(i - 1) % len(INDUSTRIES)]
        name = f"{industry} Digital Twin {i:03d}"
        customer, _ = KhachHangTiemNang.objects.get_or_create(
            ten_cong_ty=name,
            defaults={
                "nguoi_lien_he": ctx.fake.name(),
                "sdt": vn_phone(200000 + i),
                "email": internal_email("customer", i),
                "dia_chi": ctx.fake.address(),
                "nguon": random.choice(["WEBSITE", "GIOI_THIEU", "MXH", "KHAC"]),
                "trang_thai": "CHOT_HOP_DONG",
                "ghi_chu": f"Digital Twin customer group: {industry}",
            },
        )
        customers.append(customer)
        opp, _ = CoHoiKinhDoanh.objects.get_or_create(
            khach_hang_tiem_nang=customer,
            ten_co_hoi=f"Gói dịch vụ bảo vệ {name}",
            defaults={
                "gia_tri_uoc_tinh": Decimal(str(random.randint(120, 1800) * 1_000_000)),
                "trang_thai": CoHoiKinhDoanh.TrangThai.THANH_CONG,
                "nguoi_phu_trach": random.choice(sales_pool),
            },
        )
        opportunities.append(opp)
    ctx.count("customers", len(customers))
    ctx.count("opportunities", len(opportunities))
    return {"customers": customers, "opportunities": opportunities}
