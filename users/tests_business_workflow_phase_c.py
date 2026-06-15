# -*- coding: utf-8 -*-
"""Phase C business workflow integration tests."""

from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role

from accounting.application.payroll_reconciliation_use_case import PayrollSourceReconciliationUseCase
from accounting.models import BangLuongThang, ChiTietLuong, KhoanKhauTruNhanVien, TamUngLuong
from accounting.services.payroll_calculation import PayrollCalculationService
from clients.models import BienBanNghiemThu, CongNo, HoaDon, HopDong, MucTieu, PhuLucHopDongDichVu
from main.models import AuditLog
from operations.application.attendance_use_cases import GetSwapRateReportUseCase
from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase
from operations.application.shift_change_permission_policy import ShiftChangePermissionPolicy
from operations.application.shift_change_use_cases import ApplyShiftChangeRequestUseCase, ApproveShiftChangeRequestUseCase
from operations.models import CaLamViec, PhanCongCaTruc, ShiftChangeRequest, ViTriChot
from users.models import (
    CauHinhMaNhanVien,
    DonNghiPhep,
    HoSoBaoHiem,
    HopDongLaoDong,
    NhanVien,
    QuyetDinhNghiViec,
)


class PhaseCTestMixin:
    def setUp(self):
        CauHinhMaNhanVien.objects.all().delete()
        CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
        self.today = timezone.localdate()
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="phase-c-admin",
            email="phase-c-admin@example.com",
            password="password",
        )
        self.staff = self.make_staff("NV Phase C")
        self.contract = self.make_service_contract()
        self.target = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Mục tiêu Phase C",
            dia_chi="Hà Nội",
            so_luong_nhan_vien=1,
        )
        self.post = ViTriChot.objects.create(muc_tieu=self.target, ten_vi_tri="Cổng chính")
        self.shift = CaLamViec.objects.create(ten_ca="Ca ngày", gio_bat_dau=time(6, 0), gio_ket_thuc=time(18, 0))

    def make_staff(self, name, *, status=NhanVien.TrangThaiLamViec.CHINH_THUC, phone="0901234567", user=None):
        if user is not None:
            try:
                staff = user.nhan_vien
            except NhanVien.DoesNotExist:
                staff = None
            if staff is not None:
                staff.ho_ten = name
                staff.trang_thai_lam_viec = status
                staff.ngay_vao_lam = self.today - timedelta(days=120)
                staff.sdt_chinh = phone
                staff.save()
                return staff

        return NhanVien.objects.create(
            user=user,
            ho_ten=name,
            trang_thai_lam_viec=status,
            ngay_vao_lam=self.today - timedelta(days=120),
            sdt_chinh=phone,
        )

    def make_user_and_staff(self, username, full_name, *, phone, role=None):
        user = self.User.objects.create_user(username=username, password="password")
        if role:
            assign_role(user, role)
        staff = self.make_staff(full_name, phone=phone, user=user)
        return user, staff

    def make_service_contract(self):
        return HopDong.objects.create(
            so_hop_dong=f"HD-DV-C-{HopDong.objects.count() + 1}",
            ngay_ky=self.today - timedelta(days=30),
            ngay_hieu_luc=self.today - timedelta(days=30),
            ngay_het_han=self.today + timedelta(days=365),
            gia_tri=Decimal("10000000"),
        )

    def make_assignment(self, staff=None, work_date=None, shift=None):
        return PhanCongCaTruc.objects.create(
            nhan_vien=staff or self.staff,
            vi_tri_chot=self.post,
            ca_lam_viec=shift or self.shift,
            ngay_truc=work_date or self.today + timedelta(days=1),
        )


class PhaseCTransitionPolicyTests(PhaseCTestMixin, TestCase):
    def test_required_phase_c_models_expose_transition_matrix(self):
        for model in [
            HopDongLaoDong,
            DonNghiPhep,
            QuyetDinhNghiViec,
            HoSoBaoHiem,
            ShiftChangeRequest,
            TamUngLuong,
            KhoanKhauTruNhanVien,
            PhuLucHopDongDichVu,
            BienBanNghiemThu,
            HoaDon,
            CongNo,
        ]:
            self.assertTrue(getattr(model, "ALLOWED_STATUS_TRANSITIONS", None), model.__name__)

    def test_invalid_transitions_are_rejected(self):
        contract = HopDongLaoDong.objects.create(
            nhan_vien=self.staff,
            so_hop_dong="HDLD-POLICY-001",
            loai_hop_dong=NhanVien.LoaiHopDong.KHONG_XAC_DINH_THOI_HAN,
            ngay_hieu_luc=self.today - timedelta(days=1),
            trang_thai=HopDongLaoDong.TrangThai.ACTIVE,
        )
        with self.assertRaises(ValidationError):
            contract.transition_status(HopDongLaoDong.TrangThai.DRAFT, actor=self.admin_user)

        advance = TamUngLuong.objects.create(
            nhan_vien=self.staff,
            so_phieu="TU-POLICY-001",
            so_tien=Decimal("300000"),
            trang_thai=TamUngLuong.TrangThai.PAID,
        )
        with self.assertRaises(ValidationError):
            advance.transition_status(TamUngLuong.TrangThai.DRAFT, actor=self.admin_user)

        invoice = HoaDon.objects.create(
            hop_dong=self.contract,
            so_hoa_don="HDON-POLICY-001",
            tong_tien=Decimal("10000000"),
            trang_thai=HoaDon.TrangThai.PAID,
        )
        with self.assertRaises(ValidationError):
            invoice.transition_status(HoaDon.TrangThai.DRAFT, actor=self.admin_user)


class PhaseCShiftChangeAuthorizationTests(PhaseCTestMixin, TestCase):
    def make_shift_request_for_authorization(self, *, requester_staff=None, assignment=None, status=None):
        assignment = assignment or self.make_assignment(staff=requester_staff or self.staff)
        return ShiftChangeRequest.objects.create(
            ma_yeu_cau=f"SCR-AUTH-{ShiftChangeRequest.objects.count() + 1}",
            nguoi_yeu_cau=requester_staff or self.staff,
            phan_cong_goc=assignment,
            nhan_vien_thay_the=self.make_staff(f"NV thay thế auth {ShiftChangeRequest.objects.count() + 1}", phone=f"091{ShiftChangeRequest.objects.count():07d}"),
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
            trang_thai=status or ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )

    def test_regular_employee_cannot_approve_other_request(self):
        user, _staff = self.make_user_and_staff("plain-approver", "NV không quyền", phone="0910000001")
        request = self.make_shift_request_for_authorization()
        with self.assertRaises(PermissionDenied):
            ApproveShiftChangeRequestUseCase.execute(request.pk, actor=user, tenant_id=request.tenant_id)

    def test_employee_cannot_self_approve_own_request(self):
        user, requester = self.make_user_and_staff("self-approver", "NV tự duyệt", phone="0910000002")
        assignment = self.make_assignment(staff=requester)
        request = self.make_shift_request_for_authorization(requester_staff=requester, assignment=assignment)
        with self.assertRaises(PermissionDenied):
            ApproveShiftChangeRequestUseCase.execute(request.pk, actor=user, tenant_id=request.tenant_id)

    def test_commander_cannot_approve_outside_managed_site(self):
        commander_user, commander = self.make_user_and_staff("commander-outside", "Đội trưởng ngoài mục tiêu", phone="0910000003", role="doi_truong")
        request = self.make_shift_request_for_authorization()
        self.assertFalse(ShiftChangePermissionPolicy.can_approve(commander_user, request).allowed)
        with self.assertRaises(PermissionDenied):
            ApproveShiftChangeRequestUseCase.execute(request.pk, actor=commander_user, tenant_id=request.tenant_id)

        self.target.quan_ly_muc_tieu = commander
        self.target.save(update_fields=["quan_ly_muc_tieu"])
        self.assertTrue(ShiftChangePermissionPolicy.can_approve(commander_user, request).allowed)

    def test_user_without_operational_role_gets_403_when_calling_apply_endpoint(self):
        user, _staff = self.make_user_and_staff("api-no-role", "NV API không quyền", phone="0910000004")
        request = self.make_shift_request_for_authorization(status=ShiftChangeRequest.TrangThai.APPROVED)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(reverse("operations:mobile_doi_ca_approve_api"), {"request_id": request.pk, "apply": "true"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_approve_and_apply(self):
        request = self.make_shift_request_for_authorization()
        approved = ApproveShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)
        self.assertEqual(approved.status, ShiftChangeRequest.TrangThai.APPROVED)
        result = ApplyShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)
        request.refresh_from_db()
        self.assertEqual(request.trang_thai, ShiftChangeRequest.TrangThai.APPLIED)
        self.assertEqual(result.action, "update_assignment")


class PhaseCShiftChangeIntegrationTests(PhaseCTestMixin, TestCase):
    def test_approved_shift_change_not_applied_does_not_modify_assignment(self):
        assignment = self.make_assignment()
        replacement = self.make_staff("NV thay thế", phone="0902222333")
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau="SCR-NOAPPLY-001",
            nguoi_yeu_cau=self.staff,
            phan_cong_goc=assignment,
            nhan_vien_thay_the=replacement,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)
        assignment.refresh_from_db()
        self.assertEqual(assignment.nhan_vien, self.staff)

    def test_apply_approved_shift_change_updates_assignment_and_audits(self):
        assignment = self.make_assignment()
        replacement = self.make_staff("NV thay thế apply", phone="0903333444")
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau="SCR-APPLY-001",
            nguoi_yeu_cau=self.staff,
            phan_cong_goc=assignment,
            nhan_vien_thay_the=replacement,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)

        result = ApplyShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)
        assignment.refresh_from_db()
        request.refresh_from_db()

        self.assertEqual(result.assignment_id, assignment.pk)
        self.assertEqual(assignment.nhan_vien, replacement)
        self.assertEqual(request.trang_thai, ShiftChangeRequest.TrangThai.APPLIED)
        self.assertTrue(AuditLog.objects.filter(model_name="ShiftChangeRequest", object_id=str(request.pk)).exists())
        with self.assertRaises(ValidationError):
            ApplyShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)

    def test_apply_shift_change_refuses_locked_payroll_period(self):
        assignment = self.make_assignment(work_date=self.today)
        payroll = BangLuongThang.objects.create(
            ten_bang_luong="Kỳ lương đã khóa",
            thang=self.today.month,
            nam=self.today.year,
            trang_thai=BangLuongThang.TrangThai.LOCKED,
        )
        replacement = self.make_staff("NV thay thế khóa lương", phone="0904444555")
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau="SCR-LOCKED-001",
            nguoi_yeu_cau=self.staff,
            phan_cong_goc=assignment,
            nhan_vien_thay_the=replacement,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)
        with self.assertRaises(ValidationError):
            ApplyShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)
        assignment.refresh_from_db()
        self.assertEqual(assignment.nhan_vien, self.staff)
        self.assertEqual(payroll.trang_thai, BangLuongThang.TrangThai.LOCKED)

    def test_swap_rate_report_uses_shift_change_request_not_generic_proposal(self):
        assignment = self.make_assignment(work_date=self.today)
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau="SCR-RATE-001",
            nguoi_yeu_cau=self.staff,
            phan_cong_goc=assignment,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.CHANGE_SHIFT,
            ngay_mong_muon=self.today + timedelta(days=2),
            ca_mong_muon=self.shift,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)

        report = GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=assignment.tenant_id, system_context=True)
        row = next(item for item in report["results"] if item["muc_tieu_id"] == self.target.id)
        self.assertEqual(row["swap_count"], 0)
        self.assertEqual(row["shift_change_approved_count"], 1)
        self.assertEqual(row["metric_basis"], "APPLIED")

        ApplyShiftChangeRequestUseCase.execute(request.pk, actor=self.admin_user, tenant_id=request.tenant_id)
        report = GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=assignment.tenant_id, system_context=True)
        row = next(item for item in report["results"] if item["muc_tieu_id"] == self.target.id)
        self.assertEqual(row["swap_count"], 1)
        self.assertEqual(row["shift_change_applied_count"], 1)

        source = Path("operations/application/attendance_use_cases.py").read_text(encoding="utf-8")
        self.assertNotIn("loai_de_xuat='DOI_CA'", source)
        self.assertNotIn("trang_thai='DA_XU_LY'", source)
        self.assertIn("ShiftChangeRequest", source)


class PhaseCLeaveAndPayrollIntegrationTests(PhaseCTestMixin, TestCase):
    def test_operations_dashboard_flags_approved_leave_overlapping_shift(self):
        self.make_assignment(work_date=self.today)
        DonNghiPhep.objects.create(
            nhan_vien=self.staff,
            ma_don="NP-CONFLICT-001",
            loai_nghi=DonNghiPhep.LoaiNghi.PHEP_NAM,
            tu_ngay=self.today,
            den_ngay=self.today,
            so_ngay=Decimal("1"),
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
        )
        context = GetOperationsDashboardUseCase.execute(
            user=self.admin_user,
            tenant_id=self.staff.tenant_id,
            target_date=self.today,
        )
        self.assertEqual(context["stats"]["leave_schedule_conflicts"], 1)
        self.assertEqual(context["leave_schedule_conflicts"][0]["ma_don"], "NP-CONFLICT-001")

    def test_approved_paid_leave_is_payroll_snapshot_not_unauthorized_absence(self):
        self.make_assignment(work_date=self.today)
        DonNghiPhep.objects.create(
            nhan_vien=self.staff,
            ma_don="NP-PAID-001",
            loai_nghi=DonNghiPhep.LoaiNghi.PHEP_NAM,
            tu_ngay=self.today,
            den_ngay=self.today,
            so_ngay=Decimal("1"),
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
        )
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year)
        batch_context = PayrollCalculationService.build_batch_context(
            bang_luong=payroll,
            tenant_id=self.staff.tenant_id,
            nhan_vien_ids=[self.staff.id],
        )
        calculation = PayrollCalculationService.calculate_detail(self.staff, batch_context)
        snapshot = calculation["snapshot"]
        self.assertEqual(snapshot["approved_paid_leave_days_not_absent"], "1")
        self.assertEqual(calculation["so_ngay_nghi"], 0)

    def test_payroll_reconciliation_uses_new_sources_and_keeps_legacy_metadata(self):
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year)
        ChiTietLuong.objects.create(
            bang_luong=payroll,
            nhan_vien=self.staff,
            luong_chinh=Decimal("5000000"),
            thuc_lanh=Decimal("5000000"),
        )
        advance = TamUngLuong.objects.create(
            nhan_vien=self.staff,
            so_phieu="TU-REC-001",
            bang_luong_du_kien=payroll,
            so_tien=Decimal("500000"),
            trang_thai=TamUngLuong.TrangThai.APPROVED,
        )
        deduction = KhoanKhauTruNhanVien.objects.create(
            nhan_vien=self.staff,
            so_chung_tu="KT-REC-001",
            loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.BAO_HIEM,
            bang_luong_du_kien=payroll,
            so_tien=Decimal("300000"),
            trang_thai=KhoanKhauTruNhanVien.TrangThai.APPROVED,
        )
        HoSoBaoHiem.objects.create(
            nhan_vien=self.staff,
            so_bao_hiem="BHXH-REC-001",
            loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
            ngay_tham_gia=self.today - timedelta(days=30),
            trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
        )
        DonNghiPhep.objects.create(
            nhan_vien=self.staff,
            ma_don="NP-UNPAID-001",
            loai_nghi=DonNghiPhep.LoaiNghi.KHONG_LUONG,
            tu_ngay=self.today,
            den_ngay=self.today,
            so_ngay=Decimal("1"),
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
        )

        result = PayrollSourceReconciliationUseCase.execute(
            bang_luong=payroll,
            tenant_id=self.staff.tenant_id,
            actor=self.admin_user,
        )
        detail = ChiTietLuong.objects.get(bang_luong=payroll, nhan_vien=self.staff)
        snapshot = detail.nguon_du_lieu_snapshot["phase_c_reconciliation"]

        self.assertEqual(result["reconciled_count"], 1)
        self.assertEqual(detail.ung_luong, advance.so_tien)
        self.assertEqual(detail.bao_hiem, deduction.so_tien)
        self.assertEqual(detail.so_ngay_nghi, 1)
        self.assertIn(advance.pk, snapshot["tam_ung_luong_ids"])
        self.assertIn(deduction.pk, snapshot["khoan_khau_tru_ids"])
        self.assertTrue(snapshot["legacy_sources"]["enabled"])

    def test_payroll_reconciliation_does_not_double_count_linked_advance_deduction(self):
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year)
        advance = TamUngLuong.objects.create(
            nhan_vien=self.staff,
            so_phieu="TU-NODOUBLE-001",
            bang_luong_du_kien=payroll,
            so_tien=Decimal("500000"),
            trang_thai=TamUngLuong.TrangThai.APPROVED,
        )
        deduction = KhoanKhauTruNhanVien.objects.create(
            nhan_vien=self.staff,
            so_chung_tu="KT-NODOUBLE-001",
            loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.TAM_UNG,
            tam_ung=advance,
            bang_luong_du_kien=payroll,
            so_tien=Decimal("500000"),
            trang_thai=KhoanKhauTruNhanVien.TrangThai.APPROVED,
        )
        PayrollSourceReconciliationUseCase.execute(
            bang_luong=payroll,
            tenant_id=self.staff.tenant_id,
            actor=self.admin_user,
        )
        detail = ChiTietLuong.objects.get(bang_luong=payroll, nhan_vien=self.staff)
        snapshot = detail.nguon_du_lieu_snapshot["phase_c_reconciliation"]
        self.assertEqual(detail.ung_luong, Decimal("500000"))
        self.assertIn(advance.pk, snapshot["tam_ung_luong_excluded_due_to_deduction_ids"])
        self.assertIn(deduction.pk, snapshot["khoan_khau_tru_ids"])

    def test_payroll_reconciliation_refuses_locked_or_paid_period(self):
        payroll = BangLuongThang.objects.create(
            thang=self.today.month,
            nam=self.today.year,
            trang_thai=BangLuongThang.TrangThai.PAID,
        )
        with self.assertRaises(ValueError):
            PayrollSourceReconciliationUseCase.execute(
                bang_luong=payroll,
                tenant_id=self.staff.tenant_id,
                actor=self.admin_user,
            )
