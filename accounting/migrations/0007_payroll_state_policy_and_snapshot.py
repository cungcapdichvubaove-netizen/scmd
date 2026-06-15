from django.db import migrations, models


def migrate_payroll_states(apps, schema_editor):
    BangLuongThang = apps.get_model("accounting", "BangLuongThang")
    state_map = {
        "NHAP": "DRAFT",
        "CHO_DUYET": "REVIEWED",
        "DA_PHAT_HANH": "LOCKED",
    }
    for old_state, new_state in state_map.items():
        BangLuongThang.objects.filter(trang_thai=old_state).update(trang_thai=new_state)


def reverse_payroll_states(apps, schema_editor):
    BangLuongThang = apps.get_model("accounting", "BangLuongThang")
    state_map = {
        "DRAFT": "NHAP",
        "REVIEWED": "CHO_DUYET",
        "LOCKED": "DA_PHAT_HANH",
    }
    for new_state, old_state in state_map.items():
        BangLuongThang.objects.filter(trang_thai=new_state).update(trang_thai=old_state)


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0006_alter_bangluongthang_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chitietluong",
            name="nguon_du_lieu_snapshot",
            field=models.JSONField(blank=True, default=dict, help_text="Dữ liệu đối soát nguồn tại thời điểm tính lương.", verbose_name="Snapshot dữ liệu nguồn"),
        ),
        migrations.AddField(
            model_name="chitietluong",
            name="reconciliation_note",
            field=models.TextField(blank=True, help_text="Giải thích thay đổi thực lãnh hoặc lần tính lại.", verbose_name="Ghi chú đối soát"),
        ),
        migrations.RunPython(migrate_payroll_states, reverse_payroll_states),
        migrations.AlterField(
            model_name="bangluongthang",
            name="trang_thai",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Dự thảo"),
                    ("CALCULATED", "Đã tính"),
                    ("REVIEWED", "Đã đối soát"),
                    ("LOCKED", "Đã khóa kỳ"),
                    ("PAID", "Đã thanh toán"),
                ],
                default="DRAFT",
                max_length=20,
                verbose_name="Trạng thái phê duyệt",
            ),
        ),
    ]
