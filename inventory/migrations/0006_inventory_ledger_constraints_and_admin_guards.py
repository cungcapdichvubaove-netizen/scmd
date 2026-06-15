# Generated manually for inventory ledger hardening.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_inventoryledgerentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryledgerentry",
            name="chi_tiet_phieu_nhap",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="ledger_entries",
                to="inventory.chitietphieunhap",
                verbose_name="Chi tiết phiếu nhập liên quan",
            ),
        ),
        migrations.AddField(
            model_name="inventoryledgerentry",
            name="chi_tiet_phieu_xuat",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="ledger_entries",
                to="inventory.chitietphieuxuat",
                verbose_name="Chi tiết phiếu xuất liên quan",
            ),
        ),
        migrations.AddConstraint(
            model_name="inventoryledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(chi_tiet_phieu_nhap__isnull=False),
                fields=("chi_tiet_phieu_nhap", "movement_type"),
                name="inventory_ledger_unique_receipt_detail_movement",
            ),
        ),
        migrations.AddConstraint(
            model_name="inventoryledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(chi_tiet_phieu_xuat__isnull=False),
                fields=("chi_tiet_phieu_xuat", "movement_type"),
                name="inventory_ledger_unique_issue_detail_movement",
            ),
        ),
    ]
