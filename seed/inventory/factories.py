"""Inventory factories.

SCMD Pro currently has stock categories/items, receipt/issue documents and
site-held tools, but no first-class Warehouse or serialised AssetUnit model.
The generator therefore creates native inventory records and exports synthetic
warehouse/serial-unit history as JSONL linked to real `MucTieu`/`VatTu` ids.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from inventory.models import ChiTietPhieuNhap, ChiTietPhieuXuat, CongCuTaiMucTieu, LoaiVatTu, PhieuNhap, PhieuXuat, VatTu
from seed.orchestrator.utils import decimal_vnd

CATEGORIES = ["Bộ đàm", "Điện thoại", "Camera", "Đồng phục", "Máy tuần tra", "Máy tính", "Thiết bị mạng", "Công cụ hỗ trợ"]
ITEMS = {
    "Bộ đàm": ["Bộ đàm UHF", "Pin bộ đàm", "Tai nghe bộ đàm"],
    "Điện thoại": ["Điện thoại tuần tra", "SIM dữ liệu", "Sạc nhanh"],
    "Camera": ["Camera thân", "Camera IP", "Thẻ nhớ camera"],
    "Đồng phục": ["Áo bảo vệ", "Quần bảo vệ", "Mũ kêpi", "Giày bảo vệ"],
    "Máy tuần tra": ["Máy tuần tra QR", "Đầu đọc NFC", "Dock sạc"],
    "Máy tính": ["Laptop SOC", "Mini PC", "Màn hình giám sát"],
    "Thiết bị mạng": ["Router 4G", "Switch PoE", "Access Point"],
    "Công cụ hỗ trợ": ["Gậy cao su", "Đèn pin", "Áo phản quang"],
}


def seed_inventory(ctx, hr, site_data):
    categories = []
    items = []
    for category_name in CATEGORIES:
        category, _ = LoaiVatTu.objects.get_or_create(ten_loai=f"DT - {category_name}", defaults={"mo_ta": "Digital Twin inventory category"})
        categories.append(category)
        for item_name in ITEMS[category_name]:
            sku_index = len(items) + 1
            item, _ = VatTu.objects.get_or_create(
                ten_vat_tu=f"{ctx.code('SKU', sku_index)} - {item_name}",
                defaults={
                    "loai_vat_tu": category,
                    "don_vi_tinh": "Cái" if category_name != "Đồng phục" else "Bộ",
                    "gia_nhap": decimal_vnd(random.randint(150, 5500) * 1000),
                    "gia_ban": decimal_vnd(random.randint(180, 6500) * 1000),
                    "so_luong_ton": random.randint(300, 2500),
                    "muc_canh_bao": random.randint(20, 80),
                },
            )
            items.append(item)

    storekeepers = [s for s in hr["staff"] if s.chuc_danh and s.chuc_danh.ten_chuc_danh == "Thủ kho"] or hr["staff"][:5]
    receipt_count = max(20, min(800, ctx.scale.asset_units // 50))
    issue_count = max(20, min(1200, ctx.scale.asset_units // 40))
    receipts = []
    issues = []

    for i in range(1, receipt_count + 1):
        receipt, _ = PhieuNhap.objects.get_or_create(
            ma_phieu=ctx.code("PN", i),
            defaults={"nguoi_nhap": random.choice(storekeepers), "ghi_chu": "Digital Twin receipt", "trang_thai": PhieuNhap.TrangThai.DRAFT},
        )
        receipts.append(receipt)
        for item in random.sample(items, k=min(3, len(items))):
            ChiTietPhieuNhap.objects.get_or_create(
                phieu_nhap=receipt,
                vat_tu=item,
                defaults={"so_luong": random.randint(5, 80), "don_gia": item.gia_nhap},
            )

    for i in range(1, issue_count + 1):
        issue_type = random.choice(["CAP_PHAT", "BAN_TRU_LUONG", "CONG_CU"])
        site = random.choice(site_data["sites"])
        staff = random.choice(hr["staff"])
        issue, _ = PhieuXuat.objects.get_or_create(
            ma_phieu=ctx.code("PX", i),
            defaults={
                "loai_xuat": issue_type,
                "nhan_vien_nhan": staff if issue_type != "CONG_CU" else None,
                "muc_tieu_nhan": site if issue_type == "CONG_CU" else None,
                "ghi_chu": "Digital Twin issue",
                "trang_thai": PhieuXuat.TrangThai.DRAFT,
            },
        )
        issues.append(issue)
        for item in random.sample(items, k=min(2, len(items))):
            ChiTietPhieuXuat.objects.get_or_create(
                phieu_xuat=issue,
                vat_tu=item,
                defaults={"so_luong": random.randint(1, 6), "don_gia_ban": item.gia_ban},
            )

    for site in site_data["sites"]:
        for item in random.sample(items, k=min(4, len(items))):
            CongCuTaiMucTieu.objects.get_or_create(
                muc_tieu=site,
                vat_tu=item,
                defaults={"so_luong_dang_giu": random.randint(1, 20)},
            )

    warehouses = []
    site_ids = [s.id for s in site_data["sites"]]
    for i in range(1, ctx.scale.warehouses + 1):
        scope = "HEADQUARTER" if i == 1 else ("BRANCH" if i <= 4 else "SITE")
        warehouses.append({
            "code": ctx.code("WH", i),
            "scope": scope,
            "site_id": None if scope != "SITE" else site_ids[(i - 5) % len(site_ids)],
            "name": f"Kho {scope.lower()} {i:03d}",
        })
    ctx.write_jsonl("inventory/warehouses.jsonl", warehouses)

    serial_rows = []
    for i in range(1, ctx.scale.asset_units + 1):
        item = items[(i - 1) % len(items)]
        site = site_data["sites"][(i - 1) % len(site_data["sites"])]
        serial_rows.append({
            "serial": f"DT-ASSET-{i:08d}",
            "vat_tu_id": item.id,
            "site_id": site.id,
            "status": random.choice(["IN_STOCK", "ASSIGNED", "IN_REPAIR", "RETIRED"]),
            "issued_at": str(date.today() - timedelta(days=random.randint(0, 900))),
        })
    ctx.write_jsonl("inventory/asset_units.jsonl", serial_rows)

    ctx.count("inventory_categories", len(categories))
    ctx.count("inventory_skus", len(items))
    ctx.count("warehouse_snapshots", len(warehouses))
    ctx.count("asset_unit_snapshots", len(serial_rows))
    return {"categories": categories, "items": items, "receipts": receipts, "issues": issues}
