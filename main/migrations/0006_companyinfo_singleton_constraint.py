# Generated for SCMD Pro CompanyInfo singleton hardening on 2026-06-08

from django.db import migrations, models


def dedupe_company_info_per_tenant(apps, schema_editor):
    CompanyInfo = apps.get_model("main", "CompanyInfo")
    tenant_ids = (
        CompanyInfo.objects.order_by()
        .values_list("tenant_id", flat=True)
        .distinct()
    )
    for tenant_id in tenant_ids:
        duplicates = list(
            CompanyInfo.objects.filter(tenant_id=tenant_id)
            .order_by("id")
            .values_list("id", flat=True)
        )
        if len(duplicates) <= 1:
            continue
        keep_id = duplicates[0]
        CompanyInfo.objects.filter(tenant_id=tenant_id).exclude(id=keep_id).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_companyinfo"),
    ]

    operations = [
        migrations.RunPython(dedupe_company_info_per_tenant, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="companyinfo",
            constraint=models.UniqueConstraint(fields=["tenant_id"], name="uq_companyinfo_one_per_org"),
        ),
    ]
