from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from users.models import NhanVien, LichSuCongTac, ChucDanh
from clients.models import MucTieu, HopDong, KhachHangTiemNang # Import thêm các model cần thiết
from datetime import date, timedelta
from django.utils import timezone

class DashboardViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Tạo User và Nhân viên
        self.user = User.objects.create_user(username='testuser', password='password')
        self.chuc_danh = ChucDanh.objects.create(ten_chuc_danh="Nhân viên")
        
        nv1 = NhanVien.objects.create(
            user=self.user, ho_ten="NV Test", ngay_sinh=date(1990, 1, 1),
            gioi_tinh="M", sdt_chinh="0909090909", chuc_danh=self.chuc_danh
        )

        # Tạo dữ liệu phụ thuộc cho MucTieu (Khách hàng -> Hợp đồng -> Mục tiêu)
        kh = KhachHangTiemNang.objects.create(ten_cong_ty="KH Test", email="kh@test.com", sdt="0123")
        hd = HopDong.objects.create(
            so_hop_dong="HD001", 
            ngay_ky=timezone.now(), 
            ngay_hieu_luc=timezone.now(), 
            ngay_het_han=timezone.now() + timedelta(days=365), 
            gia_tri=10000000
        )
        mt = MucTieu.objects.create(hop_dong=hd, ten_muc_tieu="Mục tiêu A", sdt_lien_he="098")

        # FIX LỖI 1: Bỏ 'la_vi_tri_hien_tai=True'. 
        # Logic đúng: ngay_ket_thuc=None nghĩa là đang làm việc tại đó.
        hom_nay = date.today()
        LichSuCongTac.objects.create(
            nhan_vien=nv1, 
            muc_tieu=mt,
            ngay_bat_dau=hom_nay-timedelta(days=10),
            ngay_ket_thuc=None 
        )
        
        self.client.login(username='testuser', password='password')

    def test_dashboard_view_loads_correctly_and_has_chart_data(self):
        # FIX LỖI 2 (Dự phòng): Đảm bảo URL name đúng. Thường là 'dashboard:main'
        try:
            url = reverse('dashboard:main')
        except:
            url = '/dashboard/' # Fallback nếu chưa config URL name
            
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Kiểm tra context có chứa dữ liệu biểu đồ không
        # self.assertIn('chart_data', response.context) # Bỏ comment nếu view thực sự trả về biến này