# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from rolepermissions.roles import assign_role

from operations.models import BaoCaoDeXuat


class MobileWorkspaceNavigationTests(TestCase):
    def test_mobile_base_disables_patrol_shortcut_without_permission(self):
        user = get_user_model().objects.create_user(username="mobile-shell-user", password="password")

        request = RequestFactory().get(reverse("operations:mobile_dashboard"))
        request.user = user
        request.resolver_match = resolve(reverse("operations:mobile_dashboard"))

        html = render_to_string("mobile/base.html", {"request": request, "user": user})

        self.assertIn("scmd-mobile-account-link--disabled", html)
        self.assertIn("Tuần tra", html)
        self.assertIn("Vui lòng liên hệ với Admin", html)
        self.assertNotIn("SCMD Pro</span>", html)

    def test_mobile_attendance_route_has_dedicated_screen(self):
        user = get_user_model().objects.create_user(username="mobile-attendance-user", password="password")
        assign_role(user, "nhan_vien_bao_ve")
        self.client.force_login(user)

        response = self.client.get(reverse("operations:mobile_cham_cong"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "operations/mobile/cham_cong.html")
        self.assertContains(response, "Chấm công")
        self.assertNotContains(response, "Tác vụ hiện trường")


class MobileProposalFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mobile-proposal-user", password="password")
        assign_role(self.user, "nhan_vien_bao_ve")
        self.client.force_login(self.user)

    def test_mobile_proposal_form_exposes_operational_fields(self):
        response = self.client.get(reverse("operations:mobile_de_xuat_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="loai_de_xuat"', html=False)
        self.assertContains(response, 'name="hinh_anh"', html=False)

    def test_mobile_proposal_create_persists_type_and_content(self):
        response = self.client.post(
            reverse("operations:mobile_de_xuat_create"),
            data={
                "loai_de_xuat": BaoCaoDeXuat.LoaiDeXuat.VAT_TU,
                "tieu_de": "Xin cấp pin đèn pin",
                "noi_dung": "Ca đêm cần bổ sung pin cho đèn pin tuần tra.",
            },
        )

        self.assertRedirects(response, reverse("operations:mobile_de_xuat_list"))
        proposal = BaoCaoDeXuat.objects.get(nhan_vien=self.user.nhan_vien)
        self.assertEqual(proposal.loai_de_xuat, BaoCaoDeXuat.LoaiDeXuat.VAT_TU)
        self.assertEqual(proposal.tieu_de, "Xin cấp pin đèn pin")
