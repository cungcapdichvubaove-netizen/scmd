# Generated manually for inventory document state hardening.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_alter_chitietphieunhap_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="phieunhap",
            name="trang_thai",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Nháp"),
                    ("POSTED", "Đã ghi sổ"),
                    ("VOIDED", "Đã hủy"),
                ],
                db_index=True,
                default="DRAFT",
                max_length=20,
                verbose_name="Trạng thái chứng từ",
            ),
        ),
        migrations.AddField(
            model_name="phieuxuat",
            name="trang_thai",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Nháp"),
                    ("POSTED", "Đã ghi sổ"),
                    ("VOIDED", "Đã hủy"),
                ],
                db_index=True,
                default="DRAFT",
                max_length=20,
                verbose_name="Trạng thái chứng từ",
            ),
        ),
    ]
