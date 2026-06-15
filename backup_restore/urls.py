# file: backup_restore/urls.py
<<<<<<< HEAD
"""Backup/restore web URLs are intentionally disabled.

Phase 0 production safety keeps the app installed for historical migrations and
admin grouping, but exposes no HTTP route. Future re-enable must add a hardened
runbook-backed view and tests in the same patch.
"""

from django.urls import path

app_name = "backup_restore"

urlpatterns: list = []
=======
from django.urls import path
# from . import views # Sẽ dùng trong tương lai

app_name = "backup_restore"

urlpatterns = [
    # Thêm các đường dẫn URL cho ứng dụng backup_restore của bạn ở đây trong tương lai
]
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
