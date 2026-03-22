# file: operations/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from .models import ViTriChot, CaLamViec, PhanCongCaTruc, BaoCaoSuCo, ChamCong
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

    def test_cham_cong_checkin(self):
        cham_cong = ChamCong.objects.create(ca_truc=self.phan_cong)
        cham_cong.thoi_gian_check_in = timezone.now()
        cham_cong.save()
        self.assertTrue(self.phan_cong.da_checkin)

class OperationsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='bv1', password='password')
        self.nhan_vien = NhanVien.objects.create(user=self.user, ho_ten="Bảo vệ API", ngay_sinh="1990-01-01", gioi_tinh="M", sdt_chinh="+84999888777")
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