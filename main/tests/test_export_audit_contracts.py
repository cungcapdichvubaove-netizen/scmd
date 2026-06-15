# -*- coding: utf-8 -*-

from pathlib import Path
from django.test import SimpleTestCase


class ExportAuditContractTests(SimpleTestCase):
    def test_export_views_use_central_audit_helpers(self):
        for path in [Path("reports/views.py"), Path("accounting/views.py")]:
            source = path.read_text(encoding="utf-8")
            self.assertIn("export_audit_log", source, msg=f"{path} must audit export views")
            self.assertIn("_enforce_export_access", source, msg=f"{path} must enforce export access")

    def test_payroll_admin_exports_are_execute_audited(self):
        source = Path("accounting/admin.py").read_text(encoding="utf-8")
        self.assertIn("Export CSV cấu hình lương từ Django Admin", source)
        self.assertIn("Export CSV phiếu lương cá nhân từ Django Admin", source)
        self.assertIn("action=AuditLog.Action.EXECUTE", source)
