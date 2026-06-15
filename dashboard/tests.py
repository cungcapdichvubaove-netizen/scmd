from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import HopDong, KhachHangTiemNang, MucTieu
from users.models import ChucDanh, LichSuCongTac


class DashboardViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="dashboard_exec", password="password")
        Group.objects.get_or_create(name="Ban giám đốc")[0].user_set.add(self.user)

        self.chuc_danh = ChucDanh.objects.create(ten_chuc_danh="Giám đốc")
        nhan_vien = self.user.nhan_vien
        nhan_vien.ho_ten = "Điều hành thử nghiệm"
        nhan_vien.ngay_sinh = date(1990, 1, 1)
        nhan_vien.gioi_tinh = "M"
        nhan_vien.sdt_chinh = "0909090909"
        nhan_vien.chuc_danh = self.chuc_danh
        nhan_vien.save(update_fields=["ho_ten", "ngay_sinh", "gioi_tinh", "sdt_chinh", "chuc_danh"])

        kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH Test", email="kh@test.com", sdt="0123")
        hd = HopDong.objects.create(
            so_hop_dong="HD001",
            ngay_ky=timezone.now(),
            ngay_hieu_luc=timezone.now(),
            ngay_het_han=timezone.now() + timedelta(days=365),
            gia_tri=10000000,
        )
        mt = MucTieu.objects.create(hop_dong=hd, ten_muc_tieu="Mục tiêu A", sdt_lien_he="098")

        LichSuCongTac.objects.create(
            nhan_vien=nhan_vien,
            muc_tieu=mt,
            ngay_bat_dau=date.today() - timedelta(days=10),
            ngay_ket_thuc=None,
        )
        self.client.login(username="dashboard_exec", password="password")

    def test_dashboard_view_loads_compact_overview(self):
        response = self.client.get(reverse("dashboard:main"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tổng quan vận hành")
        self.assertContains(response, "Sự cố mở")
        self.assertContains(response, "Ca chưa check-in")
        self.assertContains(response, "Mục tiêu rủi ro")
        self.assertContains(response, "Top mục tiêu cần theo dõi")
        self.assertContains(response, "Sự cố mới nhất")
        self.assertContains(response, "Doanh thu dự kiến tháng này")

    def test_dashboard_response_has_no_fake_cta_links(self):
        response = self.client.get(reverse("dashboard:main"))
        content = response.content.decode("utf-8")

        self.assertNotIn('href="#"', content)
        self.assertNotIn("javascript:void", content)


class DashboardTemplateContractTests(TestCase):
    def test_template_has_no_forbidden_runtime_links_or_cyber_copy(self):
        source = Path("dashboard/templates/dashboard/main.html").read_text(encoding="utf-8")

        self.assertNotIn('href="#"', source)
        self.assertNotIn("javascript:void", source)
        self.assertNotIn("War " + "Room", source)
        self.assertNotIn("Senti" + "nel", source)
        self.assertNotIn("SOC", source)
        self.assertNotIn("Cyber", source)

    def test_template_keeps_structured_metric_markup(self):
        source = Path("dashboard/templates/dashboard/main.html").read_text(encoding="utf-8")

        self.assertIn("exec-kpi-card__label", source)
        self.assertIn("exec-kpi-card__value", source)
        self.assertIn("exec-watch-table", source)
