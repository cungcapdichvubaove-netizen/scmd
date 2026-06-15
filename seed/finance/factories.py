"""Finance and payroll history factories."""

import random
from datetime import date
from decimal import Decimal

from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from seed.orchestrator.utils import decimal_vnd, month_iter


def seed_finance(ctx, hr):
    staff = hr["staff"]
    for person in staff:
        CauHinhLuong.objects.get_or_create(
            nhan_vien=person,
            defaults={
                "luong_co_ban_ngay": decimal_vnd(random.randint(220, 450) * 1000),
                "phu_cap_trach_nhiem": decimal_vnd(random.randint(0, 2500) * 1000),
                "phu_cap_xang_xe": decimal_vnd(random.randint(0, 800) * 1000),
                "phu_cap_an_uong": decimal_vnd(random.randint(0, 900) * 1000),
            },
        )
    periods = []
    detail_count = 0
    approver = staff[0] if staff else None
    active_staff = staff[: min(len(staff), 400 if ctx.profile != "full" else len(staff))]
    for year, month in month_iter(ctx.scale.finance_months):
        payroll, _ = BangLuongThang.objects.get_or_create(
            thang=month,
            nam=year,
            defaults={
                "ten_bang_luong": f"Digital Twin payroll {month:02d}/{year}",
                "ngay_chot_cong": date(year, month, 28 if month != 2 else 25),
                "trang_thai": BangLuongThang.TrangThai.CALCULATED,
                "nguoi_duyet": approver,
            },
        )
        periods.append(payroll)
        for person in active_staff:
            hours = random.choice([192, 204, 216, 228, 240])
            base = Decimal(str(hours * random.randint(30000, 45000)))
            allowance = Decimal(str(random.randint(0, 1500000)))
            deductions = Decimal(str(random.randint(0, 800000)))
            net = base + allowance - deductions
            _, created = ChiTietLuong.objects.get_or_create(
                bang_luong=payroll,
                nhan_vien=person,
                defaults={
                    "tong_gio_lam": hours,
                    "so_ngay_nghi": random.randint(0, 3),
                    "luong_chinh": base,
                    "thuong_chuyen_can": Decimal(str(random.choice([0, 500000, 1000000]))),
                    "phu_cap_khac": allowance,
                    "phat_vi_pham": deductions,
                    "thuc_lanh": max(Decimal("0"), net),
                    "nguon_du_lieu_snapshot": {"source": "digital_twin", "hours": hours},
                    "reconciliation_note": "Digital Twin payroll reconciliation sample",
                },
            )
            detail_count += int(created)
        payroll.update_totals()
    ctx.count("payroll_periods", len(periods))
    ctx.count("payslips_created", detail_count)
    ctx.write_jsonl("finance/ar_invoices.jsonl", ({
        "invoice_code": ctx.code("INV", i),
        "month_index": i,
        "amount": random.randint(80, 900) * 1_000_000,
        "status": random.choice(["DRAFT", "ISSUED", "PAID", "OVERDUE"]),
    } for i in range(1, ctx.scale.finance_months * 80 + 1)))
    return {"periods": periods}
