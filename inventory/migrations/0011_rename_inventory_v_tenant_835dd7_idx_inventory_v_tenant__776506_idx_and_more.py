# Generated for SCMD Pro migration-state alignment after Phase 0 hardening.

import core.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0010_inventory_document_and_ledger_tenant_scope"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="vattu",
            new_name="inventory_v_tenant__776506_idx",
            old_name="inventory_v_tenant_835dd7_idx",
        ),
        migrations.AlterField(
            model_name="chitietphieunhap",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="chitietphieuxuat",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="congcutaimuctieu",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="inventoryledgerentry",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="loaivattu",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="phieunhap",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="phieuxuat",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="vattu",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
    ]
