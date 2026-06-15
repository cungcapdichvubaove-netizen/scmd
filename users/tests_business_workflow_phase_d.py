# -*- coding: utf-8 -*-
"""Phase D business workflow hardening tests.

These tests intentionally target integration boundaries left after Phase C v2:
report scoping, payroll reconciliation preservation, leave proration, and static
regression protection against direct workflow status mutation.
"""

from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal
from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role

from accounting.application.payroll_reconciliation_use_case import PayrollSourceReconciliationUseCase
from accounting.application.payroll_use_cases import CalculatePayrollUseCase
from accounting.models import BangLuongThang, ChiTietLuong, KhoanKhauTruNhanVien, TamUngLuong
from accounting.services.payroll_calculation import PayrollCalculationService
from clients.models import HopDong, MucTieu
from operations.application.attendance_use_cases import GetSwapRateReportUseCase
from operations.models import CaLamViec, PhanCongCaTruc, ShiftChangeRequest, ViTriChot
from users.models import CauHinhMaNhanVien, DonNghiPhep, NhanVien


class PhaseDTestMixin:
    def setUp(self):
        CauHinhMaNhanVien.objects.all().delete()
        CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
        self.today = timezone.localdate()
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="phase-d-admin",
            email="phase-d-admin@example.com",
            password="password",
        )
        self.staff = self.make_staff("NV Phase D", phone="0981000001")
        self.contract = self.make_service_contract("HD-DV-D-001")
        self.target = self.make_target(self.contract, "Mục tiêu Phase D")
        self.post = ViTriChot.objects.create(muc_tieu=self.target, ten_vi_tri="Cổng chính")
        self.shift = CaLamViec.objects.create(ten_ca="Ca ngày D", gio_bat_dau=time(6, 0), gio_ket_thuc=time(18, 0))

    def make_staff(self, name, *, phone, user=None, status=NhanVien.TrangThaiLamViec.CHINH_THUC):
        if user is not None:
            try:
                staff = user.nhan_vien
            except NhanVien.DoesNotExist:
                staff = None
            if staff is not None:
                staff.ho_ten = name
                staff.sdt_chinh = phone
                staff.ngay_vao_lam = self.today - timedelta(days=120)
                staff.trang_thai_lam_viec = status
                staff.save()
                return staff

        return NhanVien.objects.create(
            user=user,
            ho_ten=name,
            sdt_chinh=phone,
            ngay_vao_lam=self.today - timedelta(days=120),
            trang_thai_lam_viec=status,
        )

    def make_user_and_staff(self, username, full_name, *, phone, role=None):
        user = self.User.objects.create_user(username=username, password="password")
        if role:
            assign_role(user, role)
        staff = self.make_staff(full_name, phone=phone, user=user)
        return user, staff

    def make_service_contract(self, code):
        return HopDong.objects.create(
            so_hop_dong=code,
            ngay_ky=self.today - timedelta(days=30),
            ngay_hieu_luc=self.today - timedelta(days=30),
            ngay_het_han=self.today + timedelta(days=365),
            gia_tri=Decimal("10000000"),
        )

    def make_target(self, contract, name, *, manager=None):
        return MucTieu.objects.create(
            hop_dong=contract,
            ten_muc_tieu=name,
            dia_chi="Hà Nội",
            so_luong_nhan_vien=1,
            quan_ly_muc_tieu=manager,
        )

    def make_assignment(self, *, target=None, staff=None, work_date=None):
        target = target or self.target
        post = self.post if target.pk == self.target.pk else ViTriChot.objects.create(muc_tieu=target, ten_vi_tri=f"Chốt {target.pk}")
        return PhanCongCaTruc.objects.create(
            nhan_vien=staff or self.staff,
            vi_tri_chot=post,
            ca_lam_viec=self.shift,
            ngay_truc=work_date or self.today,
        )

    def make_applied_shift_request(self, *, target=None, code="SCR-D-001"):
        assignment = self.make_assignment(target=target or self.target)
        request = ShiftChangeRequest.objects.create(
            ma_yeu_cau=code,
            nguoi_yeu_cau=self.staff,
            phan_cong_goc=assignment,
            loai_yeu_cau=ShiftChangeRequest.LoaiYeuCau.CHANGE_SHIFT,
            ngay_mong_muon=self.today + timedelta(days=1),
            ca_mong_muon=self.shift,
            trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
        )
        request.transition_status(ShiftChangeRequest.TrangThai.APPROVED, actor=self.admin_user)
        request.transition_status(ShiftChangeRequest.TrangThai.APPLIED, actor=self.admin_user)
        return request


class PhaseDSwapRateScopeTests(PhaseDTestMixin, TestCase):
    def test_regular_employee_and_accounting_role_cannot_view_swap_rate_report(self):
        regular_user, _ = self.make_user_and_staff("phase-d-regular", "NV thường", phone="0981000002")
        accountant_user, _ = self.make_user_and_staff("phase-d-accountant", "Kế toán", phone="0981000003", role="ke_toan")

        with self.assertRaises(PermissionDenied):
            GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=self.staff.tenant_id, user=regular_user)
        with self.assertRaises(PermissionDenied):
            GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=self.staff.tenant_id, user=accountant_user)

        client = APIClient()
        client.force_authenticate(user=regular_user)
        response = client.get(reverse("operations:report_swap_rate_api"))
        self.assertEqual(response.status_code, 403)

    def test_commander_scope_only_returns_managed_targets(self):
        commander_user, commander = self.make_user_and_staff("phase-d-commander", "Đội trưởng D", phone="0981000004", role="doi_truong")
        self.target.quan_ly_muc_tieu = commander
        self.target.save(update_fields=["quan_ly_muc_tieu"])
        other_contract = self.make_service_contract("HD-DV-D-002")
        other_target = self.make_target(other_contract, "Mục tiêu ngoài scope")
        self.make_applied_shift_request(target=self.target, code="SCR-D-SCOPE-IN")
        self.make_applied_shift_request(target=other_target, code="SCR-D-SCOPE-OUT")

        report = GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=self.staff.tenant_id, user=commander_user)
        returned_ids = {row["muc_tieu_id"] for row in report["results"]}
        self.assertEqual(returned_ids, {self.target.pk})
        self.assertEqual(report["scope"], "user_allowed_targets")

    def test_superuser_can_view_all_swap_rate_targets(self):
        other_contract = self.make_service_contract("HD-DV-D-003")
        other_target = self.make_target(other_contract, "Mục tiêu toàn cục")
        self.make_applied_shift_request(target=self.target, code="SCR-D-GLOBAL-IN")
        self.make_applied_shift_request(target=other_target, code="SCR-D-GLOBAL-OUT")

        report = GetSwapRateReportUseCase.execute(month=self.today.month, year=self.today.year, tenant_id=self.staff.tenant_id, user=self.admin_user)
        returned_ids = {row["muc_tieu_id"] for row in report["results"]}
        self.assertTrue({self.target.pk, other_target.pk}.issubset(returned_ids))

    def test_swap_rate_report_requires_explicit_system_context_for_unscoped_calls(self):
        self.make_applied_shift_request(target=self.target, code="SCR-D-SYSTEM-CTX")

        with self.assertRaises(PermissionDenied):
            GetSwapRateReportUseCase.execute(
                month=self.today.month,
                year=self.today.year,
                tenant_id=self.staff.tenant_id,
            )

        report = GetSwapRateReportUseCase.execute(
            month=self.today.month,
            year=self.today.year,
            tenant_id=self.staff.tenant_id,
            system_context=True,
        )
        self.assertEqual(report["scope"], "system_all_targets")


class PhaseDPayrollPipelineTests(PhaseDTestMixin, TestCase):
    def test_calculate_after_reconcile_preserves_phase_c_snapshot_and_marks_needs_reconciliation(self):
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year)
        ChiTietLuong.objects.create(bang_luong=payroll, nhan_vien=self.staff, luong_chinh=Decimal("5000000"), thuc_lanh=Decimal("5000000"))
        TamUngLuong.objects.create(
            nhan_vien=self.staff,
            so_phieu="TU-D-KEEP-001",
            bang_luong_du_kien=payroll,
            so_tien=Decimal("400000"),
            trang_thai=TamUngLuong.TrangThai.APPROVED,
        )
        PayrollSourceReconciliationUseCase.execute(bang_luong=payroll, tenant_id=self.staff.tenant_id, actor=self.admin_user)
        reconciled_detail = ChiTietLuong.objects.get(bang_luong=payroll, nhan_vien=self.staff)
        original_phase_c = reconciled_detail.nguon_du_lieu_snapshot["phase_c_reconciliation"]

        CalculatePayrollUseCase.execute(nhan_vien=self.staff, bang_luong=payroll, tenant_id=self.staff.tenant_id)
        reconciled_detail.refresh_from_db()
        snapshot = reconciled_detail.nguon_du_lieu_snapshot

        self.assertEqual(snapshot["phase_c_reconciliation"], original_phase_c)
        self.assertEqual(snapshot["phase_d_reconciliation_status"]["status"], "NEEDS_RECONCILIATION")

    def test_calculate_does_not_mutate_locked_or_paid_payroll(self):
        payroll = BangLuongThang.objects.create(thang=self.today.month, nam=self.today.year, trang_thai=BangLuongThang.TrangThai.LOCKED)
        with self.assertRaises(ValueError):
            CalculatePayrollUseCase.execute(nhan_vien=self.staff, bang_luong=payroll, tenant_id=self.staff.tenant_id)

    def test_leave_days_are_prorated_when_leave_crosses_month_boundary(self):
        payroll = BangLuongThang.objects.create(thang=6, nam=self.today.year)
        DonNghiPhep.objects.create(
            nhan_vien=self.staff,
            ma_don="NP-D-SPAN-001",
            loai_nghi=DonNghiPhep.LoaiNghi.KHONG_LUONG,
            tu_ngay=timezone.datetime(self.today.year, 5, 30).date(),
            den_ngay=timezone.datetime(self.today.year, 6, 2).date(),
            so_ngay=Decimal("4"),
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
        )

        batch_context = PayrollCalculationService.build_batch_context(
            bang_luong=payroll,
            tenant_id=self.staff.tenant_id,
            nhan_vien_ids=[self.staff.id],
        )
        calculation = PayrollCalculationService.calculate_detail(self.staff, batch_context)
        snapshot = calculation["snapshot"]

        self.assertEqual(snapshot["leave_total_days"], "4")
        self.assertEqual(snapshot["leave_days_in_this_period"], "2.00")
        self.assertEqual(snapshot["approved_unpaid_leave_days"], "2.00")

        PayrollSourceReconciliationUseCase.execute(bang_luong=payroll, tenant_id=self.staff.tenant_id, actor=self.admin_user)
        detail = ChiTietLuong.objects.get(bang_luong=payroll, nhan_vien=self.staff)
        phase_c = detail.nguon_du_lieu_snapshot["phase_c_reconciliation"]
        self.assertEqual(phase_c["leave_total_days"], "4")
        self.assertEqual(phase_c["leave_days_in_this_period"], "2.00")
        self.assertEqual(phase_c["unpaid_leave_days"], "2.00")


class PhaseDRoadmapStaticTests(SimpleTestCase):
    def test_phase_e_documents_decimal_half_day_payroll_absence_followup(self):
        roadmap = Path("docs/BUSINESS_DOMAIN_PHASE_CD_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("half-day", roadmap)
        self.assertIn("decimal leave/payroll absence", roadmap)



class PhaseDDirectStatusMutationStaticTests(SimpleTestCase):
    """Static guard for new lifecycle workflows.\n\n    Legacy modules still contain historical status assignments; this guard is\n    scoped to the Phase A+B/C business workflow files and fails if future\n    production code mutates ``trang_thai`` directly outside sanctioned workflow\n    paths.\n    """

    SCAN_ROOTS = ["users", "operations", "accounting", "clients"]
    STATUS_PATTERN = re.compile(r"\.trang_thai\s*=(?!=)")
    ALWAYS_ALLOWED_PARTS = {"/tests", "/migrations"}
    ALLOWED_ADMIN_FILES = {
        "users/admin.py",
        "operations/admin.py",
        "clients/admin.py",
        "accounting/admin.py",
    }
    ALLOWED_MODEL_FILES = {
        "users/models.py",
        "operations/models.py",
        "clients/models.py",
        "accounting/models.py",
    }
    LEGACY_ALLOWED_FILES = {
        "accounting/services/payroll.py",  # legacy payroll batch status, not Phase A+B lifecycle model
        "operations/application/alive_check_use_cases.py",  # legacy alive-check lifecycle; not Phase A+B workflow record
        "operations/application/attendance_use_cases.py",  # legacy KiemTraQuanSo response status mutation
        "operations/application/maintenance_use_cases.py",  # legacy alive-check maintenance status mutation
        "accounting/application/payroll_lock_use_case.py",  # sanctioned payroll period lock workflow
        "accounting/application/payroll_use_cases.py",  # sanctioned payroll batch status workflow
    }

    def test_phase_d_static_guard_blocks_direct_workflow_status_mutation(self):
        violations = []
        for root in self.SCAN_ROOTS:
            for path in Path(root).rglob("*.py"):
                path_text = path.as_posix()
                body = path.read_text(encoding="utf-8")
                if not self.STATUS_PATTERN.search(body):
                    continue
                if any(part in f"/{path_text}" for part in self.ALWAYS_ALLOWED_PARTS):
                    continue
                if path_text in self.LEGACY_ALLOWED_FILES:
                    continue
                if "/application/" in f"/{path_text}":
                    if "transition_status(" in body or "WorkflowTransitionPolicy" in body:
                        continue
                    violations.append(f"{path_text}: application status mutation must use transition_status()/policy or explicit LEGACY_ALLOWED_FILES entry")
                    continue
                if path_text in self.ALLOWED_ADMIN_FILES:
                    self.assertIn("WorkflowTransitionPolicy", body, f"{path_text} must guard admin status edits")
                    continue
                if path_text in self.ALLOWED_MODEL_FILES:
                    for line_no, line in enumerate(body.splitlines(), start=1):
                        if self.STATUS_PATTERN.search(line) and "self.trang_thai = new_status" not in line:
                            violations.append(f"{path_text}:{line_no}:{line.strip()}")
                    continue
                violations.append(path_text)
        self.assertEqual([], violations)
