# -*- coding: utf-8 -*-
"""Build a clean SCMD Pro patch ZIP.

This script packages only the files intentionally changed by the Phase 0-5
hardening patch. It never zips the full working directory and always excludes
collected/runtime artifacts such as staticfiles/, __pycache__, media/, logs,
local databases and temporary browser profiles.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PATCH_FILES = [
    ".env.example",
    ".cursorrules",
    "cursorrules.md",
    "UI_SYSTEM_REFACTOR_SPEC.md",
    "scripts/build_clean_patch_zip.py",
    "scripts/build_clean_source_zip.py",
    "inspection/violation_use_cases.py",
    "config/roles.py",
    "scripts/release_contract_check.py",
    "users/views.py",
    "users/tests_phase0_security.py",
    "inspection/models.py",
    "inspection/migrations/0004_unique_patrol_evidence.py",
    "inspection/application/patrol_use_cases.py",
    "inspection/application/violation_use_cases.py",
    "inspection/tests_patrol_use_cases.py",
    "inspection/views.py",
    "operations/views.py",
]

EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "staticfiles",
    "media",
    "node_modules",
    ".pytest_cache",
    "htmlcov",
    "tmp-edge-profile",
    "tmpedge2",
}


def is_clean_relative_path(path: Path) -> bool:
    return not (set(path.parts) & EXCLUDED_PARTS)


def build(output: str = "scmd_pro_phase_0_5_patch.zip") -> Path:
    root = Path(__file__).resolve().parent.parent
    output_path = root / output
    if output_path.exists():
        output_path.unlink()

    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        for rel in PATCH_FILES:
            rel_path = Path(rel)
            abs_path = root / rel_path
            if not abs_path.exists():
                raise FileNotFoundError(f"Missing patch file: {rel}")
            if not is_clean_relative_path(rel_path):
                raise ValueError(f"Refusing to package excluded path: {rel}")
            zf.write(abs_path, rel)
    return output_path


if __name__ == "__main__":
    print(build())
