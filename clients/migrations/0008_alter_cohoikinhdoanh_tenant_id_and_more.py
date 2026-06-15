# Generated for SCMD Pro migration-state alignment after Phase 0 hardening.

import core.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0007_muctieudongiahistory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cohoikinhdoanh",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="hopdong",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="khachhangtiemnang",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="muctieudongiahistory",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
    ]
