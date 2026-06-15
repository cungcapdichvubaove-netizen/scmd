# Generated for SCMD Pro payroll adjustment audit trail.

import core.managers
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0011_rename_user_regasg_tenant_staff_status_idx_usr_rasg_t_stf_stat_idx_and_more"),
        ("accounting", "0012_rename_accounting_s_tenant_5e74d1_idx_accounting__tenant__2028e6_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayrollAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tenant_id", models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID")),
                ("so_tien_dieu_chinh", models.DecimalField(decimal_places=0, help_text="Số dương là truy lĩnh/bổ sung; số âm là thu hồi/khấu trừ hồi tố.", max_digits=12, verbose_name="Số tiền điều chỉnh (+/-)")),
                ("ly_do", models.TextField(verbose_name="Lý do điều chỉnh")),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="Dữ liệu đối soát")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Thời điểm tạo")),
                ("bang_luong", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="adjustments", to="accounting.bangluongthang", verbose_name="Kỳ lương đã khóa/đã thanh toán")),
                ("chi_tiet_luong", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="adjustments", to="accounting.chitietluong", verbose_name="Phiếu lương liên quan")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payroll_adjustments_created", to=settings.AUTH_USER_MODEL, verbose_name="Người tạo điều chỉnh")),
                ("nhan_vien", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_adjustments", to="users.nhanvien", verbose_name="Nhân sự điều chỉnh")),
            ],
            options={
                "verbose_name": "Điều chỉnh lương hồi tố",
                "verbose_name_plural": "3. Điều chỉnh lương hồi tố",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="payrolladjustment",
            index=models.Index(fields=["tenant_id", "bang_luong", "created_at"], name="acc_adj_t_pay_created_idx"),
        ),
        migrations.AddIndex(
            model_name="payrolladjustment",
            index=models.Index(fields=["tenant_id", "nhan_vien", "created_at"], name="acc_adj_t_staff_created_idx"),
        ),
    ]
