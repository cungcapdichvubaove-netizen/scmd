# -*- coding: utf-8 -*-
"""Phase B business-domain completeness regression tests."""

from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounting.models import BangLuongThang, ChiTietLuong, KhoanKhauTruNhanVien, TamUngLuong
from clients.models import BienBanNghiemThu, CongNo, HoaDon, HopDong, PhuLucHopDongDichVu
from main.models import AuditLog
from operations.models import CaLamViec, ShiftChangeRequest
from users.models import (
    CauHinhMaNhanVien,
    DonNghiPhep,
    HoSoBaoHiem,
    NhanVien,
    OffboardingChecklist,
    QuyetDinhNghiViec,
)
from users.views import dashboard_view


class BusinessDomainPhaseBMixin:
    def setUp(self):
        CauHinhMaNhanVien.objects.all().delete()
        CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
        self.today = timezone.localdate()
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="phase-b-admin",
            email="phase-b-admin@example.com",
            password="password",
        )

    def make_staff(self, name="Nhân viên Phase B", *, status=NhanVien.TrangThaiLamViec.CHINH_THUC):
        return NhanVien.objects.create(
            ho_ten=name,
            trang_thai_lam_viec=status,
            ngay_vao_lam=self.today - timedelta(days=120),
            sdt_chinh="0901234567",
        )

    def make_contract(self):
        return HopDong.objects.create(
            so_hop_dong=f"HD-DV-{HopDong.objects.count() + 1}",
            ngay_ky=self.today - timedelta(days=30),
            ngay_hieu_luc=self.today - timedelta(days=30),
            ngay_het_han=self.today + timedelta(days=365),
            gia_tri=Decimal("10000000"),
        )

    def dashboard_context(self):
        request = RequestFactory().get("/users/dashboard/")
        request.user = self.admin_user
        with patch("users.views.render") as render_mock:
            render_mock.side_effect = lambda request, template, context: context
            return dashboard_view(request)


class PhaseBModelLifecycleTests(BusinessDomainPhaseBMixin, TestCase):
    def test_leave_request_is_separate_source_record_with_date_validation_and_audit(self):
        staff = self.make_staff()
        invalid = DonNghiPhep(
            nhan_vien=staff,
            ma_don="NP-INVALID",
            tu_ngay=self.today,
            den_ngay=self.today - timedelta(days=1),
            so_ngay=Decimal("1"),
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

        leave = DonNghiPhep.objects.create(
            nhan_vien=staff,
            ma_don="NP-001",
            tu_ngay=self.today + timedelta(days=1),
            den_ngay=self.today + timedelta(days=1),
            so_ngay=Decimal("1"),
            trang_thai=DonNghiPhep.TrangThai.PENDING_APPROVAL,
        )
        leave.transition_status(DonNghiPhep.TrangThai.APPROVED, actor=self.admin_user)
        audit = AuditLog.objects.filter(model_name="DonNghiPhep", object_id=str(leave.pk)).latest("timestamp")
        self.assertEqual(audit.changes["status_transition"]["new"], DonNghiPhep.TrangThai.APPROVED)

    def test_offboarding_decision_does_not_auto_change_employee_status(self):
        staff = self.make_staff(status=NhanVien.TrangThaiLamViec.CHINH_THUC)
        decision = QuyetDinhNghiViec.objects.create(
            nhan_vien=staff,
            so_quyet_dinh="QD-NV-001",
            ngay_quyet_dinh=self.today,
            ngay_hieu_luc=self.today + timedelta(days=7),
            trang_thai=QuyetDinhNghiViec.TrangThai.PENDING_APPROVAL,
        )
        decision.transition_status(QuyetDinhNghiViec.TrangThai.APPROVED, actor=self.admin_user)
        OffboardingChecklist.objects.create(quyet_dinh=decision)
        staff.refresh_from_db()
        self.assertEqual(staff.trang_thai_lam_viec, NhanVien.TrangThaiLamViec.CHINH_THUC)
        self.assertIsNone(staff.ngay_nghi_viec)

    def test_insurance_profile_active_status_is_not_a_field_on_employee(self):
        staff = self.make_staff()
        self.assertFalse(hasattr(NhanVien, "so_bao_hiem"))
        profile = HoSoBaoHiem.objects.create(
            nhan_vien=staff,
            so_bao_hiem="BHXH-001",
            loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
            ngay_tham_gia=self.today - timedelta(days=10),
            trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
        )
        self.assertTrue(profile.is_active_on(self.today))

    def test_shift_change_request_does_not_modify_assignment_or_payroll(self):
        staff = self.make_staff()
        ca = CaLamViec.objects.create(ten_ca="Ca ngày", gio_bat_dau=time(6, 0), gio_ket_thuc=time(18, 0))
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau="SHIFT-001",
            nguoi_yeu_cau=staff,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.OVERTIME,
            ngay_mong_muon=self.today + timedelta(days=1),
            ca_mong_muon=ca,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)
        self.assertEqual(request.trang_thai, ShiftChangeRequest.TrangThai.APPROVED)
        self.assertEqual(ChiTietLuong.objects.filter(nhan_vien=staff).count(), 0)

    def test_payroll_advance_and_deduction_are_records_not_direct_payslip_mutation(self):
        staff = self.make_staff()
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year)
        advance = TamUngLuong.objects.create(
            nhan_vien=staff,
            so_phieu="TU-001",
            bang_luong_du_kien=payroll,
            so_tien=Decimal("500000"),
            trang_thai=TamUngLuong.TrangThai.PENDING_APPROVAL,
        )
        advance.transition_status(TamUngLuong.TrangThai.APPROVED, actor=self.admin_user)
        deduction = KhoanKhauTruNhanVien.objects.create(
            nhan_vien=staff,
            so_chung_tu="KT-001",
            loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.TAM_UNG,
            tam_ung=advance,
            bang_luong_du_kien=payroll,
            so_tien=Decimal("500000"),
            trang_thai=KhoanKhauTruNhanVien.TrangThai.PENDING_APPROVAL,
        )
        deduction.transition_status(KhoanKhauTruNhanVien.TrangThai.APPROVED, actor=self.admin_user)
        self.assertEqual(ChiTietLuong.objects.filter(nhan_vien=staff, bang_luong=payroll).count(), 0)

    def test_client_contract_acceptance_invoice_and_debt_lifecycle_records(self):
        contract = self.make_contract()
        appendix = PhuLucHopDongDichVu.objects.create(
            hop_dong=contract,
            so_phu_luc="PLDV-001",
            loai_phu_luc=PhuLucHopDongDichVu.LoaiPhuLuc.GIA_HAN,
            ngay_hieu_luc=self.today,
            trang_thai=PhuLucHopDongDichVu.TrangThai.PENDING_APPROVAL,
        )
        appendix.transition_status(PhuLucHopDongDichVu.TrangThai.ACTIVE, actor=self.admin_user)
        acceptance = BienBanNghiemThu.objects.create(
            hop_dong=contract,
            so_bien_ban="BBNT-001",
            tu_ngay=self.today.replace(day=1),
            den_ngay=self.today,
            tong_gia_tri_nghiem_thu=Decimal("10000000"),
            trang_thai=BienBanNghiemThu.TrangThai.SIGNED,
        )
        invoice = HoaDon.objects.create(
            hop_dong=contract,
            bien_ban=acceptance,
            so_hoa_don="HDON-001",
            ngay_phat_hanh=self.today,
            ngay_den_han=self.today + timedelta(days=15),
            tong_tien=Decimal("10000000"),
            trang_thai=HoaDon.TrangThai.ISSUED,
        )
        debt = CongNo.objects.create(
            hoa_don=invoice,
            so_tham_chieu="CN-001",
            ngay_den_han=self.today + timedelta(days=15),
            so_tien_phai_thu=Decimal("10000000"),
            so_tien_da_thu=Decimal("2000000"),
            trang_thai=CongNo.TrangThai.PARTIAL,
        )
        self.assertEqual(debt.so_tien_con_lai, Decimal("8000000"))


class PhaseBAdminAndDashboardTests(BusinessDomainPhaseBMixin, TestCase):
    def test_admin_registers_phase_b_business_records(self):
        for model in [
            DonNghiPhep,
            QuyetDinhNghiViec,
            OffboardingChecklist,
            HoSoBaoHiem,
            ShiftChangeRequest,
            TamUngLuong,
            KhoanKhauTruNhanVien,
            PhuLucHopDongDichVu,
            BienBanNghiemThu,
            HoaDon,
            CongNo,
        ]:
            self.assertIn(model, admin.site._registry)

    def test_hr_dashboard_flags_pending_leave_missing_bhxh_and_open_offboarding(self):
        leave_staff = self.make_staff("NV nghỉ phép")
        missing_bhxh_staff = self.make_staff("NV thiếu BHXH")
        exiting_staff = self.make_staff("NV offboarding")

        # BAO_HIEM_KHAC is not sufficient for the mandatory BHXH dashboard rule.
        HoSoBaoHiem.objects.create(
            nhan_vien=missing_bhxh_staff,
            so_bao_hiem="INS-OTHER-DASH-001",
            loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BAO_HIEM_KHAC,
            ngay_tham_gia=self.today - timedelta(days=30),
            trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
        )

        DonNghiPhep.objects.create(
            nhan_vien=leave_staff,
            ma_don="NP-DASH-001",
            tu_ngay=self.today + timedelta(days=2),
            den_ngay=self.today + timedelta(days=2),
            so_ngay=Decimal("1"),
            trang_thai=DonNghiPhep.TrangThai.PENDING_APPROVAL,
        )
        QuyetDinhNghiViec.objects.create(
            nhan_vien=exiting_staff,
            so_quyet_dinh="QD-DASH-001",
            ngay_quyet_dinh=self.today,
            ngay_hieu_luc=self.today + timedelta(days=7),
            trang_thai=QuyetDinhNghiViec.TrangThai.APPROVED,
        )
        HoSoBaoHiem.objects.create(
            nhan_vien=leave_staff,
            so_bao_hiem="BHXH-DASH-001",
            loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
            ngay_tham_gia=self.today - timedelta(days=30),
            trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
        )
        HoSoBaoHiem.objects.create(
            nhan_vien=exiting_staff,
            so_bao_hiem="BHXH-DASH-002",
            loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
            ngay_tham_gia=self.today - timedelta(days=30),
            trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
        )

        context = self.dashboard_context()

        self.assertEqual(context["pending_leave_requests_count"], 1)
        self.assertIn(missing_bhxh_staff, list(context["official_without_active_bhxh"]))
        self.assertIn(missing_bhxh_staff, list(context["official_without_active_insurance"]))
        self.assertEqual(context["open_offboarding_count"], 1)
        action_types = {item["type"] for item in context["action_items"]}
        self.assertIn("Đơn nghỉ phép chờ duyệt", action_types)
        self.assertIn("Thiếu BHXH active", action_types)
        self.assertIn("Offboarding chưa xong", action_types)


class PhaseBDecisionRecordTests(TestCase):
    def test_contract_finance_decision_record_prevents_accounting_duplicate_models(self):
        body = Path("docs/BUSINESS_DOMAIN_DECISION_RECORD.md").read_text(encoding="utf-8")
        self.assertIn("clients.HoaDon", body)
        self.assertIn("clients.CongNo", body)
        self.assertIn("accounting will consume reconciled receivable data", body)
        self.assertIn("do not introduce duplicate accounting.HoaDon or accounting.CongNo", body)

    def test_phase_cd_roadmap_records_transition_policy_and_integration_boundary(self):
        body = Path("docs/BUSINESS_DOMAIN_PHASE_CD_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("transition matrix", body)
        self.assertIn("DonNghiPhep → payroll", body)
        self.assertIn("ShiftChangeRequest → PhanCongCaTruc", body)
        self.assertIn("TamUngLuong/KhoanKhauTruNhanVien → ChiTietLuong", body)
        self.assertIn("HoaDon/CongNo → accounting reports", body)
