# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from clients.models import HopDong, MucTieu
from main.models import AuditLog
from operations.application.incident_reporting_use_cases import ReportIncidentUseCase
from operations.models import BaoCaoSuCo, CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot


class IncidentReportingContractTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="incident-field-user",
            email="incident-field@example.com",
            password="password",
        )
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Bảo vệ hiện trường"
        self.nhan_vien.ma_nhan_vien = "NV_INCIDENT_001"
        self.nhan_vien.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.nhan_vien.save()

        today = timezone.localdate()
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-INCIDENT-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Mục tiêu báo sự cố",
            dia_chi="Địa chỉ mục tiêu",
            sdt_lien_he="0900000000",
        )
        self.vi_tri = ViTriChot.objects.create(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Chốt chính",
        )
        self.ca_lam = CaLamViec.objects.create(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            ten_ca="Ca ngày",
            gio_bat_dau="06:00",
            gio_ket_thuc="18:00",
        )
        self.phan_cong = PhanCongCaTruc.objects.create(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            nhan_vien=self.nhan_vien,
            vi_tri_chot=self.vi_tri,
            ca_lam_viec=self.ca_lam,
            ngay_truc=today,
        )
        self.client = Client()
        self.client.login(username="incident-field-user", password="password")
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)

    def _create_active_attendance(self):
        return ChamCong.objects.create(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
        )

    def test_report_incident_use_case_rejects_when_no_active_shift(self):
        with self.assertRaisesMessage(
            ValidationError,
            ReportIncidentUseCase.ACTIVE_SHIFT_REQUIRED_MESSAGE,
        ):
            ReportIncidentUseCase.execute(
                reporter_nv=self.nhan_vien,
                form_data={"tieu_de": "Sự cố không ca"},
                files_data={},
            )

        self.assertEqual(BaoCaoSuCo.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(model_name="BaoCaoSuCo").count(), 0)

    def test_report_incident_use_case_creates_incident_with_active_shift_site(self):
        self._create_active_attendance()

        incident = ReportIncidentUseCase.execute(
            reporter_nv=self.nhan_vien,
            form_data={"tieu_de": "Sự cố ca trực", "mo_ta_chi_tiet": "Mô tả"},
            files_data={},
        )

        self.assertEqual(incident.nhan_vien_bao_cao, self.nhan_vien)
        self.assertEqual(incident.ca_truc, self.phan_cong)
        self.assertEqual(incident.muc_tieu, self.muc_tieu)
        self.assertEqual(AuditLog.objects.filter(model_name="BaoCaoSuCo", object_id=str(incident.pk)).count(), 1)

    def test_mobile_incident_view_shows_validation_error_when_no_active_shift(self):
        response = self.client.post(
            reverse("operations:bao_cao_su_co"),
            {"tieu_de": "Sự cố mobile web", "mo_ta_chi_tiet": "Mô tả"},
            follow=True,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message_texts = [str(message) for message in messages.get_messages(response.wsgi_request)]
        self.assertIn(ReportIncidentUseCase.ACTIVE_SHIFT_REQUIRED_MESSAGE, message_texts)
        self.assertEqual(BaoCaoSuCo.objects.count(), 0)

    def test_mobile_incident_api_rejects_when_no_active_shift(self):
        response = self.api_client.post(
            reverse("operations:mobile-su-co-list"),
            {"tieu_de": "Sự cố API không ca", "mo_ta_chi_tiet": "Mô tả"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "INCIDENT_REPORT_INVALID")
        self.assertEqual(BaoCaoSuCo.objects.count(), 0)

    def test_mobile_incident_api_binds_to_active_shift_and_site(self):
        self._create_active_attendance()

        response = self.api_client.post(
            reverse("operations:mobile-su-co-list"),
            {"tieu_de": "Sự cố API hợp lệ", "mo_ta_chi_tiet": "Mô tả"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        incident = BaoCaoSuCo.objects.get()
        self.assertEqual(incident.nhan_vien_bao_cao, self.nhan_vien)
        self.assertEqual(incident.ca_truc, self.phan_cong)
        self.assertEqual(incident.muc_tieu, self.muc_tieu)
