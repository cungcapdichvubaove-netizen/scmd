# -*- coding: utf-8 -*-
"""Phase A regression tests for HR labor-contract business-domain completeness."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from main.models import AuditLog
from users.admin import HopDongLaoDongAdmin, HopDongLaoDongInline, NhanVienAdmin
from users.models import CauHinhMaNhanVien, HopDongLaoDong, NhanVien, PhuLucHopDongLaoDong
from users.views import dashboard_view


class LaborContractTestMixin:
    def setUp(self):
        CauHinhMaNhanVien.objects.all().delete()
        CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
        self.today = timezone.localdate()
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="hr-contract-admin",
            email="hr-contract-admin@example.com",
            password="password",
        )

    def make_staff(self, name="Nhân viên HĐLĐ", *, status=NhanVien.TrangThaiLamViec.CHINH_THUC, legacy_contract_type=""):
        return NhanVien.objects.create(
            ho_ten=name,
            trang_thai_lam_viec=status,
            loai_hop_dong=legacy_contract_type,
            ngay_vao_lam=self.today - timedelta(days=90),
            sdt_chinh="0901234567",
        )

    def make_contract(self, staff, **overrides):
        data = {
            "nhan_vien": staff,
            "so_hop_dong": f"HDLD-{staff.pk}-{HopDongLaoDong.objects.count() + 1}",
            "loai_hop_dong": NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN,
            "ngay_ky": self.today - timedelta(days=60),
            "ngay_hieu_luc": self.today - timedelta(days=60),
            "ngay_het_han": self.today + timedelta(days=365),
            "trang_thai": HopDongLaoDong.TrangThai.ACTIVE,
            "muc_luong_co_ban": Decimal("7000000"),
            "phu_cap": Decimal("500000"),
        }
        data.update(overrides)
        return HopDongLaoDong.objects.create(**data)


class HopDongLaoDongModelTests(LaborContractTestMixin, TestCase):
    def test_model_supports_required_lifecycle_statuses_and_expiry_helpers(self):
        staff = self.make_staff()
        contract = self.make_contract(
            staff,
            ngay_het_han=self.today + timedelta(days=15),
            trang_thai=HopDongLaoDong.TrangThai.EXPIRING,
        )

        self.assertEqual(
            set(HopDongLaoDong.TrangThai.values),
            {"DRAFT", "PENDING_SIGNATURE", "ACTIVE", "EXPIRING", "EXPIRED", "TERMINATED"},
        )
        self.assertTrue(contract.is_effective_on(self.today))
        self.assertTrue(contract.is_expiring_within(days=30, today=self.today))
        self.assertFalse(contract.is_expired_on(self.today))

    def test_model_rejects_expiry_before_effective_date(self):
        staff = self.make_staff()
        contract = HopDongLaoDong(
            nhan_vien=staff,
            so_hop_dong="HDLD-DATE-INVALID",
            loai_hop_dong=NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN,
            ngay_hieu_luc=self.today,
            ngay_het_han=self.today - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            contract.full_clean()

    def test_nhanvien_loai_hop_dong_is_legacy_not_active_contract_ssot(self):
        staff = self.make_staff(legacy_contract_type=NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN)

        self.assertEqual(staff.loai_hop_dong, NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN)
        self.assertFalse(staff.has_active_labor_contract(day=self.today))

        self.make_contract(staff)
        self.assertTrue(staff.has_active_labor_contract(day=self.today))

    def test_status_transition_writes_audit_log_and_does_not_change_employee_status(self):
        staff = self.make_staff(status=NhanVien.TrangThaiLamViec.CHINH_THUC)
        contract = self.make_contract(staff, trang_thai=HopDongLaoDong.TrangThai.PENDING_SIGNATURE)

        contract.transition_status(HopDongLaoDong.TrangThai.ACTIVE, actor=self.admin_user, note="Ký HĐLĐ")
        staff.refresh_from_db()

        self.assertEqual(staff.trang_thai_lam_viec, NhanVien.TrangThaiLamViec.CHINH_THUC)
        audit = AuditLog.objects.filter(model_name="HopDongLaoDong", object_id=str(contract.pk)).latest("timestamp")
        self.assertEqual(audit.action, AuditLog.Action.UPDATE)
        self.assertEqual(audit.changes["status_transition"]["old"], HopDongLaoDong.TrangThai.PENDING_SIGNATURE)
        self.assertEqual(audit.changes["status_transition"]["new"], HopDongLaoDong.TrangThai.ACTIVE)

    def test_labor_contract_appendix_exists_as_separate_business_record(self):
        staff = self.make_staff()
        contract = self.make_contract(staff)
        appendix = PhuLucHopDongLaoDong.objects.create(
            hop_dong=contract,
            so_phu_luc="PL-001",
            ngay_hieu_luc=self.today,
            noi_dung="Điều chỉnh phụ cấp trách nhiệm",
        )

        self.assertEqual(appendix.hop_dong, contract)
        self.assertEqual(contract.cac_phu_luc.count(), 1)


class HopDongLaoDongAdminTests(LaborContractTestMixin, TestCase):
    def test_admin_registers_contract_model_with_hr_search_filters_and_inline(self):
        self.assertIn(HopDongLaoDong, admin.site._registry)
        self.assertIn(PhuLucHopDongLaoDong, admin.site._registry)

        contract_admin = admin.site._registry[HopDongLaoDong]
        self.assertIn("trang_thai", contract_admin.list_filter)
        self.assertIn("loai_hop_dong", contract_admin.list_filter)
        self.assertIn("so_hop_dong", contract_admin.search_fields)
        self.assertIn("nhan_vien__ma_nhan_vien", contract_admin.search_fields)
        self.assertIn("nhan_vien__ho_ten", contract_admin.search_fields)

        employee_admin = admin.site._registry[NhanVien]
        self.assertIn(HopDongLaoDongInline, employee_admin.inlines)

    def test_admin_status_change_creates_audit_log(self):
        staff = self.make_staff()
        contract = self.make_contract(staff, trang_thai=HopDongLaoDong.TrangThai.PENDING_SIGNATURE)
        contract.trang_thai = HopDongLaoDong.TrangThai.ACTIVE
        model_admin = HopDongLaoDongAdmin(HopDongLaoDong, AdminSite())
        request = RequestFactory().post(f"/admin/users/hopdonglaodong/{contract.pk}/change/")
        request.user = self.admin_user

        model_admin.save_model(request, contract, form=None, change=True)

        audit = AuditLog.objects.filter(model_name="HopDongLaoDong", object_id=str(contract.pk)).latest("timestamp")
        self.assertEqual(audit.changes["status_transition"]["old"], HopDongLaoDong.TrangThai.PENDING_SIGNATURE)
        self.assertEqual(audit.changes["status_transition"]["new"], HopDongLaoDong.TrangThai.ACTIVE)


class HRDashboardLaborContractTests(LaborContractTestMixin, TestCase):
    def get_dashboard_context(self):
        request = RequestFactory().get("/users/dashboard/")
        request.user = self.admin_user

        with patch("users.views.render") as render_mock:
            render_mock.side_effect = lambda request, template, context: context
            return dashboard_view(request)

    def test_dashboard_flags_expiring_expired_and_missing_labor_contracts(self):
        expiring_staff = self.make_staff("NV sắp hết hạn")
        expired_staff = self.make_staff("NV hết hạn")
        missing_staff = self.make_staff(
            "NV chính thức thiếu HĐLĐ",
            legacy_contract_type=NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN,
        )

        self.make_contract(
            expiring_staff,
            so_hop_dong="HDLD-EXPIRING",
            ngay_het_han=self.today + timedelta(days=20),
            trang_thai=HopDongLaoDong.TrangThai.ACTIVE,
        )
        self.make_contract(
            expired_staff,
            so_hop_dong="HDLD-EXPIRED-ACTIVE-STAFF",
            ngay_het_han=self.today - timedelta(days=1),
            trang_thai=HopDongLaoDong.TrangThai.EXPIRED,
        )

        context = self.get_dashboard_context()

        self.assertEqual(context["expiring_labor_contracts_count"], 1)
        self.assertEqual(context["expired_active_labor_contracts_count"], 1)
        self.assertIn(missing_staff, list(context["official_without_active_contract"]))
        self.assertGreaterEqual(context["missing_active_labor_contract_count"], 1)
        action_types = {item["type"] for item in context["action_items"]}
        self.assertIn("HĐLĐ sắp hết hạn", action_types)
        self.assertIn("HĐLĐ đã hết hạn", action_types)
        self.assertIn("Thiếu HĐLĐ active", action_types)

    def test_dashboard_does_not_treat_legacy_loai_hop_dong_as_active_contract(self):
        staff = self.make_staff(
            "NV legacy only",
            legacy_contract_type=NhanVien.LoaiHopDong.KHONG_XAC_DINH_THOI_HAN,
        )

        context = self.get_dashboard_context()

        self.assertFalse(staff.has_active_labor_contract(day=self.today))
        self.assertIn(staff, list(context["official_without_active_contract"]))
