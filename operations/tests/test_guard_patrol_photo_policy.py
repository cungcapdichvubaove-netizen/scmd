# -*- coding: utf-8 -*-
"""Mobile photo policy regression tests for operations-owned guard patrol."""

import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from inspection.models import GhiNhanTuanTra
from operations.application.guard_patrol_use_cases import (
    ListGuardPatrolTasksUseCase,
    RecordGuardPatrolCheckpointUseCase,
    StartGuardPatrolSessionUseCase,
)
from operations.tests.test_guard_patrol_domain import GuardPatrolDomainFixture


class GuardPatrolPhotoPolicyTest(GuardPatrolDomainFixture):
    def test_missing_photo_when_schedule_requires_photo_is_rejected(self):
        schedule = self._create_photo_required_schedule()
        task = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)["nhiem_vu_tuan_tra"][0]
        session = StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)

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
        self.assertEqual(schedule.pk, session.lich_tuan_tra_van_hanh_id)

    def test_no_photo_when_not_required_still_records_checkpoint(self):
        self._create_photo_optional_schedule()
        task = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)["nhiem_vu_tuan_tra"][0]
        session = StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)

        ok, message, payload = RecordGuardPatrolCheckpointUseCase.execute(
            self.guard,
            session.pk,
            self.point.ma_qr,
            "10.0",
            "106.0",
            hinh_anh_xac_thuc=None,
        )

        self.assertTrue(ok)
        evidence = GhiNhanTuanTra.objects.get(luot_tuan_tra=session, diem_tuan_tra=self.point)
        self.assertFalse(bool(evidence.hinh_anh_xac_thuc))

    def test_uploaded_photo_when_required_records_checkpoint_via_mobile_view(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self._create_photo_required_schedule()
                task = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)["nhiem_vu_tuan_tra"][0]
                session = StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)
                self.client.login(username="guard-patrol-domain", password="password")
                photo = SimpleUploadedFile(
                    "checkpoint.jpg",
                    b"fake-jpeg-content",
                    content_type="image/jpeg",
                )

                response = self.client.post(
                    reverse("operations:xu_ly_quet_qr"),
                    {
                        "luot_tuan_tra_id": session.pk,
                        "qr_code": self.point.ma_qr,
                        "lat": "10.0",
                        "lng": "106.0",
                        "hinh_anh_xac_thuc": photo,
                    },
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertTrue(payload["success"], payload)
                evidence = GhiNhanTuanTra.objects.get(luot_tuan_tra=session, diem_tuan_tra=self.point)
                self.assertTrue(bool(evidence.hinh_anh_xac_thuc))
                self.assertTrue(Path(evidence.hinh_anh_xac_thuc.path).exists())

    def _create_photo_required_schedule(self):
        return self._create_schedule(require_gps=False, require_photo=True)

    def _create_photo_optional_schedule(self):
        return self._create_schedule(require_gps=False, require_photo=False)
