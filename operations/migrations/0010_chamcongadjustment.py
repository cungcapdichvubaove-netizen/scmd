import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0007_payroll_state_policy_and_snapshot"),
        ("operations", "0009_alter_baocaosuco_ma_su_co"),
        ("users", "0006_nhanvien_fcm_token_nhanvien_ngay_nghi_viec_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChamCongAdjustment",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                (
                    "tenant_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name="Tenant ID"),
                ),
                ("ly_do", models.TextField(verbose_name="Lý do điều chỉnh")),
                (
                    "truoc_dieu_chinh",
                    models.JSONField(blank=True, default=dict, verbose_name="Dữ liệu trước chỉnh sửa"),
                ),
                (
                    "sau_dieu_chinh",
                    models.JSONField(blank=True, default=dict, verbose_name="Dữ liệu sau chỉnh sửa"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "bang_luong",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attendance_adjustments",
                        to="accounting.bangluongthang",
                        verbose_name="Kỳ lương liên quan",
                    ),
                ),
                (
                    "cham_cong",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adjustments",
                        to="operations.chamcong",
                        verbose_name="Bản ghi chấm công",
                    ),
                ),
                (
                    "nguoi_dieu_chinh",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cham_cong_adjustments",
                        to="users.nhanvien",
                        verbose_name="Người điều chỉnh",
                    ),
                ),
            ],
            options={
                "verbose_name": "Điều chỉnh chấm công",
                "verbose_name_plural": "4B. Điều chỉnh chấm công",
                "ordering": ["-created_at"],
            },
        ),
    ]
