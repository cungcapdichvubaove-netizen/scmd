"""Static contract tests for the Digital Twin dataset generator."""

from pathlib import Path

from django.test import SimpleTestCase


class DigitalTwinStaticContractTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]

    def test_required_seed_tree_exists(self):
        required = [
            "seed/master-data",
            "seed/hr",
            "seed/customers",
            "seed/contracts",
            "seed/sites",
            "seed/inventory",
            "seed/patrol",
            "seed/incidents",
            "seed/ai-alerts",
            "seed/finance",
            "seed/realtime",
            "seed/orchestrator",
        ]
        for relative in required:
            self.assertTrue((self.root / relative).exists(), relative)

    def test_management_commands_exist(self):
        for name in [
            "digital_twin_seed.py",
            "digital_twin_reset.py",
            "digital_twin_benchmark.py",
            "digital_twin_realtime.py",
        ]:
            self.assertTrue((self.root / "main" / "management" / "commands" / name).exists(), name)

    def test_no_real_personal_domains_in_seed_code(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (self.root / "seed").rglob("*.py"))
        self.assertIn("scmdpro.local", combined)
        self.assertNotIn("gmail.com", combined.lower())
        self.assertNotIn("yahoo.com", combined.lower())

    def test_docs_exist(self):
        for name in ["DATASET_ARCHITECTURE.md", "SEED_EXECUTION_GUIDE.md", "DATA_COVERAGE_REPORT.md"]:
            self.assertTrue((self.root / "docs" / name).exists(), name)


class DigitalTwinSideEffectSuppressionContractTests(SimpleTestCase):
    def test_seed_command_suppresses_operational_side_effects_by_default(self):
        command_source = Path("main/management/commands/digital_twin_seed.py").read_text(encoding="utf-8")
        context_source = Path("seed/orchestrator/context.py").read_text(encoding="utf-8")
        runner_source = Path("seed/orchestrator/runner.py").read_text(encoding="utf-8")
        side_effect_source = Path("seed/orchestrator/side_effects.py").read_text(encoding="utf-8")

        self.assertIn("--allow-side-effects", command_source)
        self.assertIn("suppress_side_effects: bool = True", context_source)
        self.assertIn("suppress_operational_side_effects(ctx.suppress_side_effects)", runner_source)
        self.assertIn("handle_su_co_changes", side_effect_source)
        self.assertIn("process_new_incident_alert", Path("operations/signals.py").read_text(encoding="utf-8"))
        self.assertNotIn("process_new_incident_alert.delay", side_effect_source)
