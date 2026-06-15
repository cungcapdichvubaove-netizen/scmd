from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]


class ViTriChotAdminCompactTemplateTests(SimpleTestCase):
    def test_vitrichot_changelist_is_table_first_and_no_duplicate_object_tools(self):
        template = (ROOT / "templates/admin/operations/vitrichot/change_list.html").read_text(encoding="utf-8")

        self.assertIn("scmd-post-console--compact", template)
        self.assertIn("scmd-post-metrics--compact", template)
        self.assertIn("{% block object-tools %}{% endblock %}", template)
        self.assertIn("{{ block.super }}", template)
        # No large hero-style title or hint block
        self.assertNotIn("scmd-post-hint", template)
        self.assertNotIn("scmd_post_links.operations_dashboard", template)
        # h2 used (not h1) — admin pages have a h1 in the base template
        self.assertIn("scmd-post-title", template)
        self.assertNotIn("<h1 class=\"scmd-post-title\"", template)
        # Link guards: buttons only rendered when URL resolved
        self.assertIn("scmd_post_links.add_post != '#'", template)
        # Default filter for zero-safe stats
        self.assertIn('|default:"0"', template)

    def test_vitrichot_admin_has_scope_filter_and_context_provider(self):
        source = (ROOT / "operations/admin.py").read_text(encoding="utf-8")

        self.assertIn("class ViTriChotQualityFilter", source)
        self.assertIn("change_list_template = 'admin/operations/vitrichot/change_list.html'", source)
        self.assertIn("PostVisibilityPolicy.visible_posts(request.user)", source)
        self.assertIn("scmd_post_stats", source)
        self.assertIn("post_quality", source)
        self.assertNotIn("list_display = ('ten_vi_tri', 'get_muc_tieu', 'get_dia_chi')", source)

    def test_vitrichot_compact_css_uses_existing_tokens(self):
        css = (ROOT / "static/common/css/operations_ux.css").read_text(encoding="utf-8")
        marker = "/* Compact Vị trí chốt admin — table-first, no hero/banner. */"
        self.assertIn(marker, css)
        compact_css = css.split(marker, 1)[1]

        # Base classes must exist
        self.assertIn(".scmd-post-head {", css)
        self.assertIn(".scmd-post-btn {", css)
        self.assertIn(".scmd-post-metric {", css)
        self.assertIn(".scmd-post-note {", css)
        self.assertIn(".scmd-post-metrics {", css)

        # Compact overrides must exist
        self.assertIn(".scmd-post-head--compact", compact_css)
        self.assertIn(".scmd-post-metrics--compact", compact_css)

        # No marketing patterns
        self.assertNotIn("linear-gradient", compact_css)
        self.assertNotIn("!important", compact_css)
        self.assertIn("var(--scmd-radius-sm)", compact_css)

        # Responsive breakpoints present
        self.assertIn("@media (max-width: 760px)", compact_css)
        self.assertIn("@media (max-width: 520px)", compact_css)
