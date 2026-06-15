# -*- coding: utf-8 -*-

from django.test import SimpleTestCase


class PayrollSnapshotContractTests(SimpleTestCase):
    def test_payroll_snapshot_contract_contains_rate_and_hours_fields(self):
        from pathlib import Path

        source = Path("accounting/services/payroll_calculation.py").read_text(encoding="utf-8")
        required_tokens = [
            '"schema_version": "payroll-detail-snapshot.v1"',
            '"schema_version": "payroll-attendance-rate-snapshot.v1"',
            '"gio_lam": str(gio_lam)',
            '"thuc_lam_gio": str(gio_lam)',
            '"don_gia_gio": str(don_gia_gio)',
            '"don_gia_hieu_luc_tu": rate_context["effective_date"].isoformat()',
            '"nguon_don_gia": rate_context["source"]',
            '"rate_record_id": rate_context["rate_record_id"]',
            '"rate_snapshot_count": len(attendance_snapshot)',
        ]
        for token in required_tokens:
            self.assertIn(token, source)
