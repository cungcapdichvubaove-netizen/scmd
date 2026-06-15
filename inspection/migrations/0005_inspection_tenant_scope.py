# Generated for SCMD Pro architecture hardening on 2026-06-08

import uuid

from django.conf import settings
from django.db import migrations, models


SCOPED_MODELS = [
    "LoaiTuanTra",
    "DiemTuanTra",
    "LuotTuanTra",
    "GhiNhanTuanTra",
    "HangMucKiemTra",
    "BienBanThanhTra",
    "KetQuaKiemTra",
    "BuoiHuanLuyen",
    "BienBanViPham",
    "DotThanhTra",
]


def organization_id():
    return getattr(
        settings,
        "SCMD_ORGANIZATION_ID",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )


def populate_inspection_tenant_id(apps, schema_editor):
    org_id = organization_id()
    for model_name in SCOPED_MODELS:
        Model = apps.get_model("inspection", model_name)
        Model.objects.all().update(tenant_id=org_id)


def noop_reverse(apps, schema_editor):
    # tenant_id is organization scope metadata; do not erase it on reverse.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("inspection", "0004_unique_patrol_evidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="loaituantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="diemtuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="luottuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="ghinhantuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="hangmuckiemtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="bienbanthanhtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="ketquakiemtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="buoihuanluyen",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="bienbanvipham",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AddField(
            model_name="dotthanhtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.RunPython(populate_inspection_tenant_id, noop_reverse),
        migrations.AddIndex(
            model_name="loaituantra",
            index=models.Index(fields=["tenant_id", "muc_tieu", "ten_loai"], name="insp_ltt_tenant_mt_name_idx"),
        ),
        migrations.AddIndex(
            model_name="luottuantra",
            index=models.Index(fields=["tenant_id", "trang_thai", "thoi_gian_bat_dau"], name="insp_luot_tenant_state_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="ghinhantuantra",
            index=models.Index(fields=["tenant_id", "thoi_gian_quet"], name="insp_gn_tenant_scan_idx"),
        ),
        migrations.AddIndex(
            model_name="bienbanvipham",
            index=models.Index(fields=["tenant_id", "trang_thai", "ngay_vi_pham"], name="insp_vp_tenant_state_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="dotthanhtra",
            index=models.Index(fields=["tenant_id", "ket_qua", "thoi_gian_den"], name="insp_dtt_tenant_result_dt_idx"),
        ),
    ]
