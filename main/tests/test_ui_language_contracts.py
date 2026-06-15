from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class UILanguageContractTests(unittest.TestCase):
    def test_no_legacy_war_room_or_cyber_asset_filenames(self):
        roots = [ROOT / "static", ROOT / "staticfiles"]
        offenders = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {".js", ".css"}:
                    continue
                lowered = path.name.lower()
                if "war" + "_room" in lowered or "war-room" in lowered or "cy" + "ber" in lowered:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], "Brand Contract Violation: Legacy terminology detected in asset filenames.")

    def test_owned_static_assets_do_not_reintroduce_cyber_visual_language(self):
        offenders = []
        for root in [ROOT / "static"]:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {".js", ".css"}:
                    continue
                if "vendor" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
                for token in ("War " + "Room", "war" + "_room", "Cy" + "ber", "cy" + "ber", "--scmd-cyan", "Ne" + "on", "ne" + "on"):
                    if token in text:
                        offenders.append(f"{path.relative_to(ROOT)}::{token}")
        self.assertEqual(offenders, [], "Brand Contract Violation: Forbidden legacy visual language detected in static assets.")

    def test_dashboard_templates_follow_sentence_case_contract(self):
        roots = [
            ROOT / "dashboard" / "templates",
            ROOT / "operations" / "templates" / "operations",
            ROOT / "accounting" / "templates" / "accounting",
            ROOT / "clients" / "templates" / "clients",
            ROOT / "inventory" / "templates" / "inventory",
            ROOT / "inspection" / "templates" / "inspection",
            ROOT / "users" / "templates" / "users",
            ROOT / "reports" / "templates" / "reports",
        ]
        offenders = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*dashboard*.html"):
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
                if "text-transform: uppercase" in text or " uppercase tracking" in text:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], "Dashboard UI should not force broad uppercase styling")

    def test_admin_console_visible_copy_is_localized(self):
        checked = [
            ROOT / "templates" / "admin" / "index.html",
            ROOT / "templates" / "admin" / "auth" / "user" / "change_list.html",
            ROOT / "templates" / "admin" / "auth" / "group" / "change_list.html",
            ROOT / "templates" / "partials" / "sidebar_menu_items.html",
        ]
        offenders = []
        for path in checked:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            for token in ("SCMD Pro Technical Console", "Technical Console", ">Dashboard<", "Admin Taxonomy"):
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)}::{token}")
        self.assertEqual(offenders, [], "Admin-visible copy must be localized per ADMIN_LOCALIZATION_AUDIT.md")
