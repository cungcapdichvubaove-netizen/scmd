# -*- coding: utf-8 -*-
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from clients.models import HopDong, MucTieu
from inspection.application.patrol_use_cases import RecordPatrolCheckpointUseCase
from inspection.models import DiemTuanTra, LoaiTuanTra, LuotTuanTra, GhiNhanTuanTra
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from main.models import AuditLog

ORG_ID = UUID("00000000-0000-0000-0000-000000000812")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class PatrolGpsPolicyTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="patrol-gps")
        self.staff = self.user.nhan_vien
        self.staff.ma_nhan_vien = "NV-PATROL-GPS"
        self.staff.ho_ten = "Nhân viên tuần tra GPS"
        self.staff.tenant_id = ORG_ID
        self.staff.save()
        today = timezone.localdate()
        self.contract = HopDong.objects.create(
            so_hop_dong="HD-PATROL-GPS",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=0,
        )
        self.site = MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu="Site GPS", dia_chi="GPS")
        self.post = ViTriChot.objects.create(
            tenant_id=ORG_ID,
            muc_tieu=self.site,
            ten_vi_tri="Chốt GPS",
        )
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca GPS",
            gio_bat_dau="00:00",
            gio_ket_thuc="23:59",
        )
        self.shift = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.staff,
            vi_tri_chot=self.post,
            ca_lam_viec=self.shift_type,
            ngay_truc=today,
        )
        self.route = LoaiTuanTra.objects.create(
            tenant_id=ORG_ID,
            muc_tieu=self.site,
            ten_loai="Tuyến bắt buộc GPS",
            yeu_cau_gps=True,
        )
        self.point = DiemTuanTra.objects.create(
            tenant_id=ORG_ID,
            loai_tuan_tra=self.route,
            ten_diem="Điểm GPS",
            ma_qr="QR-GPS-001",
            vi_do=10.0,
            kinh_do=106.0,
        )
        self.session = LuotTuanTra.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.staff,
            loai_tuan_tra=self.route,
            trang_thai="DANG_DI",
        )

    def test_required_gps_route_rejects_missing_gps_without_creating_evidence(self):
        ok, message, payload = RecordPatrolCheckpointUseCase.execute(
            self.staff,
            self.session.pk,
            self.point.ma_qr,
            None,
            None,
        )

        self.assertFalse(ok)
        self.assertEqual(payload["error_code"], "MISSING_REQUIRED_GPS")
        self.assertFalse(GhiNhanTuanTra.objects.filter(luot_tuan_tra=self.session, diem_tuan_tra=self.point).exists())
        self.assertTrue(AuditLog.objects.filter(model_name="GhiNhanTuanTra", changes__reason="MISSING_REQUIRED_GPS").exists())

    def test_required_gps_accepts_zero_coordinates_as_present(self):
        self.route.yeu_cau_gps = True
        self.route.save(update_fields=["yeu_cau_gps"])
        self.point.vi_do = 0
        self.point.kinh_do = 0
        self.point.save(update_fields=["vi_do", "kinh_do"])

        ok, message, payload = RecordPatrolCheckpointUseCase.execute(
            nhan_vien=self.staff,
            luot_id=self.session.pk,
            ma_qr=self.point.ma_qr,
            lat_req=0.0,
            lng_req=0.0,
        )

        self.assertTrue(ok)
        self.assertIn("Thành công", message)
        self.assertEqual(payload["ten_diem"], self.point.ten_diem)
