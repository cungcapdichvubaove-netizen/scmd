# -*- coding: utf-8 -*-
"""Static regression tests for executive dashboard query follow-up."""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase


class ExecutiveDashboardQueryContractTests(SimpleTestCase):
    def test_no_date_lookup_for_proposal_window(self):
        source = Path("dashboard/application/executive_dashboard.py").read_text(encoding="utf-8")
        self.assertNotIn("ngay_tao__date__gte", source)
        self.assertIn("ngay_tao__gte=proposal_window_start", source)

    def test_yesterday_status_detail_list_not_built(self):
        source = Path("dashboard/application/executive_dashboard.py").read_text(encoding="utf-8")
        self.assertNotIn("target_statuses_hom_qua = GetExecutiveDashboardUseCase._get_target_statuses", source)
        self.assertIn("_count_risky_targets_for_day", source)
