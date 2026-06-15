# Generated for SCMD Pro company profile SSOT on 2026-06-08

from django.db import migrations, models
import core.managers


def seed_default_company_info(apps, schema_editor):
    CompanyInfo = apps.get_model("main", "CompanyInfo")
    org_id = core.managers.organization_id()
    if not CompanyInfo.objects.filter(tenant_id=org_id).exists():
        CompanyInfo.objects.create(
            tenant_id=org_id,
            ten_cong_ty="CÔNG TY DỊCH VỤ BẢO VỆ SCMD",
            dia_chi="Chưa cấu hình địa chỉ công ty",
            dien_thoai="Chưa cấu hình số điện thoại",
            hotline="",
            email="",
            website="",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_alter_auditlog_tenant_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tenant_id", models.UUIDField(db_index=True, default=core.managers.organization_id, editable=False, verbose_name="Tenant ID")),
                ("ten_cong_ty", models.CharField(max_length=255, verbose_name="Tên công ty/đơn vị")),
                ("ten_phap_ly", models.CharField(blank=True, help_text="Nếu bỏ trống, hệ thống dùng Tên công ty/đơn vị trên mẫu biểu.", max_length=255, verbose_name="Tên pháp lý đầy đủ")),
                ("ma_so_thue", models.CharField(blank=True, max_length=32, verbose_name="Mã số thuế")),
                ("dia_chi", models.CharField(blank=True, max_length=255, verbose_name="Địa chỉ trụ sở")),
                ("dien_thoai", models.CharField(blank=True, max_length=32, verbose_name="Số điện thoại")),
                ("hotline", models.CharField(blank=True, max_length=32, verbose_name="Số điện thoại liên hệ/Hotline")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Email giao dịch")),
                ("website", models.URLField(blank=True, verbose_name="Website")),
                ("nguoi_dai_dien", models.CharField(blank=True, max_length=128, verbose_name="Người đại diện")),
                ("chuc_vu_nguoi_dai_dien", models.CharField(blank=True, max_length=128, verbose_name="Chức vụ người đại diện")),
                ("so_tai_khoan", models.CharField(blank=True, max_length=64, verbose_name="Số tài khoản")),
                ("ngan_hang", models.CharField(blank=True, max_length=128, verbose_name="Ngân hàng")),
                ("logo", models.ImageField(blank=True, help_text="Dùng cho header báo cáo/PDF nếu template hỗ trợ logo động.", null=True, upload_to="company/logos/%Y/", verbose_name="Logo dùng trên mẫu biểu")),
                ("ghi_chu", models.TextField(blank=True, verbose_name="Ghi chú nội bộ")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")),
            ],
            options={
                "verbose_name": "Thông tin công ty",
                "verbose_name_plural": "Thông tin công ty",
            },
        ),
        migrations.AddIndex(
            model_name="companyinfo",
            index=models.Index(fields=["tenant_id"], name="main_company_tenant_idx"),
        ),
        migrations.RunPython(seed_default_company_info, migrations.RunPython.noop),
    ]
