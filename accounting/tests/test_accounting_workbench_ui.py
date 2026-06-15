# -*- coding: utf-8 -*-
"""Static regression coverage for the Accounting Workbench dashboard."""

from pathlib import Path

from django.test import SimpleTestCase


DASHBOARD_TEMPLATE = Path("accounting/templates/accounting/dashboard.html")
ACCOUNTING_VIEW = Path("accounting/views.py")
DASHBOARD_CSS = Path("static/common/css/dashboard_modules.css")


class AccountingWorkbenchUITests(SimpleTestCase):
    def test_dashboard_copy_is_action_or_status_only(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        views = ACCOUNTING_VIEW.read_text(encoding="utf-8")
        css = DASHBOARD_CSS.read_text(encoding="utf-8")
        combined = "\n".join([template, views, css])
        forbidden_copy = [
            "Màn hình làm việc cho kế toán",
            "Theo dõi trạng thái",
            "Các phiếu thu/chi mới nhất",
            "Thu/chi đã duyệt theo tháng",
            "Hạng mục phát sinh",
            "Hệ thống sẽ quét chấm công",
            "Đã tải xong — không có mục kế toán đang mở",
        ]
        for phrase in forbidden_copy:
            self.assertNotIn(phrase, combined)

    def test_work_queue_is_table_first_with_required_columns(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('class="acct-workspace"', template)
        self.assertIn("acct-workqueue-table", template)
        for column in ["Mức", "Nghiệp vụ", "Hồ sơ", "Giá trị", "Trạng thái", "Hạn", "CTA"]:
            self.assertIn(f"<th>{column}</th>", template)
        self.assertIn("{{ item.status }}", template)
        self.assertIn('{{ item.due_label|default:"—" }}', template)
        self.assertIn("{{ item.cta }}", template)

    def test_duplicate_workstrip_and_explainer_classes_are_removed(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("scmd-workstrip", template)
        self.assertNotIn("acct-subtitle", template)
        self.assertNotIn("acct-panel-subtitle", template)
        self.assertIn("acct-kpi-strip", template)
        self.assertIn("{% if utility_cards %}", template)
        self.assertNotIn('<h1 class="acct-title">', template)

    def test_view_provides_status_cta_kpi_and_does_not_mutate_business_data(self):
        source = ACCOUNTING_VIEW.read_text(encoding="utf-8")
        self.assertIn("'status': 'Cảnh báo'", source)
        self.assertIn("'cta': 'Xem'", source)
        self.assertIn("'due_label':", source)
        self.assertIn("ACCOUNTING_DASHBOARD_UI_VERSION", source)
        self.assertIn("deduction_scope_label", source)
        self.assertNotIn("'type': 'Đối soát khấu trừ'", source)
        self.assertIn("Mở kỳ lương chờ phát hành", source)
        self.assertIn("'cta': 'Mở phiếu'", source)
        dashboard_source = source[
            source.index("def dashboard_accounting"):source.index(
                "@login_required",
                source.index("def dashboard_accounting"),
            )
        ]
        forbidden_mutations = [".create(", ".bulk_create(", ".save(", ".delete(", ".update("]
        for token in forbidden_mutations:
            self.assertNotIn(token, dashboard_source)
