# -*- coding: utf-8 -*-
"""
Infrastructure helpers for field-level encryption.

This module intentionally keeps a small API surface so legacy imports can be
stabilized while the project converges on a single architecture contract.
"""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_fernet() -> Fernet:
    raw_key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_aes256(value: Optional[str]) -> str:
    if not value:
        return ""
    return _get_fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")


def decrypt_aes256(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return _get_fernet().decrypt(str(value).encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""
