# -*- coding: utf-8 -*-
"""
SCMD Pro - Patrol Use Case Regression Tests
-------------------------------------------
Kiểm thử P1: Không cho nhân viên bắt đầu tuyến tuần tra khác khi còn lượt
DANG_DI chưa hoàn thành, tránh audit sai tuyến và lẫn dữ liệu bằng chứng.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from clients.models import HopDong, MucTieu
from inspection.application.patrol_use_cases import StartPatrolSessionUseCase
from inspection.models import LoaiTuanTra, LuotTuanTra
from main.models import AuditLog
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import NhanVien


class StartPatrolSessionUseCaseRegressionTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-PATROL-REGRESSION",
            tenant_id=self.tenant_id,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Mục tiêu tuần tra",
            tenant_id=self.tenant_id,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Chốt tuần tra",
            tenant_id=self.tenant_id,
        )
        self.ca = CaLamViec.objects.create(
            ten_ca="Ca tuần tra",
            gio_bat_dau="08:00",
            gio_ket_thuc="17:00",
            tenant_id=self.tenant_id,
        )
        self.nhan_vien = NhanVien.objects.create(
            ho_ten="Nhân viên tuần tra",
            ma_nhan_vien="NV-PATROL-01",
            tenant_id=self.tenant_id,
        )
        PhanCongCaTruc.objects.create(
            nhan_vien=self.nhan_vien,
            vi_tri_chot=self.vi_tri,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.localdate(),
            tenant_id=self.tenant_id,
        )
        self.tuyen_a = LoaiTuanTra.objects.create(
            muc_tieu=self.muc_tieu,
            ten_loai="Tuyến A",
        )
        self.tuyen_b = LoaiTuanTra.objects.create(
            muc_tieu=self.muc_tieu,
            ten_loai="Tuyến B",
        )

    def test_starting_different_route_is_blocked_when_active_session_exists(self):
        active = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen_a,
            trang_thai="DANG_DI",
        )

        with self.assertRaises(ValidationError):
            StartPatrolSessionUseCase.execute(self.nhan_vien, self.tuyen_b.pk)

        active.refresh_from_db()
        self.assertEqual(active.loai_tuan_tra_id, self.tuyen_a.pk)
        self.assertEqual(active.trang_thai, "DANG_DI")
        self.assertEqual(
            LuotTuanTra.objects.filter(nhan_vien=self.nhan_vien, trang_thai="DANG_DI").count(),
            1,
        )
        self.assertFalse(
            AuditLog.objects.filter(
                model_name="LuotTuanTra",
                object_id=str(active.pk),
            ).exists()
        )

    def test_starting_same_route_continues_existing_active_session(self):
        active = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen_a,
            trang_thai="DANG_DI",
        )

        luot = StartPatrolSessionUseCase.execute(self.nhan_vien, self.tuyen_a.pk)

        self.assertEqual(luot.pk, active.pk)
        self.assertEqual(
            LuotTuanTra.objects.filter(nhan_vien=self.nhan_vien, trang_thai="DANG_DI").count(),
            1,
        )
        audit = AuditLog.objects.get(
            model_name="LuotTuanTra",
            object_id=str(active.pk),
        )
        self.assertEqual(audit.changes["requested_loai_tuan_tra_id"], self.tuyen_a.pk)
        self.assertEqual(audit.changes["active_loai_tuan_tra_id"], self.tuyen_a.pk)

from django.db import IntegrityError
from inspection.application.patrol_use_cases import CompletePatrolSessionUseCase, RecordPatrolCheckpointUseCase
from inspection.models import DiemTuanTra, GhiNhanTuanTra


class PatrolEvidenceIntegrityRegressionTest(StartPatrolSessionUseCaseRegressionTest):
    def setUp(self):
        super().setUp()
        self.diem = DiemTuanTra.objects.create(
            loai_tuan_tra=self.tuyen_a,
            ten_diem="Checkpoint A1",
            ma_qr="QR-A1",
            vi_do=10.0,
            kinh_do=106.0,
            ban_kinh_cho_phep=100,
        )
        self.luot = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen_a,
            trang_thai="DANG_DI",
        )

    def test_checkpoint_duplicate_is_rejected_by_database_invariant(self):
        GhiNhanTuanTra.objects.create(
            luot_tuan_tra=self.luot,
            diem_tuan_tra=self.diem,
            ket_qua="HOP_LE",
        )
        with self.assertRaises(IntegrityError):
            GhiNhanTuanTra.objects.create(
                luot_tuan_tra=self.luot,
                diem_tuan_tra=self.diem,
                ket_qua="HOP_LE",
            )

    def test_record_checkpoint_duplicate_returns_clear_business_message(self):
        GhiNhanTuanTra.objects.create(
            luot_tuan_tra=self.luot,
            diem_tuan_tra=self.diem,
            ket_qua="HOP_LE",
        )
        ok, message, payload = RecordPatrolCheckpointUseCase.execute(
            self.nhan_vien,
            self.luot.pk,
            self.diem.ma_qr,
            "10.0",
            "106.0",
        )
        self.assertFalse(ok)
        self.assertEqual(message, "Đã quét điểm này rồi!")
        self.assertEqual(payload, {})

    def test_complete_patrol_is_idempotent_without_duplicate_audit(self):
        GhiNhanTuanTra.objects.create(
            luot_tuan_tra=self.luot,
            diem_tuan_tra=self.diem,
            ket_qua="HOP_LE",
        )
        first = CompletePatrolSessionUseCase.execute(self.nhan_vien, self.luot.pk)
        self.assertEqual(first.trang_thai, "HOAN_THANH")
        audit_count = AuditLog.objects.filter(
            model_name="LuotTuanTra",
            object_id=str(self.luot.pk),
            changes__trang_thai="HOAN_THANH",
        ).count()
        self.assertEqual(audit_count, 1)

        second = CompletePatrolSessionUseCase.execute(self.nhan_vien, self.luot.pk)
        self.assertEqual(second.pk, self.luot.pk)
        self.assertEqual(
            AuditLog.objects.filter(
                model_name="LuotTuanTra",
                object_id=str(self.luot.pk),
                changes__trang_thai="HOAN_THANH",
            ).count(),
            1,
        )

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse
from rolepermissions.roles import assign_role


class PatrolMobileViewValidationRegressionTest(TestCase):
    """View-level regression tests for patrol business ValidationError handling."""

    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_user(username="patrol_view_guard", password="password")
        assign_role(self.user, "nhan_vien_bao_ve")
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Guard Patrol View"
        self.nhan_vien.tenant_id = self.tenant_id
        self.nhan_vien.save()

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-PATROL-VIEW",
            tenant_id=self.tenant_id,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Mục tiêu view tuần tra",
            tenant_id=self.tenant_id,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Chốt view tuần tra",
            tenant_id=self.tenant_id,
        )
        self.ca = CaLamViec.objects.create(
            ten_ca="Ca view tuần tra",
            gio_bat_dau="08:00",
            gio_ket_thuc="17:00",
            tenant_id=self.tenant_id,
        )
        PhanCongCaTruc.objects.create(
            nhan_vien=self.nhan_vien,
            vi_tri_chot=self.vi_tri,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.localdate(),
            tenant_id=self.tenant_id,
        )
        self.tuyen_a = LoaiTuanTra.objects.create(
            muc_tieu=self.muc_tieu,
            ten_loai="Tuyến view A",
        )
        self.tuyen_b = LoaiTuanTra.objects.create(
            muc_tieu=self.muc_tieu,
            ten_loai="Tuyến view B",
        )
        self.client.login(username="patrol_view_guard", password="password")

    def test_starting_different_route_redirects_with_business_error(self):
        active = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen_a,
            trang_thai="DANG_DI",
        )

        response = self.client.get(reverse("inspection:bat_dau_tuan_tra", kwargs={"loai_id": self.tuyen_b.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("operations:mobile_tuan_tra_list"))
        active.refresh_from_db()
        self.assertEqual(active.trang_thai, "DANG_DI")
        self.assertEqual(active.loai_tuan_tra_id, self.tuyen_a.pk)
        self.assertEqual(
            LuotTuanTra.objects.filter(nhan_vien=self.nhan_vien, trang_thai="DANG_DI").count(),
            1,
        )
        self.assertTrue(any("lượt tuần tra chưa hoàn thành" in str(message) for message in get_messages(response.wsgi_request)))

    def test_completing_abandoned_session_redirects_with_business_error(self):
        abandoned = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen_a,
            trang_thai="BO_DO",
        )

        response = self.client.post(reverse("inspection:hoan_thanh_tuan_tra", kwargs={"luot_id": abandoned.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("operations:mobile_tuan_tra_list"))
        abandoned.refresh_from_db()
        self.assertEqual(abandoned.trang_thai, "BO_DO")
        self.assertFalse(
            AuditLog.objects.filter(
                model_name="LuotTuanTra",
                object_id=str(abandoned.pk),
                changes__trang_thai="HOAN_THANH",
            ).exists()
        )
        self.assertTrue(any("Chỉ có thể hoàn thành" in str(message) for message in get_messages(response.wsgi_request)))


class PatrolMobilePermissionBoundaryRegressionTest(TestCase):
    """RBAC boundary tests for mobile patrol/inspection endpoints."""

    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_user(username="patrol_no_role", password="password")
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Guard Without Patrol Permission"
        self.nhan_vien.tenant_id = self.tenant_id
        self.nhan_vien.save()

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-PATROL-PERM",
            tenant_id=self.tenant_id,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Mục tiêu permission tuần tra",
            tenant_id=self.tenant_id,
        )
        self.tuyen = LoaiTuanTra.objects.create(
            muc_tieu=self.muc_tieu,
            ten_loai="Tuyến permission",
        )
        self.luot = LuotTuanTra.objects.create(
            nhan_vien=self.nhan_vien,
            loai_tuan_tra=self.tuyen,
            trang_thai="DANG_DI",
        )
        self.client.login(username="patrol_no_role", password="password")

    def test_record_checkpoint_requires_patrol_permission(self):
        response = self.client.post(reverse("inspection:ghi_nhan_diem"), data={
            "luot_tuan_tra_id": self.luot.pk,
            "qr_code": "ANY",
        })
        self.assertEqual(response.status_code, 403)

    def test_complete_patrol_requires_patrol_permission(self):
        response = self.client.post(reverse("inspection:hoan_thanh_tuan_tra", kwargs={"luot_id": self.luot.pk}))
        self.assertEqual(response.status_code, 403)

    def test_mobile_violation_form_requires_violation_permission(self):
        response = self.client.get(reverse("inspection:mobile_lap_bien_ban"))
        self.assertEqual(response.status_code, 403)
