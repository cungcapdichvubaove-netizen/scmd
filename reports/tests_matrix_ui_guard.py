# -*- coding: utf-8 -*-
"""Regression coverage for the monthly attendance matrix UI guard."""

from __future__ import annotations

from uuid import UUID

from django.test import SimpleTestCase, TestCase, override_settings

from reports.application.report_use_cases import GetMonthlyAttendanceMatrixUseCase


ORG_ID = UUID("00000000-0000-0000-0000-000000000735")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class MonthlyAttendanceMatrixUIGuardTests(TestCase):
    def test_page_size_is_capped_and_large_page_notice_is_returned(self):
        context = GetMonthlyAttendanceMatrixUseCase.execute(
            1,
            2026,
            ORG_ID,
            filters={"page_size": "999"},
        )

        self.assertEqual(context["page_obj"].paginator.per_page, 200)
        self.assertIn("làm chậm trình duyệt", context["matrix_performance_notice"])
        self.assertIn("rendered_count", context["summary"])
        self.assertIn("employee_count", context["summary"])

    def test_small_page_size_does_not_show_large_page_notice(self):
        context = GetMonthlyAttendanceMatrixUseCase.execute(
            1,
            2026,
            ORG_ID,
            filters={"page_size": "50"},
        )

        self.assertEqual(context["page_obj"].paginator.per_page, 50)
        self.assertIsNone(context["matrix_performance_notice"])


class MonthlyAttendanceMatrixTemplateGuardTests(SimpleTestCase):
    def test_matrix_template_uses_notice_without_new_frontend_dependency(self):
        from pathlib import Path

        template_path = Path(__file__).resolve().parent / "templates" / "reports" / "tong_hop_cham_cong.html"
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("matrix_performance_notice", template_source)
        self.assertIn("data-testid=\"matrix-performance-notice\"", template_source)
        self.assertNotIn("TanStack", template_source)
        self.assertNotIn("DataTable", template_source)
