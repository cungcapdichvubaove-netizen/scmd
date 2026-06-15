# -*- coding: utf-8 -*-
"""Build a clean SCMD Pro source ZIP from the project root.

Use this for handoff/release packaging instead of zipping the working directory.
It excludes runtime residue, virtualenvs, local dependency folders, collected
static output, local media uploads, caches, logs, databases, temporary browser
profiles and generated patch ZIPs.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

WARNING_SIZE_BYTES = 30 * 1024 * 1024

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "node_modules",
    "staticfiles",
    "media",
    "tmp-edge-profile",
    "tmpedge2",
    "venv",
    ".venv",
    "env",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".sqlite3",
    ".db",
    ".zip",
}

EXCLUDED_NAMES = {
    ".env",
    "dump.rdb",
    "celerybeat-schedule",
    "celerybeat-schedule-shm",
    "celerybeat-schedule-wal",
}

EXCLUDED_PATHS = {
    Path("scripts/patrol_use_cases.py"),
}

EXCLUDED_PATH_PREFIXES = {
    Path("tools/dev_only"),
}


def is_under(path: Path, prefix: Path) -> bool:
    try:
        path.relative_to(prefix)
        return True
    except ValueError:
        return False


def should_include(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_DIRS:
        return False
    if path in EXCLUDED_PATHS:
        return False
    if any(is_under(path, prefix) for prefix in EXCLUDED_PATH_PREFIXES):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def _iter_clean_files(root: Path):
    """Yield clean source files while pruning excluded directories early."""

    for abs_path in sorted(root.rglob("*")):
        if not abs_path.is_file():
            continue
        rel_path = abs_path.relative_to(root)
        if not should_include(rel_path):
            continue
        yield abs_path, rel_path


def build(output: str = "scmd_pro_clean_source.zip") -> Path:
    root = Path(__file__).resolve().parent.parent
    output_path = root / output
    if output_path.exists():
        output_path.unlink()

    file_count = 0
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        for abs_path, rel_path in _iter_clean_files(root):
            zf.write(abs_path, rel_path.as_posix())
            file_count += 1

    zip_size = output_path.stat().st_size
    print(f"Clean source ZIP: {output_path}")
    print(f"Files included: {file_count}")
    print(f"ZIP size: {zip_size / (1024 * 1024):.2f} MB ({zip_size} bytes)")
    if zip_size > WARNING_SIZE_BYTES:
        print(
            "WARNING: Clean source ZIP is larger than 30 MB. "
            "Check for unexpected release artifacts before handoff."
        )
    return output_path


if __name__ == "__main__":
    build()
