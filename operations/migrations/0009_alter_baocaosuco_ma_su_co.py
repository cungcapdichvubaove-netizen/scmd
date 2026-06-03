from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0008_baocaodexuat_tenant_id_baocaosuco_tenant_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="baocaosuco",
            name="ma_su_co",
            field=models.CharField(
                editable=False,
                max_length=30,
                unique=True,
                verbose_name="Mã vụ việc",
            ),
        ),
    ]
