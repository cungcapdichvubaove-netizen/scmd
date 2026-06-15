"""
Production governance note for 0011_operations_performance_indexes.

Backup:
- Capture a database backup/snapshot before applying on production because the
  indexed tables participate in attendance and incident operational truth.

Rollback:
- Safe reverse is `migrate operations 0010`; this migration only adds indexes
  and does not rewrite attendance or incident rows.

Reconciliation:
- After deploy, verify attendance month reports, check-in lookups, and incident
  status/date filters return the same row counts as pre-deploy baselines.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0010_chamcongadjustment"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="phancongcatruc",
            index=models.Index(
                fields=["tenant_id", "ngay_truc"],
                name="operations__tenant__68513a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="chamcong",
            index=models.Index(
                fields=["tenant_id", "thoi_gian_check_in"],
                name="operations__tenant__31fea6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="baocaosuco",
            index=models.Index(
                fields=["tenant_id", "trang_thai", "created_at"],
                name="operations__tenant__5e5d69_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="baocaosuco",
            index=models.Index(
                fields=["tenant_id", "created_at"],
                name="operations__tenant__7f68d2_idx",
            ),
        ),
    ]
