# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
Unit tests for dashboard use cases.
"""

import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role

from clients.models import HopDong, KhachHangTiemNang, MucTieu
from main.dashboard_router import DashboardRouter
from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from users.models import NhanVien


class TestGetOperationsDashboardUseCase(unittest.TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.target_date = date(2026, 5, 16)

    @patch("operations.application.dashboard_use_cases.GetOperationsDashboardUseCase._get_allowed_targets_queryset")
    @patch("operations.application.dashboard_use_cases.BaoCaoSuCo")
    @patch("operations.application.dashboard_use_cases.PhanCongCaTruc")
    @patch("operations.application.dashboard_use_cases.ChamCong")
    def test_execute_success_logic(
        self,
        mock_allowed_targets_qs,
        mock_cham_cong,
        mock_phan_cong,
        mock_bao_cao_su_co,
    ):
        """
        Kiểm tra logic tổng hợp dữ liệu dashboard mà không cần database.
        """
        mock_cc = MagicMock()
        mock_cc.location_check_in = Point(106.660172, 10.762622)
=======
Unit Tests for Dashboard Use Cases.
Compliance: Rule 10 of .cursorrules (No Database Context).
Version: v2.1.0-strict
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import date, datetime
from django.contrib.gis.geos import Point
from operations.dashboard_use_cases import GetWarRoomDashboardUseCase
from django.conf import settings
from django.contrib.auth.models import User, Group
from users.models import NhanVien
from clients.models import MucTieu, HopDong, KhachHangTiemNang

class TestGetWarRoomDashboardUseCase(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "00000000-0000-0000-0000-000000000001"
        self.target_date = date(2026, 5, 16)

    @patch('operations.application.dashboard_use_cases.BaoCaoSuCo')
    @patch('operations.application.dashboard_use_cases.PhanCongCaTruc')
    @patch('operations.application.dashboard_use_cases.ChamCong')
    def test_execute_success_logic(self, MockChamCong, MockPhanCong, MockBaoCaoSuCo):
        """
        Kiểm tra logic tổng hợp dữ liệu dashboard mà không cần database.
        Mục tiêu: Đảm bảo stats tính toán đúng và markers được format chính xác.
        """
        # 1. Giả lập dữ liệu cho ChamCong (Active Staff)
        mock_cc = MagicMock()
        mock_cc.location_check_in = Point(106.660172, 10.762622) # Sài Gòn
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        mock_cc.ca_truc.nhan_vien.id = 1
        mock_cc.ca_truc.nhan_vien.ho_ten = "Nguyễn Văn A"
        mock_cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu = "Mục tiêu Alpha"
        mock_cc.thoi_gian_check_in = datetime(2026, 5, 16, 6, 0)

<<<<<<< HEAD
        active_qs = (
            mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value
        )
        active_qs.__iter__.return_value = [mock_cc]

        total_qs = mock_phan_cong.objects.for_tenant.return_value.filter.return_value
        total_qs.count.return_value = 10

=======
        # Mock chaining cho active_ccs_qs
        # .for_tenant().filter().select_related()
        active_qs = MockChamCong.objects.for_tenant.return_value.filter.return_value.select_related.return_value
        active_qs.__iter__.return_value = [mock_cc]

        # 2. Giả lập dữ liệu cho PhanCongCaTruc (Total Shifts)
        total_qs = MockPhanCong.objects.for_tenant.return_value.filter.return_value
        total_qs.count.return_value = 10  # Giả sử có 10 ca trực

        # 3. Giả lập dữ liệu cho BaoCaoSuCo (Incidents)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        mock_incident = MagicMock()
        mock_incident.id = 101
        mock_incident.tieu_de = "Mất cắp vật tư"
        mock_incident.muc_do = "CAO"
        mock_incident.muc_tieu.vi_do = 10.762622
        mock_incident.muc_tieu.kinh_do = 106.660172
<<<<<<< HEAD
        mock_allowed_targets_qs.return_value = MagicMock()

        incident_qs = (
            mock_bao_cao_su_co.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value
        )
        incident_qs.__iter__.return_value = [mock_incident]

        last_qs = (
            mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value
        )
        last_qs.first.return_value = mock_cc

        user = SimpleNamespace(nhan_vien=SimpleNamespace())
        result = GetOperationsDashboardUseCase.execute(
            user=user,
            tenant_id=self.tenant_id,
            target_date=self.target_date,
        )

        self.assertEqual(result["stats"]["tong_ca"], 10)
        self.assertEqual(result["stats"]["da_checkin"], 1)
        self.assertEqual(result["stats"]["vang_mat"], 9)
        self.assertEqual(len(result["markers"]), 1)
        self.assertEqual(result["markers"][0]["name"], "Nguyễn Văn A")
        self.assertEqual(result["markers"][0]["lat"], 10.762622)
        self.assertEqual(result["markers"][0]["lng"], 106.660172)
        self.assertEqual(len(result["incidents"]), 1)
        self.assertEqual(result["incidents"][0]["title"], "Mất cắp vật tư")
        self.assertIsNotNone(result["last_activity"])
        self.assertEqual(result["last_activity"]["user"], "Nguyễn Văn A")
        self.assertEqual(result["last_activity"]["time"], "06:00")

    @patch("operations.application.dashboard_use_cases.GetOperationsDashboardUseCase._get_allowed_targets_queryset")
    @patch("operations.application.dashboard_use_cases.ChamCong")
    @patch("operations.application.dashboard_use_cases.PhanCongCaTruc")
    @patch("operations.application.dashboard_use_cases.BaoCaoSuCo")
    def test_execute_empty_data(
        self,
        mock_allowed_targets_qs,
        mock_bao_cao_su_co,
        mock_phan_cong,
        mock_cham_cong,
    ):
        """Kiểm tra trường hợp ngày không có dữ liệu ca trực."""
        mock_allowed_targets_qs.return_value = MagicMock()
        mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.__iter__.return_value = []
        mock_phan_cong.objects.for_tenant.return_value.filter.return_value.count.return_value = 0
        mock_bao_cao_su_co.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.__iter__.return_value = []
        mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = None

        user = SimpleNamespace(nhan_vien=SimpleNamespace())
        result = GetOperationsDashboardUseCase.execute(
            user=user,
            tenant_id=self.tenant_id,
            target_date=self.target_date,
        )

        self.assertEqual(result["stats"]["tong_ca"], 0)
        self.assertEqual(len(result["markers"]), 0)
        self.assertIsNone(result["last_activity"])

    @patch("operations.application.dashboard_use_cases.GetOperationsDashboardUseCase._get_allowed_targets_queryset")
    @patch("operations.application.dashboard_use_cases.BaoCaoSuCo")
    @patch("operations.application.dashboard_use_cases.PhanCongCaTruc")
    @patch("operations.application.dashboard_use_cases.ChamCong")
    def test_execute_allows_superuser_without_nhanvien_profile(
        self,
        mock_cham_cong,
        mock_phan_cong,
        mock_bao_cao_su_co,
        mock_allowed_targets_qs,
    ):
        mock_allowed_targets_qs.return_value = MagicMock()
        mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.__iter__.return_value = []
        mock_phan_cong.objects.for_tenant.return_value.filter.return_value.count.return_value = 0
        mock_bao_cao_su_co.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.__iter__.return_value = []
        mock_cham_cong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = None

        user = SimpleNamespace(is_superuser=True, is_staff=True)
        result = GetOperationsDashboardUseCase.execute(
            user=user,
            tenant_id=self.tenant_id,
            target_date=self.target_date,
        )

        self.assertIn("stats", result)
        self.assertTrue(result["diagnostic_mode"])
        self.assertEqual(result["stats"]["tong_ca"], 0)

    def test_execute_keeps_non_profile_non_admin_user_blocked(self):
        user = SimpleNamespace(is_superuser=False, is_staff=False)

        result = GetOperationsDashboardUseCase.execute(
            user=user,
            tenant_id=self.tenant_id,
            target_date=self.target_date,
        )

        self.assertEqual(result, {})


class DashboardAPIRouterPermissionContractTest(TestCase):
    """API permission must follow DashboardRouter SSOT, not ad-hoc Django Group fixtures."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("operations:api_dashboard_data")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID

        self.user_bgd = User.objects.create_user(username="bgd", password="password")
        assign_role(self.user_bgd, "ban_giam_doc")
        NhanVien.objects.update_or_create(
            user=self.user_bgd,
            defaults={"ho_ten": "Giám Đốc", "tenant_id": self.tenant_id},
        )

        self.user_qlv = User.objects.create_user(username="qlv", password="password")
        assign_role(self.user_qlv, "quan_ly_vung")
        NhanVien.objects.update_or_create(
            user=self.user_qlv,
            defaults={"ho_ten": "Quản Lý Vùng", "tenant_id": self.tenant_id},
        )

        self.user_dt = User.objects.create_user(username="dt", password="password")
        assign_role(self.user_dt, "doi_truong")
        NhanVien.objects.update_or_create(
            user=self.user_dt,
            defaults={"ho_ten": "Đội Trưởng", "tenant_id": self.tenant_id},
        )

        self.user_guard = User.objects.create_user(username="guard", password="password")
        assign_role(self.user_guard, "nhan_vien_bao_ve")
        NhanVien.objects.update_or_create(
            user=self.user_guard,
            defaults={"ho_ten": "Bảo Vệ", "tenant_id": self.tenant_id},
        )

    def _minimal_dashboard_payload(self):
        return {
            "stats": {
                "tong_ca": 0,
                "da_checkin": 0,
                "vang_mat": 0,
                "tong_muc_tieu": 0,
                "tong_su_co": 0,
                "su_co_nghiem_trong": 0,
                "ti_le_phu_ca": 0,
                "leave_schedule_conflicts": 0,
            },
            "markers": [],
            "incidents": [],
            "recent_activity": [],
            "last_activity": None,
            "leave_schedule_conflicts": [],
            "diagnostics": {},
        }

    @patch("operations.api_views.cache")
    @patch("operations.api_views.GetOperationsDashboardUseCase.execute")
    def test_dashboard_api_allows_every_operations_route_role_from_dashboard_router(
        self,
        mock_execute,
        mock_cache,
    ):
        mock_cache.get.return_value = None
        mock_execute.return_value = self._minimal_dashboard_payload()

        for user in (self.user_bgd, self.user_qlv, self.user_dt):
            with self.subTest(username=user.username):
                self.assertTrue(DashboardRouter.user_can_access(user, "operations:dashboard_vanhanh"))
                self.client.force_authenticate(user=user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertIn("stats", response.data)

        self.assertEqual(mock_execute.call_count, 3)

    @patch("operations.api_views.cache")
    @patch("operations.api_views.GetOperationsDashboardUseCase.execute")
    def test_dashboard_api_denies_user_when_dashboard_router_denies_shell_route(
        self,
        mock_execute,
        mock_cache,
    ):
        mock_cache.get.return_value = None
        self.assertFalse(DashboardRouter.user_can_access(self.user_guard, "operations:dashboard_vanhanh"))

        self.client.force_authenticate(user=self.user_guard)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error_code"], "permission_denied")
        self.assertIn("không có quyền", response.data["message"].lower())
        mock_execute.assert_not_called()
=======
        
        # Mock chaining cho incidents_qs: .for_tenant().filter().select_related().order_by()
        incident_qs = MockBaoCaoSuCo.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value
        incident_qs.__iter__.return_value = [mock_incident]

        # 4. Giả lập Last Activity
        last_qs = MockChamCong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value
        last_qs.first.return_value = mock_cc

        # --- THỰC THI USE CASE ---
        result = GetWarRoomDashboardUseCase.execute(
            tenant_id=self.tenant_id,
            target_date=self.target_date
        )

        # --- KIỂM TRA KẾT QUẢ (ASSERTIONS) ---
        
        # Kiểm tra Stats
        self.assertEqual(result['stats']['tong_ca'], 10)
        self.assertEqual(result['stats']['da_checkin'], 1)
        self.assertEqual(result['stats']['vang_mat'], 9)

        # Kiểm tra Markers (Chuyển đổi PointField y,x sang lat,lng)
        self.assertEqual(len(result['markers']), 1)
        self.assertEqual(result['markers'][0]['name'], "Nguyễn Văn A")
        self.assertEqual(result['markers'][0]['lat'], 10.762622)
        self.assertEqual(result['markers'][0]['lng'], 106.660172)

        # Kiểm tra Incidents
        self.assertEqual(len(result['incidents']), 1)
        self.assertEqual(result['incidents'][0]['title'], "Mất cắp vật tư")

        # Kiểm tra Last Activity
        self.assertIsNotNone(result['last_activity'])
        self.assertEqual(result['last_activity']['user'], "Nguyễn Văn A")
        self.assertEqual(result['last_activity']['time'], "06:00")

    @patch('operations.application.dashboard_use_cases.ChamCong')
    @patch('operations.application.dashboard_use_cases.PhanCongCaTruc')
    @patch('operations.application.dashboard_use_cases.BaoCaoSuCo')
    def test_execute_empty_data(self, MockBaoCaoSuCo, MockPhanCong, MockChamCong):
        """Kiểm tra trường hợp ngày không có dữ liệu ca trực."""
        # Mock return empty lists/counts
        MockChamCong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.__iter__.return_value = []
        MockPhanCong.objects.for_tenant.return_value.filter.return_value.count.return_value = 0
        MockBaoCaoSuCo.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.__iter__.return_value = []
        MockChamCong.objects.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = None

        result = GetWarRoomDashboardUseCase.execute(
            tenant_id=self.tenant_id,
            target_date=self.target_date
        )

        self.assertEqual(result['stats']['tong_ca'], 0)
        self.assertEqual(len(result['markers']), 0)
        self.assertIsNone(result['last_activity'])

if __name__ == '__main__':
    unittest.main()

class DashboardAPIRoleBasedAccessTest(unittest.TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('operations:api_dashboard_data')
        self.tenant_id = settings.SCMD_ORGANIZATION_ID

        # Create roles
        self.bgd_group = Group.objects.create(name='BanGiamDoc')
        self.qlv_group = Group.objects.create(name='QuanLyVung')
        self.dt_group = Group.objects.create(name='DoiTruong')

        # Create users
        self.user_bgd = User.objects.create_user(username='bgd', password='password')
        self.user_bgd.groups.add(self.bgd_group)
        self.nv_bgd = NhanVien.objects.create(user=self.user_bgd, ho_ten="Giám Đốc")

        self.user_qlv = User.objects.create_user(username='qlv', password='password')
        self.user_qlv.groups.add(self.qlv_group)
        self.nv_qlv = NhanVien.objects.create(user=self.user_qlv, ho_ten="Quản Lý Vùng")

        self.user_dt = User.objects.create_user(username='dt', password='password')
        self.user_dt.groups.add(self.dt_group)
        self.nv_dt = NhanVien.objects.create(user=self.user_dt, ho_ten="Đội Trưởng")

        self.user_guard = User.objects.create_user(username='guard', password='password')
        self.nv_guard = NhanVien.objects.create(user=self.user_guard, ho_ten="Bảo Vệ")

        # Create targets
        self.kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH Test", sdt="0123456789")
        self.hd = HopDong.objects.create(so_hop_dong="HD001", ngay_ky=timezone.now().date(), ngay_hieu_luc=timezone.now().date(), ngay_het_han=timezone.now().date() + timedelta(days=365), gia_tri=1000000)
        self.target1 = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="Target Alpha", quan_ly_vung=self.nv_qlv, quan_ly_muc_tieu=self.nv_dt, vi_do=10.0, kinh_do=106.0, ban_kinh_cho_phep=100)
        self.target2 = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="Target Beta", vi_do=11.0, kinh_do=107.0, ban_kinh_cho_phep=100)

        # Create some ChamCong for target1
        self.vt1 = ViTriChot.objects.create(muc_tieu=self.target1, ten_vi_tri="Chốt 1")
        self.ca1 = CaLamViec.objects.create(ten_ca="Ca Sáng", gio_bat_dau="06:00", gio_ket_thuc="14:00")
        self.pc1 = PhanCongCaTruc.objects.create(nhan_vien=self.nv_guard, vi_tri_chot=self.vt1, ca_lam_viec=self.ca1, ngay_truc=timezone.now().date())
        ChamCong.objects.create(ca_truc=self.pc1, thoi_gian_check_in=timezone.now(), location_check_in=Point(106.0, 10.0, srid=4326))

    @patch('operations.dashboard_use_cases.MucTieu.objects')
    @patch('operations.dashboard_use_cases.ChamCong.objects')
    @patch('operations.dashboard_use_cases.PhanCongCaTruc.objects')
    @patch('operations.dashboard_use_cases.BaoCaoSuCo.objects')
    def test_dashboard_access_ban_giam_doc(self, MockBaoCaoSuCo, MockPhanCongCaTruc, MockChamCong, MockMucTieu):
        self.client.force_authenticate(user=self.user_bgd)
        
        # Mock MucTieu.objects.values_list for BGĐ
        MockMucTieu.for_tenant.return_value.values_list.return_value = [self.target1.id, self.target2.id]

        # Mock other objects to return some data
        MockChamCong.for_tenant.return_value.filter.return_value.select_related.return_value.__iter__.return_value = [MagicMock()]
        MockPhanCongCaTruc.for_tenant.return_value.filter.return_value.count.return_value = 2
        MockBaoCaoSuCo.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.__iter__.return_value = []
        MockChamCong.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = MagicMock()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stats', response.data)
        # Ensure MucTieu.objects.values_list was called without specific filters for QLV/DT
        MockMucTieu.for_tenant.return_value.values_list.assert_called_once()

    @patch('operations.dashboard_use_cases.MucTieu.objects')
    @patch('operations.dashboard_use_cases.ChamCong.objects')
    @patch('operations.dashboard_use_cases.PhanCongCaTruc.objects')
    @patch('operations.dashboard_use_cases.BaoCaoSuCo.objects')
    def test_dashboard_access_quan_ly_vung(self, MockBaoCaoSuCo, MockPhanCongCaTruc, MockChamCong, MockMucTieu):
        self.client.force_authenticate(user=self.user_qlv)
        
        # Mock MucTieu.objects.filter for QLV
        MockMucTieu.for_tenant.return_value.filter.return_value.values_list.return_value = [self.target1.id]

        # Mock other objects to return some data
        MockChamCong.for_tenant.return_value.filter.return_value.select_related.return_value.__iter__.return_value = [MagicMock()]
        MockPhanCongCaTruc.for_tenant.return_value.filter.return_value.count.return_value = 1
        MockBaoCaoSuCo.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.__iter__.return_value = []
        MockChamCong.for_tenant.return_value.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = MagicMock()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stats', response.data)
        # Ensure MucTieu.objects.filter was called with quan_ly_vung
        MockMucTieu.for_tenant.return_value.filter.assert_called_once_with(quan_ly_vung=self.nv_qlv)

    def test_dashboard_access_guard_unauthorized(self):
        """Bảo vệ không có quyền truy cập Dashboard API."""
        self.client.force_authenticate(user=self.user_guard)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error_code'], 'permission_denied')
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    def test_dashboard_access_unauthenticated(self):
        """Người dùng chưa xác thực không có quyền truy cập Dashboard API."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
<<<<<<< HEAD
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "Authentication credentials were not provided.",
        )

class OperationsDashboardUseCaseTest(TestCase):
    def test_dashboard_use_case_uses_timestamp_range_not_date_lookup(self):
        source = Path("operations/application/dashboard_use_cases.py").read_text(encoding="utf-8")

        self.assertNotIn("thoi_gian_check_in" + "__date", source)
        self.assertIn("thoi_gian_check_in__gte=start_at", source)
        self.assertIn("thoi_gian_check_in__lt=end_at", source)

    @patch("operations.application.dashboard_use_cases.MucTieu.objects")
    def test_technical_admin_gets_full_target_scope_without_nhanvien(self, mock_muc_tieu_objects):
        user = User.objects.create_user(username="staff-no-profile", password="password")
        user.is_staff = True
        user.save(update_fields=["is_staff"])

        sentinel_qs = MagicMock()
        mock_muc_tieu_objects.for_tenant.return_value = sentinel_qs

        result = GetOperationsDashboardUseCase._get_allowed_targets_queryset(
            user=user,
            tenant_id="org-1",
        )

        self.assertIs(result, sentinel_qs)
        mock_muc_tieu_objects.for_tenant.assert_called_once_with("org-1")
=======
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
