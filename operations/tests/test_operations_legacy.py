# file: operations/tests.py
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from operations.application.incident_transition_policy import IncidentTransitionPolicy
from operations.admin import BaoCaoSuCoAdminForm
from operations.models import ViTriChot, CaLamViec, PhanCongCaTruc, BaoCaoSuCo, ChamCong
from users.models import NhanVien
from clients.models import MucTieu, HopDong, KhachHangTiemNang

class OperationsModelTest(TestCase):
    def setUp(self):
        self.kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH Test", email="test@kh.com", sdt="0999")
        self.hop_dong = HopDong.objects.create(so_hop_dong="HD001", ngay_ky=timezone.now(), ngay_hieu_luc=timezone.now(), ngay_het_han=timezone.now(), gia_tri=1000)
        self.muc_tieu = MucTieu.objects.create(hop_dong=self.hop_dong, ten_muc_tieu="Mục tiêu A", sdt_lien_he="0123")
        self.vi_tri = ViTriChot.objects.create(muc_tieu=self.muc_tieu, ten_vi_tri="Cổng chính")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Sáng", gio_bat_dau="06:00", gio_ket_thuc="14:00")
        
        self.nhan_vien = NhanVien.objects.create(ho_ten="Bảo vệ 1", ngay_sinh="1990-01-01", gioi_tinh="M", sdt_chinh="+84987654321")
        self.phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri, 
            nhan_vien=self.nhan_vien, 
            ca_lam_viec=self.ca, 
            ngay_truc=timezone.now().date()
        )

    def test_bao_cao_su_co_uuid_generation(self):
        """Test xem mã sự cố có tự sinh ra dạng UUID không"""
        su_co = BaoCaoSuCo.objects.create(
            tieu_de="Mất xe đạp",
            muc_tieu=self.muc_tieu
        )
        self.assertTrue(su_co.ma_su_co.startswith("SC-"))
        # SC (3) + YYYYMMDD (8) + - (1) + UUID 6 chars (6) = 18 ký tự
        self.assertEqual(len(su_co.ma_su_co), 18) 

    def test_bao_cao_su_co_generates_unique_codes_across_direct_creates(self):
        first = BaoCaoSuCo.objects.create(
            tieu_de="Su co 1",
            muc_tieu=self.muc_tieu
        )
        second = BaoCaoSuCo.objects.create(
            tieu_de="Su co 2",
            muc_tieu=self.muc_tieu
        )

        self.assertNotEqual(first.ma_su_co, second.ma_su_co)
        self.assertNotEqual(first.ma_su_co, "PENDING")
        self.assertNotEqual(second.ma_su_co, "PENDING")

    def test_bao_cao_su_co_replaces_legacy_pending_placeholder(self):
        su_co = BaoCaoSuCo.objects.create(
            tieu_de="Su co legacy",
            muc_tieu=self.muc_tieu,
            ma_su_co="PENDING"
        )

        self.assertTrue(su_co.ma_su_co.startswith("SC-"))
        self.assertNotEqual(su_co.ma_su_co, "PENDING")

    def test_cham_cong_checkin(self):
        cham_cong = ChamCong.objects.create(ca_truc=self.phan_cong)
        cham_cong.thoi_gian_check_in = timezone.now()

        with self.assertRaisesMessage(ValidationError, "Dữ liệu chấm công nhạy cảm"):
            cham_cong.save()

        self.phan_cong.refresh_from_db()
        self.assertFalse(self.phan_cong.da_checkin)


class IncidentTransitionPolicyTest(TestCase):
    def test_closed_incident_only_allows_reopen_transition(self):
        IncidentTransitionPolicy.validate_transition("HOAN_TAT", "DANG_XU_LY")

        with self.assertRaises(ValueError):
            IncidentTransitionPolicy.validate_transition("HOAN_TAT", "CHO_DEN_BU")

    def test_closed_incident_blocks_primary_field_edits_without_reopen(self):
        with self.assertRaises(ValueError):
            IncidentTransitionPolicy.validate_closed_incident_edit(
                previous_status="HUY",
                new_status="HUY",
                changed_fields={"tong_thiet_hai"},
            )

    def test_closed_incident_reopen_only_allows_status_change(self):
        IncidentTransitionPolicy.validate_closed_incident_edit(
            previous_status="HUY",
            new_status="DANG_XU_LY",
            changed_fields={"trang_thai"},
        )

        with self.assertRaises(ValueError):
            IncidentTransitionPolicy.validate_closed_incident_edit(
                previous_status="HUY",
                new_status="DANG_XU_LY",
                changed_fields={"trang_thai", "tong_thiet_hai"},
            )


class IncidentAdminFormRegressionTest(TestCase):
    def setUp(self):
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-INC-001",
            ngay_ky=timezone.now(),
            ngay_hieu_luc=timezone.now(),
            ngay_het_han=timezone.now(),
            gia_tri=1000,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu su co",
            sdt_lien_he="0123",
        )
        self.su_co = BaoCaoSuCo.objects.create(
            tieu_de="Su co dong",
            muc_tieu=self.muc_tieu,
            trang_thai=IncidentTransitionPolicy.STATUS_HOAN_TAT,
        )

    def _build_form(self, *, trang_thai, transition_reason="", tong_thiet_hai=None):
        payload = {
            "tieu_de": self.su_co.tieu_de,
            "muc_do": self.su_co.muc_do,
            "muc_tieu": self.su_co.muc_tieu_id,
            "ca_truc": self.su_co.ca_truc_id,
            "thoi_gian_phat_hien": self.su_co.thoi_gian_phat_hien.strftime("%Y-%m-%d %H:%M:%S"),
            "mo_ta_chi_tiet": self.su_co.mo_ta_chi_tiet or "",
            "tong_thiet_hai": tong_thiet_hai if tong_thiet_hai is not None else self.su_co.tong_thiet_hai,
            "cong_ty_chi_tra": self.su_co.cong_ty_chi_tra,
            "nhan_vien_co_loi": self.su_co.nhan_vien_co_loi_id,
            "phai_thu_nhan_vien": self.su_co.phai_thu_nhan_vien,
            "nguoi_xu_ly": self.su_co.nguoi_xu_ly_id,
            "ghi_chu_quan_ly": self.su_co.ghi_chu_quan_ly or "",
            "trang_thai": trang_thai,
            "transition_reason": transition_reason,
        }
        return BaoCaoSuCoAdminForm(data=payload, instance=self.su_co)

    def test_admin_form_requires_reason_for_reopen_transition(self):
        form = self._build_form(
            trang_thai=IncidentTransitionPolicy.REOPEN_TARGET_STATUS,
            transition_reason="",
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Phải nhập lý do", str(form.errors))

    def test_admin_form_allows_reopen_with_reason_and_status_only(self):
        form = self._build_form(
            trang_thai=IncidentTransitionPolicy.REOPEN_TARGET_STATUS,
            transition_reason="Can dieu tra bo sung",
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_blocks_reopen_with_primary_field_edit(self):
        form = self._build_form(
            trang_thai=IncidentTransitionPolicy.REOPEN_TARGET_STATUS,
            transition_reason="Can dieu tra bo sung",
            tong_thiet_hai=5000,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Không được sửa trực tiếp các trường nội dung chính", str(form.errors))

class OperationsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='bv1', email='bv1@example.com', password='password')
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Bao ve API"
        self.nhan_vien.ngay_sinh = "1990-01-01"
        self.nhan_vien.gioi_tinh = "M"
        self.nhan_vien.sdt_chinh = "+84999888777"
        self.nhan_vien.save()
        self.client.force_authenticate(user=self.user)

        self.kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH API", email="api@kh.com", sdt="0888")
        self.hop_dong = HopDong.objects.create(so_hop_dong="HD-API", ngay_ky=timezone.now(), ngay_hieu_luc=timezone.now(), ngay_het_han=timezone.now(), gia_tri=5000)
        self.muc_tieu = MucTieu.objects.create(hop_dong=self.hop_dong, ten_muc_tieu="Mục tiêu API", sdt_lien_he="0111")
        self.vi_tri = ViTriChot.objects.create(muc_tieu=self.muc_tieu, ten_vi_tri="Chốt 1")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Chiều", gio_bat_dau="14:00", gio_ket_thuc="22:00")
        
        self.phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date()
        )

    def test_get_my_schedule(self):
        url = reverse('operations:mobile-ca-truc-list') 
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # FIX: DRF trả về {count, next, previous, results}. Dữ liệu nằm trong 'results'
        if 'results' in response.data:
            data_list = response.data['results']
        else:
            data_list = response.data
            
        self.assertEqual(len(data_list), 1)
        self.assertEqual(data_list[0]['vi_tri_chot']['ten_vi_tri'], "Chốt 1")


    def test_checkin_api_rejects_other_employee_shift(self):
        other_user = User.objects.create_user(username='bv2', email='bv2@example.com', password='password')
        other_employee = other_user.nhan_vien
        other_employee.ho_ten = "Bao ve khac"
        other_employee.ngay_sinh = "1991-01-01"
        other_employee.gioi_tinh = "M"
        other_employee.sdt_chinh = "+84991111222"
        other_employee.save()
        other_shift = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=other_employee,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date()
        )

        response = self.client.post(
            reverse('operations:mobile_checkin_api'),
            {
                'ca_truc_id': other_shift.id,
                'lat': '10.0',
                'lng': '106.0',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_checkout_api_rejects_other_employee_shift(self):
        other_user = User.objects.create_user(username='bv3', email='bv3@example.com', password='password')
        other_employee = other_user.nhan_vien
        other_employee.ho_ten = "Bao ve checkout"
        other_employee.ngay_sinh = "1992-01-01"
        other_employee.gioi_tinh = "M"
        other_employee.sdt_chinh = "+84992222333"
        other_employee.save()
        other_shift = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=other_employee,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date()
        )

        response = self.client.post(
            reverse('operations:mobile_checkout_api'),
            {
                'ca_truc_id': other_shift.id,
                'lat': '10.0',
                'lng': '106.0',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class OperationsAttendanceViewSecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='bvweb', email='bvweb@example.com', password='password')
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Bao ve web"
        self.nhan_vien.ngay_sinh = "1990-01-01"
        self.nhan_vien.gioi_tinh = "M"
        self.nhan_vien.sdt_chinh = "+84993333444"
        self.nhan_vien.save()
        self.client.login(username='bvweb', password='password')

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-WEB",
            ngay_ky=timezone.now(),
            ngay_hieu_luc=timezone.now(),
            ngay_het_han=timezone.now(),
            gia_tri=5000,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu web",
            sdt_lien_he="0222",
        )
        self.vi_tri = ViTriChot.objects.create(muc_tieu=self.muc_tieu, ten_vi_tri="Chot web")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Web", gio_bat_dau="06:00", gio_ket_thuc="14:00")

    def test_checkin_view_rejects_other_employee_shift(self):
        other_user = User.objects.create_user(username='bvweb2', email='bvweb2@example.com', password='password')
        other_employee = other_user.nhan_vien
        other_employee.ho_ten = "Bao ve web khac"
        other_employee.ngay_sinh = "1993-01-01"
        other_employee.gioi_tinh = "M"
        other_employee.sdt_chinh = "+84994444555"
        other_employee.save()
        other_shift = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=other_employee,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date(),
        )

        response = self.client.post(
            reverse('operations:check_in', args=[other_shift.id]),
            {'lat': '10.0', 'lng': '106.0'},
            follow=True,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ChamCong.objects.filter(ca_truc=other_shift, thoi_gian_check_in__isnull=False).exists())


class OperationsDashboardPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='opsdash', email='opsdash@example.com', password='password')
        ops_group, _ = Group.objects.get_or_create(name='Đội trưởng')
        self.user.groups.add(ops_group)
        self.client.login(username='opsdash', password='password')

    def test_operations_dashboard_page_loads(self):
        response = self.client.get(reverse('operations:dashboard_vanhanh'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trình chiếu")
        self.assertContains(response, "/operations/dashboard/trinh-chieu/")

    def test_operations_presentation_page_loads(self):
        response = self.client.get(reverse('operations:dashboard_trinh_chieu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Màn hình trình chiếu SCMD Pro")


class CeleryTaskIdempotencyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Test NV"
        self.nhan_vien.save()
        self.kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH Test", sdt="0123456789")
        self.hd = HopDong.objects.create(so_hop_dong="HD001", ngay_ky=timezone.now().date(), ngay_hieu_luc=timezone.now().date(), ngay_het_han=timezone.now().date() + timedelta(days=365), gia_tri=1000000)
        self.muc_tieu = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="Mục tiêu Test", vi_do=10.0, kinh_do=106.0, ban_kinh_cho_phep=100)
        self.vi_tri = ViTriChot.objects.create(muc_tieu=self.muc_tieu, ten_vi_tri="Chốt Test")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Test", gio_bat_dau="08:00", gio_ket_thuc="17:00")
        self.phan_cong = PhanCongCaTruc.objects.create(
            nhan_vien=self.nhan_vien,
            vi_tri_chot=self.vi_tri,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date()
        )
        self.cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now() - timedelta(hours=8),
            thoi_gian_check_out=timezone.now(),
            thuc_lam_gio=0.0 # Initial value
        )

    @patch('operations.application.attendance_use_cases.CalculateWorkHoursUseCase.execute')
    def test_process_timesheet_async_idempotency(self, mock_calculate_work_hours):
        """
        Đảm bảo task process_timesheet_async là idempotent.
        Nghĩa là gọi nhiều lần không làm thay đổi kết quả sau lần gọi đầu tiên.
        """
        from operations.tasks import process_timesheet_async

        # Mock the calculation to return a fixed value
        mock_calculate_work_hours.return_value = 8.5

        # First call to the task
        process_timesheet_async(self.cham_cong.id)
        self.cham_cong.refresh_from_db()
        self.assertEqual(self.cham_cong.thuc_lam_gio, 8.5)
        mock_calculate_work_hours.assert_called_once_with(self.cham_cong)

        # Reset mock for second call
        mock_calculate_work_hours.reset_mock()
        mock_calculate_work_hours.return_value = 8.5 # Still returns the same value

        # Second call to the task
        process_timesheet_async(self.cham_cong.id)
        self.cham_cong.refresh_from_db()
        self.assertEqual(self.cham_cong.thuc_lam_gio, 8.5) # Value should not change
        # The calculation should still be performed, as the task is designed to update the field.
        # The idempotency here means it won't *incorrectly* modify the value if called again.
        mock_calculate_work_hours.assert_called_once_with(self.cham_cong)
