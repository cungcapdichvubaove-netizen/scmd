from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from unittest.mock import patch, MagicMock
from main.models import AuditLog
import tempfile
import os

class BackupRestoreViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.normal_user = User.objects.create_user('user', 'user@example.com', 'password')
        self.backup_restore_url = reverse('backup_restore:backup_restore_view')

        # Ensure SCMD_ORGANIZATION_ID is set for AuditLog
        settings.SCMD_ORGANIZATION_ID = 'd8f89835-f716-419b-9800-47b74403387c'

    def test_backup_requires_superuser(self):
        self.client.login(username='user', password='password')
        response = self.client.post(self.backup_restore_url, {'backup': 'true'})
        self.assertEqual(response.status_code, 302) # Redirected to login/permission denied
        self.assertIn('/admin/login/', response.url)

    @patch('django.core.management.call_command')
    def test_backup_success_and_audit_log(self, mock_call_command):
        self.client.login(username='admin', password='password')
        response = self.client.post(self.backup_restore_url, {'backup': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename="backup_'))
        mock_call_command.assert_called_with("dumpdata", stdout=MagicMock())
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.ACCESS, module="BackupRestore", user=self.superuser).exists())

    @patch('django.core.management.call_command')
    @patch('tempfile.mkdtemp', return_value=tempfile.gettempdir()) # Mock temp dir for cleanup
    def test_restore_disabled_by_default(self, mock_mkdtemp, mock_call_command):
        settings.ENABLE_WEB_RESTORE = False # Explicitly set to False
        self.client.login(username='admin', password='password')
        
        mock_file = SimpleUploadedFile("test_backup.json", b"{}", content_type="application/json")
        response = self.client.post(self.backup_restore_url, {'restore': 'true', 'restore_file': mock_file, 'confirm_action': 'CONFIRM_RESTORE'})
        
        self.assertEqual(response.status_code, 302) # Redirect to central_hub
        self.assertIn('BẢO MẬT: Tính năng phục hồi dữ liệu qua Web UI bị vô hiệu hóa', [m.message for m in messages.get_messages(response.wsgi_request)])
        mock_call_command.assert_not_called()

    @patch('django.core.management.call_command')
    @patch('tempfile.mkdtemp', return_value=tempfile.gettempdir())
    def test_restore_requires_confirmation(self, mock_mkdtemp, mock_call_command):
        settings.ENABLE_WEB_RESTORE = True
        self.client.login(username='admin', password='password')
        
        mock_file = SimpleUploadedFile("test_backup.json", b"{}", content_type="application/json")
        response = self.client.post(self.backup_restore_url, {'restore': 'true', 'restore_file': mock_file, 'confirm_action': 'WRONG_CONFIRMATION'})
        
        self.assertEqual(response.status_code, 200) # Renders the same page with error
        self.assertIn("Xác thực thất bại: Vui lòng nhập 'CONFIRM_RESTORE' để xác nhận thao tác xóa sạch dữ liệu.", [m.message for m in messages.get_messages(response.wsgi_request)])
        mock_call_command.assert_not_called()

    @patch('django.core.management.call_command')
    @patch('tempfile.mkdtemp', return_value=tempfile.gettempdir())
    def test_restore_success_and_audit_log(self, mock_mkdtemp, mock_call_command):
        settings.ENABLE_WEB_RESTORE = True
        self.client.login(username='admin', password='password')
        
        mock_file = SimpleUploadedFile("test_backup.json", b"{}", content_type="application/json")
        response = self.client.post(self.backup_restore_url, {'restore': 'true', 'restore_file': mock_file, 'confirm_action': 'CONFIRM_RESTORE'})
        
        self.assertEqual(response.status_code, 302) # Redirect to admin logout
        self.assertIn('/admin/logout/', response.url)
        
        # Ensure flush and loaddata were called, and a safety backup was made
        mock_call_command.assert_any_call("dumpdata", stdout=MagicMock()) # Safety backup
        mock_call_command.assert_any_call("flush", "--noinput")
        mock_call_command.assert_any_call("loaddata", os.path.join(tempfile.gettempdir(), "test_backup.json"))
        
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.EXECUTE, module="BackupRestore", user=self.superuser).exists())
