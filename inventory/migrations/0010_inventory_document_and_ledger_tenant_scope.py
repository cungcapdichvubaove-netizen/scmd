# Generated for SCMD Pro architecture hardening on 2026-06-08

import uuid

from django.conf import settings
from django.db import migrations, models


SCOPED_MODELS = [
    "LoaiVatTu",
    "CongCuTaiMucTieu",
    "PhieuNhap",
    "ChiTietPhieuNhap",
    "PhieuXuat",
    "ChiTietPhieuXuat",
    "InventoryLedgerEntry",
]


def organization_id():
    return getattr(
        settings,
        "SCMD_ORGANIZATION_ID",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )


def populate_inventory_tenant_id(apps, schema_editor):
    org_id = organization_id()
    for model_name in SCOPED_MODELS:
        Model = apps.get_model("inventory", model_name)
        Model.objects.all().update(tenant_id=org_id)


def noop_reverse(apps, schema_editor):
    # tenant_id is organization scope metadata; do not erase it on reverse.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_vattu_tenant_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="loaivattu",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="congcutaimuctieu",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="phieunhap",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="chitietphieunhap",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="phieuxuat",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="chitietphieuxuat",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="inventoryledgerentry",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.RunPython(populate_inventory_tenant_id, noop_reverse),
        migrations.AddIndex(
            model_name="loaivattu",
            index=models.Index(fields=["tenant_id", "ten_loai"], name="inv_lvt_tenant_name_idx"),
        ),
        migrations.AddIndex(
            model_name="phieunhap",
            index=models.Index(fields=["tenant_id", "trang_thai", "ngay_nhap"], name="inv_pn_tenant_state_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="phieuxuat",
            index=models.Index(fields=["tenant_id", "trang_thai", "ngay_xuat"], name="inv_px_tenant_state_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="congcutaimuctieu",
            index=models.Index(fields=["tenant_id", "muc_tieu"], name="inv_cctmt_tenant_mt_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryledgerentry",
            index=models.Index(fields=["tenant_id", "vat_tu", "-created_at"], name="inv_led_tenant_vt_cr_idx"),
        ),
    ]
