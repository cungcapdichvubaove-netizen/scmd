# -*- coding: utf-8 -*-
"""Domain correction tests for guard patrol ownership.

Guard Patrol is owned by operations. The legacy inspection persistence tables are
used only as a transition storage layer until a controlled migration can rename
or split them safely.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rolepermissions.roles import assign_role

from clients.models import HopDong, MucTieu
from inspection.models import DiemTuanTra, GhiNhanTuanTra, LoaiTuanTra, LuotTuanTra
from main.models import AuditLog
from operations.application.guard_patrol_use_cases import (
    CompleteGuardPatrolSessionUseCase,
    GuardPatrolComplianceUseCase,
    ListGuardPatrolTasksUseCase,
    MaterializeGuardPatrolTasksUseCase,
    RecordGuardPatrolCheckpointUseCase,
    StartGuardPatrolSessionUseCase,
)
from operations.models import CaLamViec, LichTuanTraVanHanh, NhiemVuTuanTraCa, PhanCongCaTruc, ViTriChot


class GuardPatrolDomainFixture(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        User = get_user_model()
        self.guard_user = User.objects.create_user(username="guard-patrol-domain", password="password")
        assign_role(self.guard_user, "nhan_vien_bao_ve")
        self.guard = self.guard_user.nhan_vien
        self.guard.ho_ten = "Guard Patrol Domain"
        self.guard.ma_nhan_vien = "NV-GP-DOMAIN"
        self.guard.tenant_id = self.tenant_id
        self.guard.save()

        self.other_user = User.objects.create_user(username="other-guard-patrol-domain", password="password")
        assign_role(self.other_user, "nhan_vien_bao_ve")
        self.other_guard = self.other_user.nhan_vien
        self.other_guard.ho_ten = "Other Guard Patrol Domain"
        self.other_guard.ma_nhan_vien = "NV-GP-OTHER"
        self.other_guard.tenant_id = self.tenant_id
        self.other_guard.save()

        self.contract = HopDong.objects.create(so_hop_dong="HD-GP-DOMAIN", tenant_id=self.tenant_id)
        self.site = MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu="Site Guard Patrol", tenant_id=self.tenant_id)
        self.other_site = MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu="Other Site Guard Patrol", tenant_id=self.tenant_id)
        self.post = ViTriChot.objects.create(muc_tieu=self.site, ten_vi_tri="Post Guard Patrol", tenant_id=self.tenant_id)
        self.other_post = ViTriChot.objects.create(muc_tieu=self.other_site, ten_vi_tri="Other Post Guard Patrol", tenant_id=self.tenant_id)
        self.shift_type = CaLamViec.objects.create(
            ten_ca="Ca guard patrol",
            gio_bat_dau="00:00",
            gio_ket_thuc="23:59",
            tenant_id=self.tenant_id,
        )
        self.shift = PhanCongCaTruc.objects.create(
            nhan_vien=self.guard,
            vi_tri_chot=self.post,
            ca_lam_viec=self.shift_type,
            ngay_truc=timezone.localdate(),
            tenant_id=self.tenant_id,
        )
        self.other_shift = PhanCongCaTruc.objects.create(
            nhan_vien=self.other_guard,
            vi_tri_chot=self.other_post,
            ca_lam_viec=self.shift_type,
            ngay_truc=timezone.localdate(),
            tenant_id=self.tenant_id,
        )
        self.route = LoaiTuanTra.objects.create(muc_tieu=self.site, ten_loai="Route Guard Patrol", tenant_id=self.tenant_id)
        self.other_route = LoaiTuanTra.objects.create(muc_tieu=self.other_site, ten_loai="Other Route Guard Patrol", tenant_id=self.tenant_id)
        self.point = DiemTuanTra.objects.create(
            loai_tuan_tra=self.route,
            ten_diem="Checkpoint Guard Patrol",
            ma_qr="QR-GP-DOMAIN-1",
            vi_do=10.0,
            kinh_do=106.0,
            ban_kinh_cho_phep=100,
            tenant_id=self.tenant_id,
        )
        self.second_point = DiemTuanTra.objects.create(
            loai_tuan_tra=self.route,
            ten_diem="Checkpoint Guard Patrol 2",
            ma_qr="QR-GP-DOMAIN-2",
            vi_do=10.0,
            kinh_do=106.0,
            ban_kinh_cho_phep=100,
            tenant_id=self.tenant_id,
        )
        self.other_point = DiemTuanTra.objects.create(
            loai_tuan_tra=self.other_route,
            ten_diem="Other Checkpoint Guard Patrol",
            ma_qr="QR-GP-OTHER-1",
            vi_do=10.0,
            kinh_do=106.0,
            ban_kinh_cho_phep=100,
            tenant_id=self.tenant_id,
        )

    def _create_schedule(self, *, frequency=1, require_gps=True, require_photo=False):
        return LichTuanTraVanHanh.objects.create(
            muc_tieu=self.site,
            vi_tri_chot=self.post,
            ca_lam_viec=self.shift_type,
            tuyen_tuan_tra=self.route,
            tan_suat_luot_bat_buoc=frequency,
            khung_gio_bat_dau="00:00",
            khung_gio_ket_thuc="23:59",
            grace_minutes=15,
            yeu_cau_gps=require_gps,
            yeu_cau_anh=require_photo,
            tenant_id=self.tenant_id,
        )


class GuardPatrolPermissionTest(GuardPatrolDomainFixture):
    def test_guard_only_sees_routes_for_current_shift_site(self):
        context = ListGuardPatrolTasksUseCase.execute(self.guard)

        self.assertEqual(context["ca_hien_tai"], self.shift)
        self.assertIn(self.route, context["lo_trinhs"])
        self.assertNotIn(self.other_route, context["lo_trinhs"])

    def test_guard_without_shift_cannot_start_patrol(self):
        PhanCongCaTruc.objects.filter(pk=self.shift.pk).delete()

        with self.assertRaises(PermissionDenied):
            StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)

    def test_guard_cannot_start_route_for_another_site(self):
        with self.assertRaises(PermissionDenied):
            StartGuardPatrolSessionUseCase.execute(self.guard, self.other_route.pk)

    def test_mobile_dashboard_links_to_operations_patrol_route(self):
        dashboard_template = open("operations/templates/operations/mobile/dashboard.html", encoding="utf-8").read()

        self.assertIn("operations:mobile_tuan_tra_list", dashboard_template)
        self.assertNotIn("inspection" + ":mobile_tuan_tra_list", dashboard_template)


class GuardPatrolIntegrityTest(GuardPatrolDomainFixture):
    def test_start_patrol_audits_shift_context(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)

        audit = AuditLog.objects.get(model_name="LuotTuanTra", object_id=str(session.pk))
        self.assertEqual(audit.module, "operations")
        self.assertEqual(session.phan_cong_ca_truc_id, self.shift.pk)
        self.assertEqual(session.trang_thai_doi_soat, "IN_PROGRESS")
        self.assertEqual(session.so_diem_bat_buoc, 2)
        self.assertEqual(audit.changes["domain_owner"], "operations.guard_patrol")
        self.assertEqual(audit.changes["phan_cong_ca_truc_id"], self.shift.pk)

    def test_qr_checkpoint_from_other_target_is_rejected(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)

        ok, message, payload = RecordGuardPatrolCheckpointUseCase.execute(
            self.guard,
            session.pk,
            self.other_point.ma_qr,
            "10.0",
            "106.0",
        )

        self.assertFalse(ok)
        self.assertEqual(payload["error_code"], "CHECKPOINT_OUT_OF_ROUTE")
        self.assertIn("không thuộc tuyến", message)

    def test_missing_required_checkpoint_blocks_valid_completion(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.point.ma_qr, "10.0", "106.0")

        with self.assertRaises(ValidationError):
            CompleteGuardPatrolSessionUseCase.execute(self.guard, session.pk)

        session.refresh_from_db()
        self.assertEqual(session.trang_thai, "DANG_DI")
        self.assertEqual(session.trang_thai_doi_soat, "IN_PROGRESS")
        self.assertEqual(session.so_diem_da_quet, 1)

    def test_all_required_checkpoints_complete_valid(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.point.ma_qr, "10.0", "106.0")
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.second_point.ma_qr, "10.0", "106.0")

        completed = CompleteGuardPatrolSessionUseCase.execute(self.guard, session.pk)

        self.assertEqual(completed.trang_thai, "HOAN_THANH")
        self.assertEqual(completed.phan_cong_ca_truc_id, self.shift.pk)
        self.assertEqual(completed.trang_thai_doi_soat, "COMPLETED_VALID")
        self.assertEqual(completed.so_diem_bat_buoc, 2)
        self.assertEqual(completed.so_diem_da_quet, 2)
        audit = AuditLog.objects.filter(
            model_name="LuotTuanTra",
            object_id=str(session.pk),
            changes__trang_thai="HOAN_THANH",
        ).latest("timestamp")
        self.assertEqual(audit.changes["completion_quality"], "COMPLETED_VALID")

    @override_settings(GUARD_PATROL_REQUIRE_PHOTO=True)
    def test_required_photo_policy_rejects_missing_photo(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)

        ok, message, payload = RecordGuardPatrolCheckpointUseCase.execute(
            self.guard,
            session.pk,
            self.point.ma_qr,
            "10.0",
            "106.0",
            hinh_anh_xac_thuc=None,
        )

        self.assertFalse(ok)
        self.assertEqual(payload["error_code"], "MISSING_REQUIRED_PHOTO")
        self.assertFalse(GhiNhanTuanTra.objects.filter(luot_tuan_tra=session).exists())

    def test_all_required_checkpoints_complete_with_warnings_is_not_counted_as_valid(self):
        session = StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.point.ma_qr, "10.0", "106.0")
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.second_point.ma_qr, None, None)

        completed = CompleteGuardPatrolSessionUseCase.execute(self.guard, session.pk)

        self.assertEqual(completed.trang_thai, "HOAN_THANH")
        self.assertEqual(completed.trang_thai_doi_soat, "COMPLETED_WITH_WARNINGS")
        self.assertEqual(completed.so_diem_canh_bao, 1)



class RouteCompatibilityTest(GuardPatrolDomainFixture):
    def test_operations_patrol_routes_are_registered(self):
        self.client.login(username="guard-patrol-domain", password="password")

        response = self.client.get(reverse("operations:mobile_tuan_tra_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tuần tra mục tiêu")

    def test_legacy_inspection_route_remains_available_during_transition(self):
        self.client.login(username="guard-patrol-domain", password="password")

        response = self.client.get(reverse("inspection" + ":mobile_tuan_tra_list"))

        self.assertIn(response.status_code, {200, 302})

    def test_new_operations_url_paths_match_canonical_contract(self):
        self.assertEqual(reverse("operations:mobile_tuan_tra_list"), "/operations/mobile/tuan-tra/")
        self.assertEqual(
            reverse("operations:bat_dau_tuan_tra", kwargs={"loai_id": self.route.pk}),
            f"/operations/mobile/tuan-tra/bat-dau/{self.route.pk}/",
        )
        self.assertEqual(reverse("operations:xu_ly_quet_qr"), "/operations/mobile/tuan-tra/ghi-nhan/quet-qr/")


class GuardPatrolSchedulePhase2Test(GuardPatrolDomainFixture):
    def _create_schedule(self, *, frequency=1, require_gps=True, require_photo=False):
        return LichTuanTraVanHanh.objects.create(
            muc_tieu=self.site,
            vi_tri_chot=self.post,
            ca_lam_viec=self.shift_type,
            tuyen_tuan_tra=self.route,
            tan_suat_luot_bat_buoc=frequency,
            khung_gio_bat_dau="00:00",
            khung_gio_ket_thuc="23:59",
            grace_minutes=15,
            yeu_cau_gps=require_gps,
            yeu_cau_anh=require_photo,
            tenant_id=self.tenant_id,
        )

    def test_list_materializes_patrol_tasks_from_operations_schedule(self):
        schedule = self._create_schedule(frequency=2)

        context = ListGuardPatrolTasksUseCase.execute(self.guard)

        self.assertTrue(context["uses_operations_schedule"])
        self.assertEqual(len(context["nhiem_vu_tuan_tra"]), 2)
        self.assertEqual(context["lo_trinhs"], [])
        task = context["nhiem_vu_tuan_tra"][0]
        self.assertEqual(task.lich_tuan_tra_id, schedule.pk)
        self.assertEqual(task.phan_cong_ca_truc_id, self.shift.pk)
        self.assertEqual(task.tuyen_tuan_tra_id, self.route.pk)
        self.assertEqual(task.so_diem_bat_buoc, 2)
        self.assertEqual(task.trang_thai, NhiemVuTuanTraCa.TrangThai.PLANNED)

    def test_start_patrol_from_task_links_shift_schedule_and_task(self):
        self._create_schedule(frequency=1, require_gps=True, require_photo=True)
        task = ListGuardPatrolTasksUseCase.execute(self.guard)["nhiem_vu_tuan_tra"][0]

        session = StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)
        task.refresh_from_db()

        self.assertEqual(session.phan_cong_ca_truc_id, self.shift.pk)
        self.assertEqual(session.lich_tuan_tra_van_hanh_id, task.lich_tuan_tra_id)
        self.assertEqual(session.nhiem_vu_tuan_tra_ca_id, task.pk)
        self.assertEqual(task.trang_thai, NhiemVuTuanTraCa.TrangThai.IN_PROGRESS)
        self.assertEqual(task.luot_tuan_tra_id, session.pk)
        audit = AuditLog.objects.filter(model_name="LuotTuanTra", object_id=str(session.pk)).latest("timestamp")
        self.assertEqual(audit.changes["requested_type"], "operations.NhiemVuTuanTraCa")
        self.assertEqual(audit.changes["nhiem_vu_tuan_tra_ca_id"], task.pk)
        self.assertTrue(audit.changes["required_gps"])
        self.assertTrue(audit.changes["required_photo"])

    def test_complete_patrol_updates_shift_task_compliance_state(self):
        self._create_schedule(frequency=1)
        task = ListGuardPatrolTasksUseCase.execute(self.guard)["nhiem_vu_tuan_tra"][0]
        session = StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.point.ma_qr, "10.0", "106.0")
        RecordGuardPatrolCheckpointUseCase.execute(self.guard, session.pk, self.second_point.ma_qr, "10.0", "106.0")

        completed = CompleteGuardPatrolSessionUseCase.execute(self.guard, session.pk)
        task.refresh_from_db()

        self.assertEqual(completed.trang_thai_doi_soat, "COMPLETED_VALID")
        self.assertEqual(task.trang_thai, NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID)
        self.assertEqual(task.so_diem_da_quet, 2)
        self.assertEqual(task.so_diem_canh_bao, 0)

    def test_compliance_summary_reads_existing_tasks_only(self):
        self._create_schedule(frequency=2)
        MaterializeGuardPatrolTasksUseCase.execute_for_shift(shift=self.shift, actor=self.guard_user)

        summary = GuardPatrolComplianceUseCase.execute(tenant_id=self.tenant_id, target_date=timezone.localdate())

        self.assertEqual(summary["stats"]["total"], 2)
        self.assertEqual(summary["stats"]["planned"], 2)
        self.assertEqual(summary["stats"]["completed_valid"], 0)
        self.assertEqual(len(summary["tasks"]), 2)

    def test_compliance_summary_does_not_materialize_tasks_on_read(self):
        self._create_schedule(frequency=2)
        before_tasks = NhiemVuTuanTraCa.objects.count()
        before_audits = AuditLog.objects.count()

        summary = GuardPatrolComplianceUseCase.execute(tenant_id=self.tenant_id, target_date=timezone.localdate())

        self.assertEqual(summary["stats"]["total"], 0)
        self.assertEqual(NhiemVuTuanTraCa.objects.count(), before_tasks)
        self.assertEqual(AuditLog.objects.count(), before_audits)
