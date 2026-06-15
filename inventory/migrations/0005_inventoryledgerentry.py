# Generated manually for inventory ledger hardening.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_inventory_document_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(choices=[("RECEIPT", "Phiếu nhập"), ("ISSUE", "Phiếu xuất")], max_length=20)),
                ("movement_type", models.CharField(choices=[("POSTING", "Ghi sổ"), ("REVERSAL", "Đảo bút toán")], max_length=20)),
                ("direction", models.CharField(choices=[("IN", "Tăng tồn"), ("OUT", "Giảm tồn")], max_length=10)),
                ("quantity_delta", models.IntegerField(verbose_name="Biến động số lượng")),
                ("stock_before", models.IntegerField(verbose_name="Tồn trước giao dịch")),
                ("stock_after", models.IntegerField(verbose_name="Tồn sau giao dịch")),
                ("reason", models.TextField(blank=True, default="", verbose_name="Diễn giải đối soát")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("phieu_nhap", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="inventory.phieunhap", verbose_name="Phiếu nhập liên quan")),
                ("phieu_xuat", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="inventory.phieuxuat", verbose_name="Phiếu xuất liên quan")),
                ("vat_tu", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="inventory.vattu")),
            ],
            options={
                "verbose_name": "Ledger tồn kho",
                "verbose_name_plural": "6. Ledger tồn kho",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
