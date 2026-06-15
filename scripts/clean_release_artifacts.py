#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove generated local artifacts before packaging SCMD Pro.

Default mode removes only safe-to-regenerate outputs:
- Python bytecode/cache
- collected static output
- local test/coverage caches
- runtime logs
- temporary browser/runtime profiles

Uploaded media and node_modules are preserved unless explicitly requested.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAFE_DIRS = ("__pycache__", "staticfiles", ".pytest_cache", "htmlcov", "tmp-edge-profile", "tmpedge2")
SAFE_FILE_GLOBS = ("*.pyc", "*.log")
SKIP_DIR_PARTS = {".git", "venv", "node_modules"}


def should_skip_path(path: Path) -> bool:
    return bool(set(path.parts) & SKIP_DIR_PARTS)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Remove generated local artifacts before packaging SCMD Pro. "
            "Default mode keeps media and node_modules unless explicitly requested."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching artifacts without deleting them.",
    )
    parser.add_argument(
        "--include-media",
        action="store_true",
        help="Also remove media/ after explicit operator confirmation via this flag.",
    )
    parser.add_argument(
        "--include-node-modules",
        action="store_true",
        help="Also remove node_modules/ after explicit operator confirmation via this flag.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    removed_dirs = 0
    removed_files = 0
    dir_targets = [
        path
        for path in ROOT.rglob("*")
        if path.is_dir() and path.name in SAFE_DIRS and not should_skip_path(path)
    ]
    if args.include_media and (ROOT / "media").exists():
        dir_targets.append(ROOT / "media")
    if args.include_node_modules and (ROOT / "node_modules").exists():
        dir_targets.append(ROOT / "node_modules")

    for path in dir_targets:
        if args.dry_run:
            print(f"Would remove directory: {path}")
        else:
            shutil.rmtree(path)
        removed_dirs += 1

    file_targets = []
    for pattern in SAFE_FILE_GLOBS:
        file_targets.extend(
            path for path in ROOT.rglob(pattern) if path.is_file() and not should_skip_path(path)
        )

    for path in sorted(set(file_targets)):
        if args.dry_run:
            print(f"Would remove file: {path}")
        else:
            path.unlink()
        removed_files += 1
    verb = "Found" if args.dry_run else "Removed"
    print(f"{verb} directories: {removed_dirs}")
    print(f"{verb} files: {removed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
