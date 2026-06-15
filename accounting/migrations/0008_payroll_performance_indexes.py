"""
Production governance note for 0008_payroll_performance_indexes.

Backup:
- Capture a database backup/snapshot before applying on production because the
  target table (`BangLuongThang`) participates in payroll lock/reconciliation.

Rollback:
- Safe reverse is `migrate accounting 0007`; this migration only adds indexes
  and does not mutate payroll rows or snapshots.

Reconciliation:
- After deploy, verify payroll period counts are unchanged and confirm monthly
  payroll list/filter queries still resolve the same records for the same
  tenant/month/status combination.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0007_payroll_state_policy_and_snapshot"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="bangluongthang",
            index=models.Index(
                fields=["tenant_id", "nam", "thang"],
                name="accounting_b_tenant__44b6e0_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="bangluongthang",
            index=models.Index(
                fields=["tenant_id", "trang_thai", "nam", "thang"],
                name="accounting_b_tenant__956a8d_idx",
            ),
        ),
    ]
