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