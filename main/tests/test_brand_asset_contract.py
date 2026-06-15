# -*- coding: utf-8 -*-
"""Release contract for optimized SCMD Pro brand assets."""

from pathlib import Path

from django.test import SimpleTestCase


BRAND_DIR = Path("static/img/brand")


class BrandAssetContractTest(SimpleTestCase):
    def test_brand_svgs_do_not_embed_base64_png_payloads(self):
        offenders = []
        for path in BRAND_DIR.glob("*.svg"):
            source = path.read_text(encoding="utf-8", errors="ignore")
            if "data:image/png;base64" in source:
                offenders.append(str(path))

        self.assertEqual(offenders, [])


    def test_brand_svgs_do_not_contain_tagline_copy(self):
        forbidden_phrases = [
            "Security Command",
            "Security Command Center",
            "Security Command & Management Dashboard",
            "Dashboard",
        ]
        offenders = []
        for path in BRAND_DIR.glob("*.svg"):
            source = path.read_text(encoding="utf-8", errors="ignore")
            for phrase in forbidden_phrases:
                if phrase in source:
                    offenders.append(f"{path}: {phrase}")

        self.assertEqual(offenders, [])

    def test_report_png_assets_do_not_embed_tagline_metadata(self):
        forbidden_phrases = [
            b"Security Command",
            b"Security Command Center",
            b"Security Command & Management Dashboard",
            b"Dashboard",
        ]
        offenders = []
        for filename in ["report-header-logo.png", "report-watermark-symbol.png"]:
            payload = (BRAND_DIR / filename).read_bytes()
            for phrase in forbidden_phrases:
                if phrase in payload:
                    offenders.append(f"{filename}: {phrase.decode('utf-8')}")

        self.assertEqual(offenders, [])

    def test_brand_svg_size_budget(self):
        budgets = {
            "logo-symbol.svg": 12 * 1024,
            "logo-symbol-blue.svg": 12 * 1024,
            "logo-symbol-white.svg": 12 * 1024,
            "logo-symbol-black.svg": 12 * 1024,
            "favicon.svg": 8 * 1024,
            "loading-symbol.svg": 12 * 1024,
            "report-watermark-symbol.svg": 12 * 1024,
        }
        for name in [
            "logo-scmd-horizontal.svg",
            "logo-scmd-horizontal-white.svg",
            "logo-scmd-horizontal-black.svg",
            "logo-scmd-pro-horizontal.svg",
            "logo-scmd-pro-horizontal-white.svg",
            "logo-scmd-pro-horizontal-black.svg",
            "logo-scmd-pro-stacked.svg",
            "logo-scmd-pro-stacked-white.svg",
            "report-header-logo.svg",
        ]:
            budgets[name] = 30 * 1024

        failures = []
        for filename, max_size in budgets.items():
            path = BRAND_DIR / filename
            if not path.exists():
                failures.append(f"{filename}: missing")
                continue
            size = path.stat().st_size
            if size > max_size:
                failures.append(f"{filename}: {size} > {max_size}")

        self.assertEqual(failures, [])

    def test_pdf_report_templates_use_png_brand_assets(self):
        report_templates = [
            Path("reports/templates/reports/print/incident_pdf.html"),
            Path("templates/admin/users/nhanvien/print_profile.html"),
            Path("templates/admin/users/nhanvien/print_profile_bulk.html"),
            Path("users/templates/users/ly_lich_pdf.html"),
            Path("accounting/templates/accounting/admin/bang_luong_trinh_ky.html"),
        ]
        for template_path in report_templates:
            source = template_path.read_text(encoding="utf-8")
            self.assertNotIn("report-header-logo.svg", source)
            self.assertNotIn("report-watermark-symbol.svg", source)
