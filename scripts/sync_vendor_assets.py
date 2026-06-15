#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync pinned frontend vendor assets from node_modules into static/vendor."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_MODULES = ROOT / "node_modules"
STATIC_VENDOR = ROOT / "static" / "vendor"

FILES_TO_COPY = {
    "chart.js/dist/chart.umd.js": "chartjs/chart.umd.min.js",
    "jquery/dist/jquery.min.js": "jquery/jquery-3.7.0.min.js",
    "select2/dist/js/select2.min.js": "select2/select2.min.js",
    "select2/dist/css/select2.min.css": "select2/select2.min.css",
    "alpinejs/dist/cdn.min.js": "alpine/alpine.min.js",
    "html5-qrcode/html5-qrcode.min.js": "html5-qrcode/html5-qrcode.min.js",
    "@fortawesome/fontawesome-free/css/all.min.css": "fontawesome/css/all.min.css",
    "dexie/dist/dexie.min.js": "dexie/dexie.min.js",
    "htmx.org/dist/htmx.min.js": "htmx/htmx.min.js",
    "nprogress/nprogress.js": "nprogress/nprogress.min.js",
    "nprogress/nprogress.css": "nprogress/nprogress.css",
    "bootstrap/dist/js/bootstrap.bundle.min.js": "bootstrap/bootstrap.bundle.min.js",
}

DIRECTORIES_TO_COPY = {
    "@fortawesome/fontawesome-free/webfonts": "fontawesome/webfonts",
}


def copy_file(source_relative: str, destination_relative: str) -> None:
    source = NODE_MODULES / source_relative
    destination = STATIC_VENDOR / destination_relative
    if not source.exists():
        raise FileNotFoundError(f"Missing vendor source: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_directory(source_relative: str, destination_relative: str) -> None:
    source = NODE_MODULES / source_relative
    destination = STATIC_VENDOR / destination_relative
    if not source.exists():
        raise FileNotFoundError(f"Missing vendor source directory: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def main() -> int:
    for source_relative, destination_relative in FILES_TO_COPY.items():
        copy_file(source_relative, destination_relative)
    for source_relative, destination_relative in DIRECTORIES_TO_COPY.items():
        copy_directory(source_relative, destination_relative)
    print("Vendor assets synced to static/vendor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
