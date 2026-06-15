# Generated for SCMD Pro migration-state alignment after Phase 0 hardening.

import core.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0013_rename_operations__tenant__5e5d69_idx_operations__tenant__632773_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="baocaodexuat",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="baocaosuco",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="calamviec",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="chamcong",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="chamcongadjustment",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="kiemtraquanso",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="phancongcatruc",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="vitrichot",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
    ]
