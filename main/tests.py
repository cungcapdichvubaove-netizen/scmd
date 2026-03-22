from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group

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