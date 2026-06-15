# -*- coding: utf-8 -*-
"""
Legacy compatibility module.

Alive Check SSOT now lives in `operations.models.KiemTraQuanSo`.
This module exists only to preserve old imports while the codebase converges.
"""

from operations.models import KiemTraQuanSo

__all__ = ["KiemTraQuanSo"]
