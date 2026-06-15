from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, SimpleTestCase, override_settings

from backup_restore import urls as backup_urls
from backup_restore.views import BACKUP_RESTORE_DISABLED_MESSAGE, backup_restore_view


class BackupRestoreDisabledContractTest(SimpleTestCase):
    def test_backup_restore_has_no_web_urls_by_default(self):
        self.assertEqual(backup_urls.urlpatterns, [])

    @override_settings(ENABLE_BACKUP_RESTORE_WEB_UI=False)
    def test_backup_restore_view_fails_closed_when_called_directly(self):
        request = RequestFactory().get("/backup-restore/")
        request.user = User(username="admin", is_superuser=True, is_staff=True)

        response = backup_restore_view(request)

        self.assertEqual(response.status_code, 403)
        self.assertIn(BACKUP_RESTORE_DISABLED_MESSAGE.encode(), response.content)

    def test_backup_restore_view_still_requires_superuser(self):
        request = RequestFactory().get("/backup-restore/")
        request.user = AnonymousUser()

        response = backup_restore_view(request)

        self.assertEqual(response.status_code, 302)
