# -*- coding: utf-8 -*-
"""Static regression coverage for the Inventory Warehouse Workbench."""

from pathlib import Path

from django.test import SimpleTestCase


DASHBOARD_TEMPLATE = Path("inventory/templates/inventory/dashboard_kho.html")
INVENTORY_VIEW = Path("inventory/views.py")
DASHBOARD_CSS = Path("static/common/css/dashboard_modules.css")


class InventoryWorkbenchUITests(SimpleTestCase):
    def test_dashboard_copy_is_action_or_status_only(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        views = INVENTORY_VIEW.read_text(encoding="utf-8")
        css = DASHBOARD_CSS.read_text(encoding="utf-8")
        combined = "\n".join([template, views, css])
        forbidden_copy = [
            "Màn hình làm việc " + "cho thủ kho",
            "Ưu tiên chứng từ " + "nháp",
            "Các mã đã " + "chạm hoặc dưới mức tồn tối thiểu",
            "Theo dõi nhanh " + "phiếu nhập/xuất",
            "Theo dõi tổng " + "tồn",
            "Biến động " + "tồn kho",
            "Nhắc nhanh để " + "tránh sửa chứng từ",
            "Luồng kho " + "chuẩn",
        ]
        for phrase in forbidden_copy:
            self.assertNotIn(phrase, combined)

    def test_work_queue_is_table_first_with_required_columns(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("inv-workspace", template)
        self.assertIn("inv-workqueue-table", template)
        for column in ["Mức", "Nghiệp vụ", "Hồ sơ", "Đối tượng", "Trạng thái", "Hạn", "CTA"]:
            self.assertIn(f"<th>{column}</th>", template)
        self.assertIn("data-work-kind", template)
        self.assertIn("{{ item.status }}", template)
        self.assertIn("{{ item.due_label }}", template)
        self.assertIn("{{ item.cta }}", template)

    def test_legacy_dashboard_blocks_are_removed(self):
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("inv-eyebrow", template)
        self.assertNotIn("inv-subtitle", template)
        self.assertNotIn("scmd-workstrip", template)
        self.assertNotIn("inv-panel-subtitle", template)
        self.assertNotIn("inv-card-note", template)
        self.assertNotIn("Luồng kho " + "chuẩn", template)

    def test_view_uses_compact_dashboard_shapes(self):
        source = INVENTORY_VIEW.read_text(encoding="utf-8")
        self.assertIn("metric_cards = [", source)
        self.assertIn("utility_cards = []", source)
        self.assertIn('"business": "nhap"', source)
        self.assertIn('"business": "xuat"', source)
        self.assertIn('"business": "ton"', source)
        self.assertIn('"business": "ccht"', source)
        self.assertIn('"business": "khau-tru"', source)
        self.assertNotIn("flow_cards =", source)
        self.assertNotIn('"note": "', source)
