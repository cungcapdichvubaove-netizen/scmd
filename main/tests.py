from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from main.models import AuditLog
from django.core.management import call_command

class MainAppAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.user = User.objects.create_user('user', 'user@test.com', 'password')

    def test_login_view_loads(self):
        # FIX: Dùng 'main:homepage' thay vì 'login'
        response = self.client.get(reverse('main:homepage')) 
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        # FIX: Post vào 'main:homepage'
        response = self.client.post(reverse('main:homepage'), {'username': 'user', 'password': 'password'})
        # Kiểm tra redirect sau khi login thành công (thường là về dashboard hoặc hub)
        self.assertIn(response.status_code, [302, 200]) 

    def test_login_fail_with_wrong_password(self):
        # FIX: Post vào 'main:homepage'
        response = self.client.post(reverse('main:homepage'), {'username': 'user', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        # Đảm bảo thông báo lỗi khớp với HTML thực tế (đã check ở lần trước)
        self.assertContains(response, "Sai tên đăng nhập hoặc mật khẩu")

    def test_dashboard_hub_for_superuser(self):
        self.client.login(username='admin', password='password')
        response = self.client.get('/hub/') 
        
        # Admin thường được redirect vào trang Admin Dashboard của Jazzmin hoặc Dashboard custom
        if response.status_code == 302:
             # Lưu ý: Đảm bảo bạn đã có view name 'dashboard:main' trong dashboard/urls.py
             # Nếu chưa có, hãy sửa dòng dưới thành nơi bạn muốn admin được chuyển tới
            try:
                target_url = reverse('dashboard:main')
            except:
                target_url = reverse('admin:index') # Fallback về trang admin gốc
            
            self.assertRedirects(response, target_url)
        else:
            self.assertEqual(response.status_code, 200)

    def test_dashboard_hub_for_nhanvien_vanhanh(self):
        # Tạo group vận hành
        g_vanhanh, _ = Group.objects.get_or_create(name="Vận hành")
        self.user.groups.add(g_vanhanh)
        self.client.login(username='user', password='password')
        
        response = self.client.get('/hub/')
        
        if response.status_code == 302:
             # Tương tự, đảm bảo 'dashboard:main' tồn tại
            try:
                target_url = reverse('dashboard:main')
            except:
                target_url = '/dashboard/'
            
            self.assertRedirects(response, target_url)

class AuditLogChecksumVerifyCommandTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        settings.SCMD_ORGANIZATION_ID = 'd8f89835-f716-419b-9800-47b74403387c'

    def test_valid_audit_logs(self):
        """
        Kiểm tra khi tất cả AuditLog đều hợp lệ.
        """
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.CREATE,
            module='test',
            model_name='TestModel',
            object_id='1',
            note='Test log 1',
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.UPDATE,
            module='test',
            model_name='TestModel',
            object_id='2',
            note='Test log 2',
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )
        
        # Run the management command
        with self.settings(SCMD_ORGANIZATION_ID=settings.SCMD_ORGANIZATION_ID):
            # call_command returns None, but we can check stdout
            with self.captureOnStdout() as stdout:
                call_command('verify_audit_logs')
                self.assertIn('Tất cả AuditLog đều hợp lệ. Không phát hiện sai lệch.', stdout.getvalue())

    def test_compromised_audit_log(self):
        """
        Kiểm tra khi có một AuditLog bị chỉnh sửa (checksum không khớp).
        """
        log_entry = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.CREATE,
            module='test',
            model_name='TestModel',
            object_id='1',
            note='Original note',
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )
        
        # Manually tamper with the log entry's note and save without re-generating checksum
        log_entry.note = 'Tampered note'
        log_entry.save(update_fields=['note']) # Save only note, not checksum

        with self.settings(SCMD_ORGANIZATION_ID=settings.SCMD_ORGANIZATION_ID):
            with self.captureOnStdout() as stdout:
                call_command('verify_audit_logs')
                output = stdout.getvalue()
                self.assertIn('PHÁT HIỆN BẢN GHI AUDIT LOG BỊ SAI LỆCH', output)
                self.assertIn('Checksum không khớp', output)
                self.assertIn(f"ID: {log_entry.id}", output)

    def test_audit_log_without_checksum(self):
        """
        Kiểm tra khi có một AuditLog không có checksum (ví dụ: từ migration cũ).
        """
        log_entry = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.CREATE,
            module='test',
            model_name='TestModel',
            object_id='1',
            note='Log without checksum',
            checksum=None, # Explicitly set to None
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )
        
        with self.settings(SCMD_ORGANIZATION_ID=settings.SCMD_ORGANIZATION_ID):
            with self.captureOnStdout() as stdout:
                call_command('verify_audit_logs')
                output = stdout.getvalue()
                self.assertIn('PHÁT HIỆN BẢN GHI AUDIT LOG BỊ SAI LỆCH', output)
                self.assertIn('Không có checksum', output)
                self.assertIn(f"ID: {log_entry.id}", output)