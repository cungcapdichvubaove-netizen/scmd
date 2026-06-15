# Generated for SCMD Pro migration-state alignment after Phase 0 hardening.

import core.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspection", "0005_inspection_tenant_scope"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="dotthanhtra",
            name="insp_dtt_tenant_result_dt_idx",
        ),
        migrations.AlterField(
            model_name="bienbanthanhtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="bienbanvipham",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="buoihuanluyen",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="diemtuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="dotthanhtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="ghinhantuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="hangmuckiemtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="ketquakiemtra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="loaituantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
        migrations.AlterField(
            model_name="luottuantra",
            name="tenant_id",
            field=models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID"),
        ),
    ]
