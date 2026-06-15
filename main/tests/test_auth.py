# -*- coding: utf-8 -*-
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.conf import settings

class MainAuthTests(TestCase):
    """
    Hợp nhất test case cho Authentication, Login Page và I18n.
    Đảm bảo tuân thủ SCMD Pro Brand Identity.
    """
    def setUp(self):
        self.client = Client()
        self.user_pass = 'password123'
        self.user = User.objects.create_user(
            username='operator_test', 
            password=self.user_pass,
            email='test@scmd.local'
        )
        # Đảm bảo session có câu trả lời xác minh để qua bước bảo mật
        session = self.client.session
        session['login_challenge_answer'] = '10'
        session.save()

    def test_login_page_brand_identity(self):
        """Kiểm tra tên thương hiệu và tagline trên trang login (WHITEPAPER.md 10.1)"""
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SCMD Pro")
        self.assertContains(response, "Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp")
        self.assertNotContains(response, "Bảng điều hành vận hành")

    def test_login_i18n_utf8_compliance(self):
        """Kiểm tra hiển thị tiếng Việt chuẩn UTF-8, không bị mojibake."""
        response = self.client.get(reverse('main:login'))
        self.assertContains(response, "Tài khoản")
        self.assertContains(response, "Mật khẩu")
        self.assertContains(response, "Xác minh đăng nhập")

    def test_login_success_and_redirect(self):
        """Đăng nhập thành công và chuyển hướng về Central Hub."""
        response = self.client.post(reverse('main:login'), {
            'username': 'operator_test',
            'password': self.user_pass,
            'login_verification_answer': '10'
        })
        # SCMD Pro sử dụng DashboardRouter điều hướng 2 lớp, cần target_status_code=302 hoặc follow=True
        self.assertRedirects(response, reverse('main:central_hub'), target_status_code=302)

    def test_login_failure_single_notification(self):
        """Kiểm tra chỉ hiện 1 thông báo lỗi khi sai thông tin (Yêu cầu người dùng)."""
        response = self.client.post(reverse('main:login'), {
            'username': 'operator_test',
            'password': 'wrong_password',
            'login_verification_answer': '10'
        }, follow=True)
        
        # Kiểm tra nội dung thông báo lỗi từ AuthenticationForm
        self.assertContains(response, "Vui lòng kiểm tra lại tài khoản và mật khẩu", count=1)

    def test_access_pending_for_unassigned_user(self):
        """User mới chưa có Group nghiệp vụ sẽ vào trang access_pending."""
        self.client.login(username='operator_test', password=self.user_pass)
        response = self.client.get(reverse('main:central_hub'), follow=True)
        self.assertTemplateUsed(response, "main/access_pending.html")

    def test_logout_behavior(self):
        """Kiểm tra logout và quay lại trang đăng nhập."""
        self.client.login(username='operator_test', password=self.user_pass)
        response = self.client.get(reverse('main:logout'))
        self.assertRedirects(response, reverse('main:login'))