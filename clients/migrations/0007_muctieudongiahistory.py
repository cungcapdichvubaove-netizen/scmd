# Generated manually for Phase 2 payroll retroactive rate snapshot support.

import decimal
import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0006_alter_muctieu_so_gio_mot_ngay_decimal"),
    ]

    operations = [
        migrations.CreateModel(
            name="MucTieuDonGiaHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tenant_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name="Tenant ID")),
                ("ngay_hieu_luc", models.DateField(help_text="Moc bat dau ap dung don gia cho payroll.", verbose_name="Ngay hieu luc")),
                ("luong_khoan_bao_ve", models.DecimalField(decimal_places=0, max_digits=12, verbose_name="Luong khoan dinh muc (Thang)")),
                (
                    "so_gio_mot_ngay",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.25"))],
                        verbose_name="Dinh muc gio truc/ngay",
                    ),
                ),
                ("ghi_chu", models.TextField(blank=True, verbose_name="Ghi chu doi soat")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "muc_tieu",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lich_su_don_gia",
                        to="clients.muctieu",
                        verbose_name="Muc tieu bao ve",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lich su don gia muc tieu",
                "verbose_name_plural": "5. Lich su don gia muc tieu",
                "ordering": ["ngay_hieu_luc", "id"],
                "unique_together": {("muc_tieu", "ngay_hieu_luc", "tenant_id")},
            },
        ),
    ]
