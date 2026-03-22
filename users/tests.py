# file: users/tests.py
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.core.exceptions import PermissionDenied # Import exception
from .models import NhanVien, CauHinhMaNhanVien, PhongBan, ChucDanh
from datetime import date
from .views import export_ly_lich_pdf

class NhanVienModelTestCase(TestCase):
    def setUp(self):
        # Reset cấu hình mỗi lần chạy test để đảm bảo tính nhất quán
        CauHinhMaNhanVien.objects.all().delete()
        CauHinhMaNhanVien.objects.create(pk=1, tien_to="NV", do_dai_so=4, so_hien_tai=0)
        
        self.phong_ban = PhongBan.objects.create(ten_phong_ban="Phòng Kỹ thuật")
        self.chuc_danh = ChucDanh.objects.create(ten_chuc_danh="Lập trình viên")
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_generate_employee_code_on_creation(self):
        nv1 = NhanVien.objects.create(
            ho_ten="Nguyễn Văn A", ngay_sinh=date(1990, 1, 1), gioi_tinh="M",
            so_cccd="123456789012", sdt_chinh="+84901234567", email="a.nguyen@example.com"
        )
        self.assertEqual(nv1.ma_nhan_vien, "NV0001")

        nv2 = NhanVien.objects.create(
            ho_ten="Trần Thị B", ngay_sinh=date(1995, 5, 10), gioi_tinh="F",
            so_cccd="987654321098", sdt_chinh="+84987654321", email="b.tran@example.com"
        )
        self.assertEqual(nv2.ma_nhan_vien, "NV0002")

    def test_permission_signal(self):
        group_pb = Group.objects.create(name='Quyền Phòng Ban')
        group_cd = Group.objects.create(name='Quyền Chức Danh')
        
        self.phong_ban.nhom_quyen = group_pb
        self.phong_ban.save()
        self.chuc_danh.nhom_quyen = group_cd
        self.chuc_danh.save()

        nhan_vien = NhanVien.objects.create(
            user=self.user, ho_ten="Test Signal", ngay_sinh=date(2000, 1, 1),
            gioi_tinh="O", so_cccd="111222333", sdt_chinh="+84123456789",
            email="signal@test.com", phong_ban=self.phong_ban, chuc_danh=self.chuc_danh
        )
        
        self.assertIn(group_pb, self.user.groups.all())
        self.assertIn(group_cd, self.user.groups.all())

class PDFExportTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('pdfuser', 'pdf@test.com', 'password')
        self.staff_user = User.objects.create_user('staffuser', 'staff@test.com', 'password', is_staff=True)
        
        permission = Permission.objects.get(codename='view_nhanvien')
        self.staff_user.user_permissions.add(permission)
        
        self.nhan_vien = NhanVien.objects.create(
            ho_ten="PDF Tester", ngay_sinh=date(1998, 1, 1), gioi_tinh="M",
            so_cccd="000000000000", sdt_chinh="+84900000000", email="pdf.tester@example.com"
        )
        self.url = reverse('users:export-ly-lich', args=[self.nhan_vien.id])

    def test_pdf_export_permission_denied(self):
        request = self.factory.post(self.url)
        request.user = self.user 
        
        # FIX: Bắt exception PermissionDenied thay vì kiểm tra status code
        with self.assertRaises(PermissionDenied):
            export_ly_lich_pdf(request, self.nhan_vien.id)

    def test_pdf_export_success(self):
        post_data = {
            "bao_gom_anh_the": "on",
            "bao_gom_thong_tin_ca_nhan": "on",
        }
        request = self.factory.post(self.url, post_data)
        request.user = self.staff_user 
        
        response = export_ly_lich_pdf(request, self.nhan_vien.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')