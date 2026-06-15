from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_inventory_ledger_constraints_and_admin_guards"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="inventoryledgerentry",
            index=models.Index(
                fields=["vat_tu", "-created_at"],
                name="inv_led_vt_cr_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="inventoryledgerentry",
            index=models.Index(
                fields=["phieu_nhap", "-created_at"],
                name="inv_led_pn_cr_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="inventoryledgerentry",
            index=models.Index(
                fields=["phieu_xuat", "-created_at"],
                name="inv_led_px_cr_idx",
            ),
        ),
    ]
