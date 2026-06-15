# Generated for SCMD Pro migration-state alignment after Phase 0 hardening.

import core.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0011_soquy_tenant_scope"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="soquy",
            new_name="accounting__tenant__2028e6_idx",
            old_name="accounting_s_tenant_5e74d1_idx",
        ),
        migrations.AlterField(
            model_name="bangluongthang",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="cauhinhluong",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="chitietluong",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="phanhoiluong",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="soquy",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
    ]
