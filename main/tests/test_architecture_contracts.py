# -*- coding: utf-8 -*-
"""Regression checks for SCMD Pro architecture hardening contracts."""

import ast
from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ApplicationLayerImportContractTests(SimpleTestCase):
    def test_application_layer_does_not_use_wildcard_imports(self):
        offenders = []
        for path in sorted(PROJECT_ROOT.glob("*/application/*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                    module = node.module or "."
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}: from {module} import *")

        self.assertEqual(offenders, [], "Wildcard import is forbidden in application layer.")

    def test_application_layer_does_not_import_models_with_wildcard(self):
        offenders = []
        for path in sorted(PROJECT_ROOT.glob("*/application/*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.module == "models" or (node.level and node.module == "models"):
                    if any(alias.name == "*" for alias in node.names):
                        offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}: from .models import *")

        self.assertEqual(offenders, [], "Application layer must import explicit model symbols only.")


class TenantAwareManagerSSOTTests(SimpleTestCase):
    def test_tenant_aware_manager_is_defined_only_in_core_managers(self):
        offenders = []
        for path in sorted(PROJECT_ROOT.rglob("*.py")):
            if "migrations" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in {"TenantAwareManager", "OrganizationScopedManager"}:
                    rel_path = path.relative_to(PROJECT_ROOT).as_posix()
                    if rel_path != "core/managers.py":
                        offenders.append(f"{rel_path}:{node.lineno}:{node.name}")

        self.assertEqual(offenders, [], "Organization-scope managers must have a single SSOT in core/managers.py.")

    def test_domain_apps_import_tenant_manager_from_core_only(self):
        forbidden_patterns = (
            "class TenantAwareManager",
            "class OrganizationScopedManager",
            "from clients.models import TenantAwareManager",
            "from operations.models import TenantAwareManager",
            "from accounting.models import TenantAwareManager",
        )
        offenders = []
        for app_name in ("clients", "operations", "accounting"):
            for path in sorted((PROJECT_ROOT / app_name).rglob("*.py")):
                if "migrations" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                for pattern in forbidden_patterns:
                    if pattern in text:
                        offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {pattern!r}")

        self.assertEqual(offenders, [], "Organization-scope manager logic must not be duplicated in app modules.")


class AccessScopeDocsContractTests(SimpleTestCase):
    def test_access_delegation_docs_do_not_claim_deployment_when_app_is_missing(self):
        delegation_app_root = PROJECT_ROOT / "delegation"
        if delegation_app_root.exists():
            self.skipTest("delegation app exists; docs may describe deployed AccessDelegation implementation.")

        forbidden_claims = (
            "AccessDelegation is deployed in `delegation/models.py`",
            "AccessDelegation is deployed in delegation/models.py",
            "`AccessDelegation` is deployed in `delegation/models.py`",
        )

        offenders = []
        for path in sorted((PROJECT_ROOT / "docs" / "access_scope").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for claim in forbidden_claims:
                if claim in text:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {claim!r}")

        self.assertEqual(
            offenders,
            [],
            "Access scope docs must not claim AccessDelegation is already deployed while the delegation app is absent.",
        )
