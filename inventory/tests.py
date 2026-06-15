<<<<<<< HEAD
# -*- coding: utf-8 -*-

from django.contrib.auth.models import Permission, User
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from rolepermissions.roles import assign_role

from inventory.cache_utils import (
    build_category_cache_key,
    build_dashboard_cache_key,
    invalidate_inventory_cache,
)
from inventory.admin import InventoryVoidActionForm, PhieuXuatAdmin, VatTuAdmin
from inventory.application.inventory_document_use_cases import InventoryDocumentUseCase
from inventory.models import ChiTietPhieuXuat, LoaiVatTu, PhieuXuat, VatTu
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog
from inventory.views import bao_cao_ton_kho


class InventoryTransactionTest(TestCase):
    def setUp(self):
        self.loai = LoaiVatTu.objects.create(ten_loai="Cong cu ho tro")
        self.vat_tu = VatTu.objects.create(
            loai_vat_tu=self.loai,
            ten_vat_tu="Bo dam Motorola",
            don_vi_tinh="Cai",
            gia_ban=150000,
            so_luong_ton=10,
            muc_canh_bao=2,
        )
        self.user = User.objects.create_user(
            username="kho_user",
            email="kho@test.com",
            password="password",
        )
        assign_role(self.user, "thu_kho")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=[
                    "view_phieunhap",
                    "change_phieunhap",
                    "delete_phieunhap",
                    "view_phieuxuat",
                    "change_phieuxuat",
                    "delete_phieuxuat",
                ],
            )
        )
        self.request_factory = RequestFactory()
        self.admin_site = admin.sites.AdminSite()

    def test_inventory_sale_transaction_updates_payroll_deduction_total(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-001",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Ban tru luong",
        )

        ChiTietPhieuXuat.objects.create(
            phieu_xuat=phieu,
            vat_tu=self.vat_tu,
            so_luong=2,
        )

        self.vat_tu.refresh_from_db()
        phieu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 10)
        self.assertEqual(phieu.trang_thai, "DRAFT")
        self.assertEqual(phieu.trang_thai_thanh_toan, "CHUA_TRU")
        self.assertEqual(phieu.tong_tien_phai_thu, 0)

        InventoryDocumentUseCase.post_inventory_document(phieu, user=self.user)

        self.vat_tu.refresh_from_db()
        phieu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 8)
        self.assertEqual(phieu.trang_thai, "POSTED")
        self.assertEqual(phieu.tong_tien_phai_thu, 300000)
        self.assertEqual(
            InventoryLedgerEntry.objects.filter(
                phieu_xuat=phieu,
                movement_type=InventoryLedgerEntry.MovementType.POSTING,
            ).count(),
            1,
        )

    def test_void_posted_issue_restores_stock(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-002",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Ban tru luong",
        )
        ChiTietPhieuXuat.objects.create(
            phieu_xuat=phieu,
            vat_tu=self.vat_tu,
            so_luong=3,
        )

        InventoryDocumentUseCase.post_inventory_document(phieu, user=self.user)
        phieu.refresh_from_db()
        InventoryDocumentUseCase.void_inventory_document(
            phieu,
            reason="Void test",
            user=self.user,
        )

        self.vat_tu.refresh_from_db()
        phieu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 10)
        self.assertEqual(phieu.trang_thai, "VOIDED")
        self.assertEqual(phieu.tong_tien_phai_thu, 0)
        self.assertEqual(InventoryLedgerEntry.objects.filter(phieu_xuat=phieu).count(), 2)
        self.assertTrue(
            InventoryLedgerEntry.objects.filter(
                phieu_xuat=phieu,
                movement_type=InventoryLedgerEntry.MovementType.REVERSAL,
                quantity_delta=3,
            ).exists()
        )

        self.assertEqual(
            AuditLog.objects.filter(
                module="inventory",
                model_name="PhieuXuat",
                object_id=str(phieu.pk),
            ).count(),
            2,
        )

    def test_posted_issue_cannot_be_hard_deleted(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-003",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Ban tru luong",
        )
        ChiTietPhieuXuat.objects.create(
            phieu_xuat=phieu,
            vat_tu=self.vat_tu,
            so_luong=1,
        )

        InventoryDocumentUseCase.post_inventory_document(phieu, user=self.user)

        with self.assertRaises(ValidationError):
            phieu.delete()

    def test_vattu_admin_marks_stock_as_readonly(self):
        model_admin = VatTuAdmin(VatTu, self.admin_site)
        self.assertIn("so_luong_ton", model_admin.get_readonly_fields(self.request_factory.get("/admin/")))

    def test_issue_detail_clean_rejects_quantity_above_current_stock_on_edit(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-004",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Draft edit",
        )
        detail = ChiTietPhieuXuat.objects.create(
            phieu_xuat=phieu,
            vat_tu=self.vat_tu,
            so_luong=2,
        )
        detail.so_luong = 11

        with self.assertRaises(ValidationError):
            detail.clean()

    def test_void_action_form_exposes_reason_field(self):
        form = InventoryVoidActionForm()
        self.assertIn("void_reason", form.fields)

    def test_void_inventory_admin_action_requires_reason(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-006",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Void admin",
            trang_thai=PhieuXuat.TrangThai.POSTED,
        )
        request = self.request_factory.post("/admin/inventory/phieuxuat/")
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        request.user = self.user

        model_admin = PhieuXuatAdmin(PhieuXuat, self.admin_site)
        model_admin.void_inventory_documents(request, PhieuXuat.objects.filter(pk=phieu.pk))

        phieu.refresh_from_db()
        self.assertEqual(phieu.trang_thai, PhieuXuat.TrangThai.POSTED)

    def test_ledger_enforces_unique_issue_detail_movement(self):
        phieu = PhieuXuat.objects.create(
            ma_phieu="PX-TEST-005",
            loai_xuat="BAN_TRU_LUONG",
            nhan_vien_nhan=self.user.nhan_vien,
            ghi_chu="Ledger unique",
        )
        detail = ChiTietPhieuXuat.objects.create(
            phieu_xuat=phieu,
            vat_tu=self.vat_tu,
            so_luong=1,
        )
        InventoryLedgerEntry.objects.create(
            phieu_xuat=phieu,
            chi_tiet_phieu_xuat=detail,
            vat_tu=self.vat_tu,
            document_type=InventoryLedgerEntry.DocumentType.ISSUE,
            movement_type=InventoryLedgerEntry.MovementType.POSTING,
            direction=InventoryLedgerEntry.Direction.OUT,
            quantity_delta=-1,
            stock_before=10,
            stock_after=9,
            reason="Posting",
        )

        duplicate = InventoryLedgerEntry(
            phieu_xuat=phieu,
            chi_tiet_phieu_xuat=detail,
            vat_tu=self.vat_tu,
            document_type=InventoryLedgerEntry.DocumentType.ISSUE,
            movement_type=InventoryLedgerEntry.MovementType.POSTING,
            direction=InventoryLedgerEntry.Direction.OUT,
            quantity_delta=-1,
            stock_before=10,
            stock_after=9,
            reason="Posting duplicate",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_stock_report_view_filters_inventory_by_query(self):
        request = self.request_factory.get(
            "/inventory/bao-cao-ton/",
            {"q": "Motorola"},
        )
        request.user = self.user

        response = bao_cao_ton_kho(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bo dam Motorola")

    def test_inventory_cache_invalidation_uses_versioned_keys(self):
        org_id = settings.SCMD_ORGANIZATION_ID
        dashboard_key = build_dashboard_cache_key(org_id, self.user.id)
        category_key = build_category_cache_key(org_id, self.user.id)
        cache.set(dashboard_key, {"cached": True}, 60)
        cache.set(category_key, ["cached"], 60)

        invalidate_inventory_cache()

        new_dashboard_key = build_dashboard_cache_key(org_id, self.user.id)
        new_category_key = build_category_cache_key(org_id, self.user.id)
        self.assertNotEqual(dashboard_key, new_dashboard_key)
        self.assertNotEqual(category_key, new_category_key)
        self.assertIsNone(cache.get(new_dashboard_key))
        self.assertIsNone(cache.get(new_category_key))
=======
# file: inventory/tests.py
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth.models import User
from .models import VatTu, LoaiVatTu, PhieuXuat, NhaCungCap
from .views import bao_cao_ton_kho_view

class InventoryModelTest(TestCase):
    def setUp(self):
        self.loai = LoaiVatTu.objects.create(ten_loai="Công cụ hỗ trợ")
        self.ncc = NhaCungCap.objects.create(ten_nha_cung_cap="Cty ABC")
        self.vat_tu = VatTu.objects.create(
            ten_vat_tu="Bộ đàm Motorola",
            loai=self.loai,
            don_vi_tinh="Cái",
            so_luong_ton=10,
            dinh_muc_toi_thieu=2
        )
        self.user = User.objects.create_user('kho_user', 'kho@test.com', 'password')

    def test_phieu_xuat_code_generation(self):
        """Test sinh mã phiếu xuất tự động PXK-YYYYMMDD-001"""
        phieu = PhieuXuat.objects.create(nguoi_xuat=self.user, ghi_chu="Test xuất")
        today_str = timezone.now().strftime('%Y%m%d')
        expected_code = f"PXK-{today_str}-001"
        self.assertEqual(phieu.so_phieu, expected_code)

        # Tạo phiếu thứ 2 xem có tăng số không
        phieu2 = PhieuXuat.objects.create(nguoi_xuat=self.user)
        expected_code_2 = f"PXK-{today_str}-002"
        self.assertEqual(phieu2.so_phieu, expected_code_2)

    def test_search_view(self):
        """Test view tìm kiếm tồn kho (bao gồm cả HTMX request)"""
        factory = RequestFactory()
        
        # 1. Test tìm kiếm bình thường
        request = factory.get('/inventory/bao-cao-ton-kho/', {'q': 'Motorola'})
        request.user = self.user
        response = bao_cao_ton_kho_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bộ đàm Motorola")

        # 2. Test tìm kiếm không có kết quả
        request = factory.get('/inventory/bao-cao-ton-kho/', {'q': 'Iphone'})
        request.user = self.user
        response = bao_cao_ton_kho_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Bộ đàm Motorola")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
