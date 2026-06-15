# Generated manually to keep payroll rate precision aligned with domain contract.

import decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0005_alter_cohoikinhdoanh_khach_hang_tiem_nang_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="muctieu",
            name="so_gio_mot_ngay",
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal("12.00"),
                help_text="Số giờ ca trực tiêu chuẩn. Hệ thống sẽ tự nhân với số ngày trong tháng.",
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(decimal.Decimal("0.25"))
                ],
                verbose_name="Định mức giờ trực/ngày",
            ),
        ),
    ]
