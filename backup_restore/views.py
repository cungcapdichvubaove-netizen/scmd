# file: backup_restore/views.py
"""Disabled web backup/restore surface for SCMD Pro.

Database backup/restore is a high-risk production operation and must be run by
controlled operations tooling, not an always-mounted web UI. The legacy view is
kept as an explicit disabled stub so stale links/tests fail closed instead of
silently exposing dumpdata/flush/loaddata from HTTP.
"""

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render


BACKUP_RESTORE_DISABLED_MESSAGE = (
    "Web backup/restore is disabled by production safety policy. "
    "Use controlled offline runbook tooling with operator approval."
)


def is_superuser(user):
    return bool(user and user.is_authenticated and user.is_superuser)


@user_passes_test(is_superuser)
def backup_restore_view(request):
    """Fail-closed compatibility view for the removed web backup/restore route."""
    if not getattr(settings, "ENABLE_BACKUP_RESTORE_WEB_UI", False):
        return HttpResponseForbidden(BACKUP_RESTORE_DISABLED_MESSAGE)

    # This branch is intentionally not wired in urls.py. If a future release
    # re-enables the feature, it must replace this stub with a hardened workflow
    # that has a separate approval gate, immutable audit trail, encrypted backup
    # storage and a restore runbook. Until then, render a disabled page only.
    return render(
        request,
        "backup_restore/main.html",
        {
            "web_restore_enabled": False,
            "backup_restore_disabled": True,
            "disabled_message": BACKUP_RESTORE_DISABLED_MESSAGE,
        },
        status=403,
    )
