from pathlib import Path

from django.test import SimpleTestCase
import re


ROOT = Path(__file__).resolve().parents[2]


class CaLamViecAdminCompactTemplateTests(SimpleTestCase):
    def test_calamviec_changelist_is_compact_and_no_duplicate_object_tools(self):
        template = (ROOT / "templates/admin/operations/calamviec/change_list.html").read_text(encoding="utf-8")

        self.assertIn("scmd-shift-page--repair", template)
        self.assertIn("scmd-shift-toolbar", template)
        self.assertIn("scmd-shift-kpis", template)
        self.assertIn("{% block object-tools %}{% endblock %}", template)
        self.assertIn("{{ block.super }}", template)
        self.assertNotIn("scmd-shift-head", template)
        # The old full-width grid class must not return; the compact modifier
        # ``scmd-shift-grid--compact`` is allowed and intentionally preserved.
        self.assertIsNone(re.search(r'class=["\'][^"\']*\bscmd-shift-grid\b(?!--)', template))
        self.assertIn("scmd-shift-note-compact", template)
        self.assertIsNone(re.search(r'class=["\'][^"\']*\bscmd-shift-note\b(?!-)', template))
        self.assertNotIn("<h1", template)

    def test_calamviec_admin_context_and_row_display_are_token_based(self):
        source = (ROOT / "operations/admin.py").read_text(encoding="utf-8")

        self.assertIn("class CaLamViecQualityFilter", source)
        self.assertIn("change_list_template = 'admin/operations/calamviec/change_list.html'", source)
        self.assertIn("scmd_shift_stats", source)
        self.assertIn("scmd-admin-cell scmd-shift-cell", source)
        self.assertIn("scmd-shift-row-actions", source)
        self.assertIn("scmd-shift-row-action", source)
        self.assertNotIn('<div style="min-width:220px;">', source)
        self.assertNotIn("font-weight:900;color:#0f172a", source)

    def test_calamviec_compact_css_uses_design_tokens(self):
        css = (ROOT / "static/common/css/operations_ux.css").read_text(encoding="utf-8")
        marker = "/* Compact Ca làm việc admin repair — dense, table-first, no hero/card stack. */"
        self.assertIn(marker, css)
        compact_css = css.split(marker, 1)[1]

        self.assertIn("body.model-calamviec.change-list", compact_css)
        self.assertIn(".scmd-shift-toolbar", compact_css)
        self.assertIn(".scmd-shift-kpis", compact_css)
        self.assertIn(".scmd-shift-row-action", compact_css)
        self.assertIn("var(--scmd-surface)", compact_css)
        self.assertNotIn("linear-gradient", compact_css)
        self.assertNotIn("!important", compact_css)
        self.assertNotIn("#0f172a", compact_css)
        self.assertIn("position: static", compact_css)
