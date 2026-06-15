"""Contract factories with deterministic business metadata."""

import random
from datetime import date, timedelta
from decimal import Decimal

from clients.models import HopDong

SERVICE_TERMS = [
    "SLA phản ứng sự cố dưới 15 phút; nghiệm thu theo dữ liệu chấm công và tuần tra.",
    "KPI quân số 98%; tuần tra đủ tuyến; báo cáo sự cố trong 5 phút.",
    "Đối soát tháng theo bảng điểm vendor, biên bản sự cố và chứng từ vật tư.",
]


def seed_contracts(ctx, customer_data):
    contracts = []
    opportunities = customer_data["opportunities"]
    for i in range(1, ctx.scale.contracts + 1):
        customer = customer_data["customers"][(i - 1) % len(customer_data["customers"])]
        opportunity = opportunities[(i - 1) % len(opportunities)] if i <= len(opportunities) else None
        start = date.today() - timedelta(days=random.randint(30, 900))
        months = random.choice([12, 24, 36])
        contract, _ = HopDong.objects.get_or_create(
            so_hop_dong=ctx.code("HD", i),
            defaults={
                "co_hoi": opportunity if opportunity and not hasattr(opportunity, "hop_dong") else None,
                "khach_hang_cu": customer,
                "ngay_ky": start - timedelta(days=7),
                "ngay_hieu_luc": start,
                "ngay_het_han": start + timedelta(days=30 * months),
                "gia_tri": Decimal(str(random.randint(80, 850) * 1_000_000)),
                "trang_thai": "HIEU_LUC",
            },
        )
        contracts.append(contract)
    ctx.count("contracts", len(contracts))
    return {"contracts": contracts, "service_terms": SERVICE_TERMS}
