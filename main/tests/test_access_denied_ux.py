# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse
from rolepermissions.roles import assign_role

from main.views import handler403


class AccessDeniedUxTests(TestCase):
    def test_forbidden_dashboard_uses_minimal_friendly_page(self):
        user = User.objects.create_user("guard403", "guard403@test.com", "password")
        assign_role(user, "nhan_vien_bao_ve")
        self.client.force_login(user)

        response = self.client.get(reverse("accounting:dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "main/403.html")
        self.assertContains(response, "TRUY CẬP BỊ GIỚI HẠN", status_code=403)
        self.assertContains(response, "Không có quyền truy cập", status_code=403)
        self.assertContains(response, "Tài khoản của bạn chưa được cấp quyền vào khu vực này", status_code=403)
        self.assertContains(response, "Quay về khu vực làm việc", status_code=403)
        self.assertContains(response, "Đăng xuất", status_code=403)
        self.assertContains(response, "Mã lỗi 403", status_code=403)
        self.assertContains(response, "access-denied-page", status_code=403)
        self.assertContains(response, "access-denied-shell", status_code=403)
        self.assertNotContains(response, "Không phải lỗi hệ thống", status_code=403)
        self.assertNotContains(response, "Phù hợp mô hình làm việc", status_code=403)
        self.assertNotContains(response, "Hướng xử lý rõ ràng", status_code=403)
        self.assertNotContains(response, "Chi tiết kỹ thuật", status_code=403)

    def test_forbidden_page_hides_technical_detail_for_regular_user(self):
        user = User.objects.create_user("regular403", "regular403@test.com", "password")
        assign_role(user, "nhan_vien_bao_ve")

        request = RequestFactory().get("/forbidden-demo/")
        request.user = user

        response = handler403(request, PermissionDenied("internal object-scope policy detail"))

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Chi tiết kỹ thuật", response.content.decode("utf-8"))
        self.assertNotIn("internal object-scope policy detail", response.content.decode("utf-8"))

    @override_settings(DEBUG=False)
    def test_forbidden_page_hides_technical_detail_for_staff_business_user(self):
        user = User.objects.create_user(
            "staffbiz403",
            "staffbiz403@test.com",
            "password",
            is_staff=True,
        )
        assign_role(user, "ke_toan")

        request = RequestFactory().get("/forbidden-demo/")
        request.user = user

        response = handler403(request, PermissionDenied("staff-only internal policy detail"))

        self.assertEqual(response.status_code, 403)
        html = response.content.decode("utf-8")
        self.assertNotIn("Chi tiết kỹ thuật", html)
        self.assertNotIn("staff-only internal policy detail", html)

    @override_settings(DEBUG=False)
    def test_forbidden_page_can_show_technical_detail_for_superuser(self):
        user = User.objects.create_superuser(
            "super403",
            "super403@test.com",
            "password",
        )
        assign_role(user, "ban_giam_doc")

        request = RequestFactory().get("/forbidden-demo/")
        request.user = user

        response = handler403(request, PermissionDenied("superuser-only internal policy detail"))

        self.assertEqual(response.status_code, 403)
        html = response.content.decode("utf-8")
        self.assertIn("Chi tiết kỹ thuật", html)
        self.assertIn("superuser-only internal policy detail", html)

    @override_settings(DEBUG=True)
    def test_forbidden_page_can_show_technical_detail_in_debug(self):
        user = User.objects.create_user("debug403", "debug403@test.com", "password")
        assign_role(user, "nhan_vien_bao_ve")

        request = RequestFactory().get("/forbidden-demo/")
        request.user = user

        response = handler403(request, PermissionDenied("debug-only object-scope policy detail"))

        self.assertEqual(response.status_code, 403)
        html = response.content.decode("utf-8")
        self.assertIn("Chi tiết kỹ thuật", html)
        self.assertIn("debug-only object-scope policy detail", html)

    def test_sidebar_marks_unavailable_workspace_links(self):
        user = User.objects.create_user("guardnav", "guardnav@test.com", "password")
        assign_role(user, "nhan_vien_bao_ve")

        request = RequestFactory().get(reverse("operations:mobile_dashboard"))
        request.user = user
        request.resolver_match = resolve(reverse("operations:mobile_dashboard"))

        html = render_to_string("partials/sidebar_menu_items.html", {"request": request, "user": user})

        self.assertIn('href="%s"' % reverse("accounting:dashboard"), html)
        self.assertIn('aria-disabled="true"', html)
        self.assertIn("scmd-nav-link-disabled", html)
        self.assertIn("Vui lòng liên hệ với Admin", html)
