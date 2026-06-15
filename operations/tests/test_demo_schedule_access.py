# -*- coding: utf-8 -*-
"""Runtime schedule/object-scope contract for the KTC Việt Nam demo seed."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rolepermissions.checkers import has_permission, has_role

from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from main.management.commands.seed_scmd_demo import DEFAULT_DEMO_PASSWORD, DEMO_PREFIX
from operations.access_policies import ShiftAssignmentPolicy, ShiftVisibilityPolicy
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.access_policies import StaffVisibilityPolicy
from users.models import LichSuCongTac, NhanVien


class DemoScheduleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "seed_scmd_demo",
            profile="light",
            password=DEFAULT_DEMO_PASSWORD,
            stdout=StringIO(),
        )

    def _login(self, username):
        self.assertTrue(self.client.login(username=username, password=DEFAULT_DEMO_PASSWORD))
        return User.objects.get(username=username)

    def _first_shift(self):
        return CaLamViec.objects.filter(ten_ca__startswith=DEMO_PREFIX).order_by("gio_bat_dau").first()

    def test_chihuy_dn01_can_open_schedule_and_only_sees_own_site_scope(self):
        user = self._login("chihuy.dn01")
        self.assertTrue(has_role(user, "doi_truong"))
        self.assertTrue(has_permission(user, "giao_ca_truc"))
        self.assertTrue(user.has_perm("operations.add_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.change_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.delete_phancongcatruc"))

        visible_sites = list(SiteVisibilityPolicy.managed_sites(user).order_by("ten_muc_tieu"))
        self.assertEqual(len(visible_sites), 1)
        self.assertIn("Đà Nẵng", visible_sites[0].ten_muc_tieu)
        self.assertTrue(visible_sites[0].ten_muc_tieu.endswith("01"))

        response = self.client.get(reverse("operations:dashboard_xep_lich"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible_sites[0].ten_muc_tieu)
        self.assertNotContains(response, "Hà Nội / miền Bắc")
        self.assertNotContains(response, "Sài Gòn / miền Nam")
        self.assertContains(response, "htmx/them-ca")

    def test_chihuy_dn01_add_edit_delete_inside_scope_and_denied_outside_scope(self):
        user = self._login("chihuy.dn01")
        site = SiteVisibilityPolicy.managed_sites(user).get()
        post = ViTriChot.objects.filter(muc_tieu=site).first()
        shift = self._first_shift()
        day = timezone.localdate() + timedelta(days=45)
        staff = StaffVisibilityPolicy.visible_staff_for_scheduling(user, site, at_date=day).exclude(pk=user.nhan_vien.pk).first()
        self.assertIsNotNone(staff)

        form_response = self.client.get(reverse("operations:them_ca_form", args=[post.pk, shift.pk, day.isoformat()]))
        self.assertEqual(form_response.status_code, 200)

        save_response = self.client.post(
            reverse("operations:luu_ca"),
            {
                "nhan_vien_id": staff.pk,
                "vi_tri_id": post.pk,
                "ca_id": shift.pk,
                "ngay_truc": day.isoformat(),
                "reason": "Demo test inside scope",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(save_response.status_code, 200)
        created_shift = PhanCongCaTruc.objects.get(nhan_vien=staff, vi_tri_chot=post, ca_lam_viec=shift, ngay_truc=day)

        edit_response = self.client.get(reverse("operations:sua_ca_form", args=[created_shift.pk]))
        self.assertEqual(edit_response.status_code, 200)

        delete_response = self.client.post(
            reverse("operations:xoa_ca", args=[created_shift.pk]),
            {"reason": "Demo test delete inside scope"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(PhanCongCaTruc.objects.filter(pk=created_shift.pk).exists())

        outside_site = MucTieu.objects.filter(ten_muc_tieu__startswith=DEMO_PREFIX).exclude(pk=site.pk).filter(ten_muc_tieu__contains="Hà Nội").first()
        if outside_site is None:
            outside_site = MucTieu.objects.filter(ten_muc_tieu__startswith=DEMO_PREFIX).exclude(pk=site.pk).first()
        outside_post = ViTriChot.objects.filter(muc_tieu=outside_site).first()
        outside_staff = PhanCongCaTruc.objects.filter(vi_tri_chot__muc_tieu=outside_site).select_related("nhan_vien").first().nhan_vien

        outside_form = self.client.get(reverse("operations:them_ca_form", args=[outside_post.pk, shift.pk, day.isoformat()]))
        self.assertEqual(outside_form.status_code, 403)

        outside_save = self.client.post(
            reverse("operations:luu_ca"),
            {
                "nhan_vien_id": outside_staff.pk,
                "vi_tri_id": outside_post.pk,
                "ca_id": shift.pk,
                "ngay_truc": (day + timedelta(days=1)).isoformat(),
                "reason": "Demo test outside scope",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(outside_save.status_code, 403)

        outside_existing = PhanCongCaTruc.objects.filter(vi_tri_chot__muc_tieu=outside_site).first()
        outside_delete = self.client.post(
            reverse("operations:xoa_ca", args=[outside_existing.pk]),
            {"reason": "Demo test outside delete"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(outside_delete.status_code, 403)

    def test_guard_baove_dn001_mobile_scope_is_personal_only(self):
        user = self._login("baove.dn001")
        response = self.client.get(reverse("operations:mobile_dashboard"))
        self.assertEqual(response.status_code, 200)

        shifts = ShiftVisibilityPolicy.visible_shifts(user)
        self.assertTrue(shifts.exists())
        self.assertEqual(set(shifts.values_list("nhan_vien_id", flat=True).distinct()), {user.nhan_vien.pk})

    def test_danang_region_manager_sees_danang_region_only(self):
        user = self._login("giamdocchinhanh.danang")
        visible_names = list(SiteVisibilityPolicy.managed_sites(user).values_list("ten_muc_tieu", flat=True))
        self.assertGreaterEqual(len(visible_names), 2)
        self.assertTrue(all("Đà Nẵng" in name for name in visible_names))
        self.assertFalse(any("Hà Nội" in name or "Sài Gòn" in name for name in visible_names))

        response = self.client.get(reverse("operations:dashboard_xep_lich"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Đà Nẵng / miền Trung")
        self.assertNotContains(response, "Hà Nội / miền Bắc")
        self.assertNotContains(response, "Sài Gòn / miền Nam")

    def test_bgd_can_view_schedule_but_no_mutation_cta_or_action_access(self):
        user = self._login("tonggiamdoc.hanoi")
        self.assertTrue(has_role(user, "ban_giam_doc"))
        self.assertFalse(has_permission(user, "giao_ca_truc"))

        response = self.client.get(reverse("operations:dashboard_xep_lich"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "htmx/them-ca")
        self.assertNotContains(response, "htmx/sua-ca")
        self.assertNotContains(response, "fas fa-plus")

        post = ViTriChot.objects.filter(muc_tieu__ten_muc_tieu__startswith=DEMO_PREFIX).first()
        shift = self._first_shift()
        day = timezone.localdate() + timedelta(days=45)
        form_response = self.client.get(reverse("operations:them_ca_form", args=[post.pk, shift.pk, day.isoformat()]))
        self.assertEqual(form_response.status_code, 403)


    def _assert_commander_scope_and_mutation(self, username, expected_region_text, forbidden_region_text):
        user = self._login(username)
        site = SiteVisibilityPolicy.managed_sites(user).get()
        self.assertIn(expected_region_text, site.ten_muc_tieu)
        self.assertTrue(site.ten_muc_tieu.endswith("01"))

        response = self.client.get(reverse("operations:dashboard_xep_lich"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, site.ten_muc_tieu)
        self.assertNotContains(response, forbidden_region_text)

        post = ViTriChot.objects.filter(muc_tieu=site).first()
        shift = self._first_shift()
        day = timezone.localdate() + timedelta(days=46)
        staff = StaffVisibilityPolicy.visible_staff_for_scheduling(user, site, at_date=day).exclude(pk=user.nhan_vien.pk).first()
        self.assertIsNotNone(staff)
        response = self.client.post(
            reverse("operations:luu_ca"),
            {
                "nhan_vien_id": staff.pk,
                "vi_tri_id": post.pk,
                "ca_id": shift.pk,
                "ngay_truc": day.isoformat(),
                "reason": f"Demo test {username} inside scope",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        created_shift = PhanCongCaTruc.objects.get(nhan_vien=staff, vi_tri_chot=post, ca_lam_viec=shift, ngay_truc=day)
        delete_response = self.client.post(
            reverse("operations:xoa_ca", args=[created_shift.pk]),
            {"reason": f"Demo test {username} cleanup"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(delete_response.status_code, 200)

    def test_chihuy_sg01_can_mutate_only_saigon_01_scope(self):
        self._assert_commander_scope_and_mutation("chihuy.sg01", "Sài Gòn", "Đà Nẵng / miền Trung")

    def test_central_operations_can_open_schedule_and_see_all_regions(self):
        for username in ("truongvanhanh.hanoi", "dieuphoi.trungtam"):
            with self.subTest(username=username):
                user = self._login(username)
                self.assertTrue(has_permission(user, "giao_ca_truc"))
                response = self.client.get(reverse("operations:dashboard_xep_lich"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Hà Nội / miền Bắc")
                self.assertContains(response, "Đà Nẵng / miền Trung")
                self.assertContains(response, "Sài Gòn / miền Nam")

    def test_shift_assignment_policy_requires_rolepermission_and_model_permission(self):
        bgd = self._login("tonggiamdoc.hanoi")
        post = ViTriChot.objects.filter(muc_tieu__ten_muc_tieu__startswith=DEMO_PREFIX).select_related("muc_tieu").first()
        staff = LichSuCongTac.objects.filter(muc_tieu=post.muc_tieu, ngay_ket_thuc__isnull=True).exclude(nhan_vien=bgd.nhan_vien).first().nhan_vien
        result = ShiftAssignmentPolicy.can_assign_shift(bgd, staff, post.muc_tieu, timezone.localdate() + timedelta(days=45))
        self.assertFalse(result.allowed)
        self.assertEqual(result.details.get("required_rolepermission"), "giao_ca_truc")
        self.assertEqual(result.details.get("required_django_permission"), "operations.add_phancongcatruc")

    def test_guard_cannot_access_back_office_or_schedule_dashboards(self):
        self._login("baove.dn001")
        denied_routes = [
            "operations:dashboard_xep_lich",
            "users:dashboard",
            "accounting:dashboard",
            "inventory:dashboard",
            "clients:dashboard_crm",
            "inspection:dashboard",
        ]
        for route_name in denied_routes:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 403)

    def test_guard_current_work_history_has_single_home_site(self):
        guard_staff = NhanVien.objects.filter(ma_nhan_vien__startswith="KTCVN-DN-BV").first()
        self.assertIsNotNone(guard_staff)
        current_rows = LichSuCongTac.objects.filter(nhan_vien=guard_staff, ngay_ket_thuc__isnull=True)
        self.assertEqual(current_rows.count(), 1)
        home_site = current_rows.get().muc_tieu
        future_site_ids = set(
            PhanCongCaTruc.objects.filter(
                nhan_vien=guard_staff,
                ngay_truc__gte=timezone.localdate(),
            ).values_list("vi_tri_chot__muc_tieu_id", flat=True).distinct()
        )
        self.assertEqual(future_site_ids, {home_site.pk})

    def test_module_dashboards_render_ctas_without_403_for_primary_staff_accounts(self):
        import re

        cases = {
            "truongnhansu.hanoi": "users:dashboard",
            "ketoantruong.hanoi": "accounting:dashboard",
            "thukho.hanoi": "inventory:dashboard",
            "truongkinhdoanh.hanoi": "clients:dashboard_crm",
            "thanhtra.hanoi": "inspection:dashboard",
        }
        for username, route_name in cases.items():
            with self.subTest(username=username):
                self.client.logout()
                self._login(username)
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode("utf-8", errors="ignore")
                links = []
                for href in re.findall(r'href="([^"]+)"', html):
                    if not href.startswith("/") or href.startswith("//"):
                        continue
                    if href in links or href.startswith("/static/"):
                        continue
                    links.append(href)
                self.assertTrue(links, f"{username} dashboard rendered no actionable internal links")
                for href in links[:8]:
                    linked = self.client.get(href)
                    self.assertNotEqual(linked.status_code, 403, f"{username} CTA {href} returned 403")
