from pathlib import Path
import zipfile

from django.test import SimpleTestCase


class OperationsAdminListCompactScopeTests(SimpleTestCase):
    """Static contract for scope-safe compact changelist patch.

    This patch must not touch operations/admin.py. It only swaps operation list
    templates and adds one shared CSS layer for the selected changelists.
    """

    ROOT = Path(__file__).resolve().parents[2]
    OPERATION_LISTS = [
        "phancongcatruc",
        "chamcong",
        "chamcongadjustment",
        "baocaosuco",
        "baocaodexuat",
        "kiemtraquanso",
    ]

    def test_selected_operations_templates_use_compact_css_and_keep_block_super(self):
        for model_name in self.OPERATION_LISTS:
            template = self.ROOT / "templates" / "admin" / "operations" / model_name / "change_list.html"
            content = template.read_text(encoding="utf-8")
            self.assertIn("common/css/admin_operations_compact.css", content)
            self.assertIn("scmd-op-header", content)
            self.assertIn("scmd-op-metrics", content)
            self.assertIn("{{ block.super }}", content)
            self.assertNotIn("scmd-admin-panel", content)
            self.assertNotIn("scmd-assignment-console", content)

    def test_compact_css_has_no_decorative_gradient_or_important(self):
        css = (self.ROOT / "static" / "common" / "css" / "admin_operations_compact.css").read_text(encoding="utf-8")
        self.assertNotIn("!important", css)
        self.assertNotIn("linear-gradient", css)
        self.assertNotIn("radial-gradient", css)
        self.assertNotIn("position: sticky;", css)
        self.assertIn("position: static", css)


    def test_compact_css_uses_standard_font_weight_scale(self):
        css = (self.ROOT / "static" / "common" / "css" / "admin_operations_compact.css").read_text(encoding="utf-8")
        for weight in ("720", "760", "780"):
            self.assertNotIn(f"font-weight: {weight}", css)
        self.assertIn("font-weight: 700", css)
        self.assertIn("font-weight: 800", css)

    def test_patch_zip_does_not_include_operations_admin_py_when_present(self):
        patch_zip = self.ROOT / "scmd_pro_operations_admin_lists_compact_scope_safe_patch.zip"
        if not patch_zip.exists():
            self.skipTest("Patch ZIP is not present inside source checkout.")
        with zipfile.ZipFile(patch_zip) as archive:
            self.assertNotIn("operations/admin.py", archive.namelist())
