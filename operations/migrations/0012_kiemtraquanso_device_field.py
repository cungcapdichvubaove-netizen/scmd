# Generated manually for alive check audit hardening.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0011_operations_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="kiemtraquanso",
            name="device_id_xac_thuc",
            field=models.CharField(
                blank=True,
                help_text="Mã thiết bị đã dùng để phản hồi Alive Check.",
                max_length=255,
                null=True,
                verbose_name="Thiết bị xác thực",
            ),
        ),
    ]
