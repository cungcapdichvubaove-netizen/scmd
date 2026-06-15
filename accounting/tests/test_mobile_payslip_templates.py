# -*- coding: utf-8 -*-
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rolepermissions.roles import assign_role

from accounting.models import BangLuongThang, ChiTietLuong


class MobilePayslipTemplateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mobile-payslip-user",
            password="password",
        )
        assign_role(self.user, "nhan_vien_bao_ve")
        self.staff = self.user.nhan_vien
        self.staff.ma_nhan_vien = "NV-LUONG-01"
        self.staff.ho_ten = "Nhân viên lương mobile"
        self.staff.save(update_fields=["ma_nhan_vien", "ho_ten"])
        self.client.force_login(self.user)

        self.payroll = BangLuongThang.objects.create(
            tenant_id=self.staff.tenant_id,
            ten_bang_luong="Bảng lương test mobile",
            thang=6,
            nam=2026,
            trang_thai=BangLuongThang.TrangThai.DRAFT,
        )
        self.payslip = ChiTietLuong.objects.create(
            tenant_id=self.staff.tenant_id,
            bang_luong=self.payroll,
            nhan_vien=self.staff,
            tong_gio_lam=208,
            luong_chinh=Decimal("12000000"),
            thuong_chuyen_can=Decimal("500000"),
            phu_cap_khac=Decimal("300000"),
            ung_luong=Decimal("1000000"),
            phat_vi_pham=Decimal("0"),
            tien_dong_phuc=Decimal("150000"),
            tien_den_bu=Decimal("0"),
            bao_hiem=Decimal("600000"),
            phi_cong_doan=Decimal("100000"),
            thuc_lanh=Decimal("10950000"),
            ghi_chu="Đã đối soát đủ dữ liệu công.",
        )
        self.payroll.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.payroll.save(update_fields=["trang_thai"])

    def test_mobile_payslip_list_renders_existing_template(self):
        response = self.client.get(reverse("accounting:mobile_phieu_luong_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounting/mobile/phieu_luong_list.html")
        self.assertContains(response, "Phiếu lương")
        self.assertContains(response, "10950000")

    def test_mobile_payslip_detail_renders_existing_template(self):
        response = self.client.get(reverse("accounting:mobile_phieu_luong_detail", args=[self.payslip.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounting/mobile/phieu_luong_detail.html")
        self.assertContains(response, "Chi tiết phiếu lương")
        self.assertContains(response, "Tổng khấu trừ")
