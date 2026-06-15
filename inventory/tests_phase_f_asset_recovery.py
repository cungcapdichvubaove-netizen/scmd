# -*- coding: utf-8 -*-
"""Phase F asset recovery and offboarding inventory workflow tests."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rolepermissions.roles import assign_role

from accounting.models import KhoanKhauTruNhanVien
from inventory.admin import PhieuThuHoiAdmin
from inventory.application.asset_recovery_use_cases import (
    ApproveAssetDamageReportUseCase,
    AssetRecoveryError,
    GetEmployeeOutstandingAssetsUseCase,
    PostAssetRecoveryUseCase,
    VoidAssetRecoveryUseCase,
)
from inventory.application.inventory_document_use_cases import InventoryDocumentUseCase
from inventory.models import (
    BienBanMatHongVatTu,
    ChiTietPhieuThuHoi,
    ChiTietPhieuXuat,
    LoaiVatTu,
    PhieuThuHoi,
    PhieuXuat,
    VatTu,
)
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog
from users.models import NhanVien, OffboardingChecklist, QuyetDinhNghiViec


class PhaseFAssetRecoveryMixin:
    def setUp(self):
        self.User = get_user_model()
        self.actor = self.User.objects.create_superuser(username="phase-f-super", email="phase-f@example.com", password="pw")
        assign_role(self.actor, "thu_kho")
        self.hr_user = self.User.objects.create_user(username="phase-f-hr", password="pw")
        assign_role(self.hr_user, "nhan_su")
        self.regular_user = self.User.objects.create_user(username="phase-f-regular", password="pw")
        self.employee = NhanVien.objects.create(ho_ten="Nguyễn Văn Thu Hồi", trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC)
        self.other_employee = NhanVien.objects.create(ho_ten="Trần Văn Khác", trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC)
        self.category = LoaiVatTu.objects.create(ten_loai="Đồng phục")
        self.vat_tu = VatTu.objects.create(
            loai_vat_tu=self.category,
            ten_vat_tu="Áo bảo vệ",
            don_vi_tinh="Cái",
            gia_ban=Decimal("150000"),
            so_luong_ton=10,
            muc_canh_bao=2,
        )
        self.issue = PhieuXuat.objects.create(
            ma_phieu="PX-F-001",
            loai_xuat="CAP_PHAT",
            nhan_vien_nhan=self.employee,
            ghi_chu="Cấp phát Phase F",
        )
        self.issue_line = ChiTietPhieuXuat.objects.create(phieu_xuat=self.issue, vat_tu=self.vat_tu, so_luong=2)
        self.mark_issue_as_posted_source_for_recovery_tests()
        self.vat_tu.refresh_from_db()

    def mark_issue_as_posted_source_for_recovery_tests(self):
        """Post and refresh the issue document used as recovery source.

        ChiTietPhieuThuHoi.clean() deliberately rejects recovery from DRAFT
        issue documents.  These Phase F tests are not testing the issue-posting
        workflow, so the fixture prepares a valid POSTED source document and
        refreshes related objects to avoid stale FK caches from the original
        in-memory DRAFT PhieuXuat instance.
        """
        self.issue = InventoryDocumentUseCase.post_inventory_document(self.issue, user=self.actor)
        self.issue.refresh_from_db()
        self.issue_line = (
            ChiTietPhieuXuat.objects
            .select_related("phieu_xuat", "vat_tu")
            .get(pk=self.issue_line.pk)
        )
        if self.issue.trang_thai != PhieuXuat.TrangThai.POSTED:
            raise AssertionError("Phase F recovery fixture must use a POSTED issue document.")
        if self.issue_line.phieu_xuat.trang_thai != PhieuXuat.TrangThai.POSTED:
            raise AssertionError("Phase F recovery fixture issue line must resolve to a POSTED issue document.")

    def make_recovery(self, *, good=1, damaged=0, employee=None, code="PTH-F-001"):
        employee = employee or self.employee
        recovery = PhieuThuHoi.objects.create(
            ma_phieu=code,
            nhan_vien=employee,
            ngay_thu_hoi=timezone.now(),
            nguoi_thu_hoi=getattr(self.actor, "nhan_vien", None),
            ghi_chu="Thu hồi Phase F",
        )
        line = ChiTietPhieuThuHoi.objects.create(
            phieu_thu_hoi=recovery,
            chi_tiet_phieu_xuat=self.issue_line,
            vat_tu=self.vat_tu,
            so_luong_thu_hoi=good + damaged,
            so_luong_nhap_lai_kho=good,
            so_luong_mat_hong=damaged,
            tinh_trang=ChiTietPhieuThuHoi.TinhTrang.HONG if damaged else ChiTietPhieuThuHoi.TinhTrang.TOT,
        )
        return recovery, line


class PhaseFAssetRecoveryWorkflowTests(PhaseFAssetRecoveryMixin, TestCase):
    def test_recover_one_good_item_increases_stock_and_leaves_one_outstanding(self):
        self.assertEqual(self.vat_tu.so_luong_ton, 8)
        recovery, _ = self.make_recovery(good=1, damaged=0)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)

        self.vat_tu.refresh_from_db()
        outstanding = GetEmployeeOutstandingAssetsUseCase.execute(nhan_vien=self.employee)

        self.assertEqual(self.vat_tu.so_luong_ton, 9)
        self.assertEqual(sum(item["outstanding_quantity"] for item in outstanding), 1)
        self.assertTrue(InventoryLedgerEntry.objects.filter(phieu_thu_hoi=recovery, direction=InventoryLedgerEntry.Direction.IN).exists())

    def test_recovery_cannot_exceed_outstanding(self):
        recovery, _ = self.make_recovery(good=3, damaged=0)
        with self.assertRaises(AssetRecoveryError):
            PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)

    def test_recovery_rejects_original_issue_for_different_employee(self):
        with self.assertRaises(ValidationError):
            self.make_recovery(good=1, damaged=0, employee=self.other_employee, code="PTH-F-OTHER")

    def test_damaged_item_creates_damage_report(self):
        recovery, _ = self.make_recovery(good=0, damaged=1)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)

        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)
        self.assertEqual(report.so_luong, 1)
        self.assertEqual(report.tong_tien, Decimal("150000"))
        self.assertEqual(report.trang_thai, BienBanMatHongVatTu.TrangThai.DRAFT)

    def test_approve_damage_report_creates_pending_deduction(self):
        recovery, _ = self.make_recovery(good=0, damaged=1)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)

        deduction = ApproveAssetDamageReportUseCase.execute(bien_ban=report, actor=self.actor)

        self.assertEqual(deduction.trang_thai, KhoanKhauTruNhanVien.TrangThai.PENDING_APPROVAL)
        self.assertEqual(deduction.loai_khau_tru, KhoanKhauTruNhanVien.LoaiKhauTru.DEN_BU)
        self.assertEqual(deduction.so_tien, Decimal("150000"))

    def test_offboarding_cannot_complete_if_assets_outstanding(self):
        decision = QuyetDinhNghiViec.objects.create(
            nhan_vien=self.employee,
            so_quyet_dinh="QD-F-001",
            ngay_quyet_dinh=timezone.localdate(),
            ngay_hieu_luc=timezone.localdate() + timedelta(days=1),
            trang_thai=QuyetDinhNghiViec.TrangThai.APPROVED,
        )
        checklist = OffboardingChecklist.objects.create(
            quyet_dinh=decision,
            thu_hoi_dong_phuc=True,
            ban_giao_tai_san=True,
            khoa_tai_khoan=True,
            chot_cong=True,
            quyet_toan_luong=True,
        )
        with self.assertRaises(ValidationError):
            checklist.mark_completed(actor=self.actor)

    def test_offboarding_completes_after_assets_recovered_and_damage_processed(self):
        decision = QuyetDinhNghiViec.objects.create(
            nhan_vien=self.employee,
            so_quyet_dinh="QD-F-002",
            ngay_quyet_dinh=timezone.localdate(),
            ngay_hieu_luc=timezone.localdate() + timedelta(days=1),
            trang_thai=QuyetDinhNghiViec.TrangThai.APPROVED,
        )
        checklist = OffboardingChecklist.objects.create(
            quyet_dinh=decision,
            thu_hoi_dong_phuc=True,
            ban_giao_tai_san=True,
            khoa_tai_khoan=True,
            chot_cong=True,
            quyet_toan_luong=True,
        )
        recovery, _ = self.make_recovery(good=1, damaged=1, code="PTH-F-ALL")
        recovery.quyet_dinh_nghi_viec = decision
        recovery.offboarding_checklist = checklist
        recovery.save(update_fields=["quyet_dinh_nghi_viec", "offboarding_checklist"])
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)
        ApproveAssetDamageReportUseCase.execute(bien_ban=report, actor=self.actor)

        checklist.mark_completed(actor=self.actor)
        checklist.refresh_from_db()
        self.assertTrue(checklist.hoan_tat)

    def test_posted_recovery_cannot_be_deleted(self):
        recovery, _ = self.make_recovery(good=1, damaged=0)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        with self.assertRaises(ValidationError):
            recovery.delete()

    def test_void_recovery_reverses_stock(self):
        recovery, _ = self.make_recovery(good=1, damaged=0)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, reason="Sai biên bản", actor=self.actor)

        self.vat_tu.refresh_from_db()
        recovery.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 8)
        self.assertEqual(recovery.trang_thai, PhieuThuHoi.TrangThai.VOIDED)
        self.assertTrue(InventoryLedgerEntry.objects.filter(phieu_thu_hoi=recovery, direction=InventoryLedgerEntry.Direction.OUT).exists())

    def test_void_recovery_blocked_if_damage_report_draft_and_does_not_reverse_ledger(self):
        recovery, _ = self.make_recovery(good=0, damaged=1)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)
        stock_before = self.vat_tu.so_luong_ton
        reversal_count_before = InventoryLedgerEntry.objects.filter(
            phieu_thu_hoi=recovery,
            direction=InventoryLedgerEntry.Direction.OUT,
        ).count()

        with self.assertRaises(AssetRecoveryError):
            VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, reason="Còn biên bản mất/hỏng", actor=self.actor)

        self.vat_tu.refresh_from_db()
        recovery.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, stock_before)
        self.assertEqual(recovery.trang_thai, PhieuThuHoi.TrangThai.POSTED)
        self.assertEqual(report.trang_thai, BienBanMatHongVatTu.TrangThai.DRAFT)
        self.assertEqual(
            InventoryLedgerEntry.objects.filter(
                phieu_thu_hoi=recovery,
                direction=InventoryLedgerEntry.Direction.OUT,
            ).count(),
            reversal_count_before,
        )

    def test_void_recovery_blocked_if_damage_deduction_pending_approval(self):
        recovery, _ = self.make_recovery(good=0, damaged=1)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)
        deduction = ApproveAssetDamageReportUseCase.execute(bien_ban=report, actor=self.actor)
        self.assertEqual(deduction.trang_thai, KhoanKhauTruNhanVien.TrangThai.PENDING_APPROVAL)
        reversal_count_before = InventoryLedgerEntry.objects.filter(
            phieu_thu_hoi=recovery,
            direction=InventoryLedgerEntry.Direction.OUT,
        ).count()

        with self.assertRaises(AssetRecoveryError):
            VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, reason="Khấu trừ chưa hủy", actor=self.actor)

        recovery.refresh_from_db()
        self.assertEqual(recovery.trang_thai, PhieuThuHoi.TrangThai.POSTED)
        self.assertEqual(
            InventoryLedgerEntry.objects.filter(
                phieu_thu_hoi=recovery,
                direction=InventoryLedgerEntry.Direction.OUT,
            ).count(),
            reversal_count_before,
        )

    def test_void_recovery_blocked_if_related_deduction_applied(self):
        recovery, _ = self.make_recovery(good=0, damaged=1)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        report = BienBanMatHongVatTu.objects.get(phieu_thu_hoi=recovery)
        deduction = ApproveAssetDamageReportUseCase.execute(bien_ban=report, actor=self.actor)
        deduction.trang_thai = KhoanKhauTruNhanVien.TrangThai.APPLIED
        deduction.save(update_fields=["trang_thai"])

        with self.assertRaises(AssetRecoveryError):
            VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, reason="Không hợp lệ", actor=self.actor)

    def test_regular_and_hr_users_cannot_post_warehouse_recovery(self):
        recovery, _ = self.make_recovery(good=1, damaged=0)
        with self.assertRaises(PermissionDenied):
            PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.regular_user)
        with self.assertRaises(PermissionDenied):
            PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.hr_user)

    def test_warehouse_or_director_actor_can_post(self):
        recovery, _ = self.make_recovery(good=1, damaged=0)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        recovery.refresh_from_db()
        self.assertEqual(recovery.trang_thai, PhieuThuHoi.TrangThai.POSTED)

    def test_audit_log_created_for_post_and_void(self):
        recovery, _ = self.make_recovery(good=1, damaged=0)
        PostAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, actor=self.actor)
        VoidAssetRecoveryUseCase.execute(phieu_thu_hoi=recovery, reason="Audit", actor=self.actor)
        self.assertEqual(AuditLog.objects.filter(module="inventory", model_name="PhieuThuHoi", object_id=str(recovery.pk)).count(), 2)


class PhaseFAssetRecoveryStaticTests(SimpleTestCase):
    def test_phase_f_does_not_use_fake_receipt_or_payroll_detail_write(self):
        source = Path("inventory/application/asset_recovery_use_cases.py").read_text(encoding="utf-8")
        self.assertNotIn("PhieuNhap", source)
        self.assertNotIn("ChiTietLuong", source)
        self.assertIn("KhoanKhauTruNhanVien", source)

    def test_phase_f_v2_void_guard_blocks_active_damage_and_deductions_before_reversal(self):
        source = Path("inventory/application/asset_recovery_use_cases.py").read_text(encoding="utf-8")
        reversal_index = source.index("InventoryLedgerEntry.MovementType.REVERSAL")
        active_damage_guard_index = source.index("active_damage_reports.exists()")
        linked_deduction_guard_index = source.index("linked_deduction_reports.exclude")
        self.assertLess(active_damage_guard_index, reversal_index)
        self.assertLess(linked_deduction_guard_index, reversal_index)
        self.assertIn("Đã xác nhận không còn biên bản mất/hỏng hoặc khoản khấu trừ còn hiệu lực", source)

    def test_recovery_admin_disables_delete_for_posted_documents(self):
        source = Path("inventory/admin.py").read_text(encoding="utf-8")
        self.assertIn("class PhieuThuHoiAdmin", source)
        self.assertIn("obj.trang_thai != PhieuThuHoi.TrangThai.DRAFT", source)
        self.assertIn("class BienBanMatHongVatTuAdmin", source)
