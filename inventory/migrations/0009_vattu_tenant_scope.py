# Generated for SCMD Pro release hardening on 2026-06-08

import uuid

from django.conf import settings
from django.db import migrations, models


def populate_vattu_tenant_id(apps, schema_editor):
    VatTu = apps.get_model("inventory", "VatTu")
    organization_id = getattr(
        settings,
        "SCMD_ORGANIZATION_ID",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    VatTu.objects.all().update(tenant_id=organization_id)


def noop_reverse(apps, schema_editor):
    # tenant_id is organization scope metadata; do not erase it on reverse.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0008_alter_chitietphieunhap_vat_tu_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vattu",
            name="tenant_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                verbose_name="Tenant ID",
            ),
        ),
        migrations.RunPython(populate_vattu_tenant_id, noop_reverse),
        migrations.AddIndex(
            model_name="vattu",
            index=models.Index(fields=["tenant_id", "so_luong_ton"], name="inventory_v_tenant_835dd7_idx"),
        ),
    ]
