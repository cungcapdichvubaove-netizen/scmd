# -*- coding: utf-8 -*-
"""Static regression tests for report export performance guards."""

from __future__ import annotations

import inspect

from django.test import SimpleTestCase

from reports.services import ReportService


class ReportExportPerformanceContractTests(SimpleTestCase):
    def test_attendance_excel_uses_sargable_date_range(self):
        source = inspect.getsource(ReportService.generate_attendance_excel)
        self.assertNotIn("ngay_truc__month", source)
        self.assertNotIn("ngay_truc__year", source)
        self.assertIn("ngay_truc__gte", source)
        self.assertIn("ngay_truc__lt", source)

    def test_attendance_excel_keeps_scope_and_row_guard(self):
        source = inspect.getsource(ReportService.generate_attendance_excel)
        self.assertIn("ShiftVisibilityPolicy.visible_shifts", source)
        self.assertIn("SCMD_REPORT_ATTENDANCE_EXCEL_MAX_ROWS", source)
        self.assertIn("row_count", source)
