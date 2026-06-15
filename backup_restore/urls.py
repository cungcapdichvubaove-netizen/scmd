# file: backup_restore/urls.py
"""Backup/restore web URLs are intentionally disabled.

Phase 0 production safety keeps the app installed for historical migrations and
admin grouping, but exposes no HTTP route. Future re-enable must add a hardened
runbook-backed view and tests in the same patch.
"""

from django.urls import path

app_name = "backup_restore"

urlpatterns: list = []
