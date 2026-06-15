# Generated for SCMD Pro release hardening on 2026-06-08

import uuid

from django.conf import settings
from django.db import migrations, models


def populate_soquy_tenant_id(apps, schema_editor):
    SoQuy = apps.get_model("accounting", "SoQuy")
    organization_id = getattr(
        settings,
        "SCMD_ORGANIZATION_ID",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    SoQuy.objects.all().update(tenant_id=organization_id)


def noop_reverse(apps, schema_editor):
    # tenant_id is organization scope metadata; do not erase it on reverse.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0010_alter_phanhoiluong_tenant_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="soquy",
            name="tenant_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                verbose_name="Tenant ID",
            ),
        ),
        migrations.RunPython(populate_soquy_tenant_id, noop_reverse),
        migrations.AddIndex(
            model_name="soquy",
            index=models.Index(fields=["tenant_id", "ngay_lap"], name="accounting_s_tenant_5e74d1_idx"),
        ),
    ]
