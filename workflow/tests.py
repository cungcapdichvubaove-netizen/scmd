# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: workflow/tests.py
Author: Mr. Anh (CTO)
Description: Kịch bản kiểm thử tự động (Automated Test Suite).
             FIXED: Sửa lỗi IntegrityError do xung đột tạo User/NhanVien.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from users.models import NhanVien, PhongBan, ChucDanh
from workflow.models import Task, Proposal
from operations.models import MucTieu
import datetime

class SecurityCompanyScenarioTest(TestCase):
    """
    Kịch bản: Công ty Bảo vệ SCMD với 500 nhân sự.
    """

    @classmethod
    def setUpTestData(cls):
        print("\n=== ĐANG KHỞI TẠO DỮ LIỆU GIẢ LẬP (SCENARIO SETUP) ===")
        
        # 1. CẤU HÌNH PHÒNG BAN & CHỨC DANH
        pb_bgd = PhongBan.objects.create(ten_phong_ban="Ban Giám Đốc", mo_ta="Lãnh đạo")
        pb_nv = PhongBan.objects.create(ten_phong_ban="Phòng Nghiệp vụ", mo_ta="Vận hành")
        pb_ns = PhongBan.objects.create(ten_phong_ban="Phòng Nhân sự", mo_ta="Tuyển dụng")
        
        cd_ceo = ChucDanh.objects.create(ten_chuc_danh="Tổng Giám Đốc")
        cd_manager = ChucDanh.objects.create(ten_chuc_danh="Trưởng phòng")
        cd_staff = ChucDanh.objects.create(ten_chuc_danh="Chuyên viên")
        cd_guard = ChucDanh.objects.create(ten_chuc_danh="Nhân viên Bảo vệ")

        # 2. TẠO NHÂN SỰ CHỦ CHỐT (KEY USERS)
        # FIX: Tạo NhanVien trước, hệ thống tự sinh User (dựa trên logic model save())
        # Lưu ý: Model NhanVien đã có logic tự tạo User nếu user=None
        
        # CEO
        cls.nv_ceo = NhanVien.objects.create(
            ho_ten="Nguyễn Văn CEO",
            phong_ban=pb_bgd, chuc_danh=cd_ceo,
            trang_thai_lam_viec='CHINHTHUC',
            email="ceo@scmd.vn" # Email dùng để login nếu cần
        )
        # Lấy user tự sinh ra để set password
        cls.user_ceo = cls.nv_ceo.user
<<<<<<< HEAD
        assert cls.user_ceo is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        cls.user_ceo.set_password('password123')
        cls.user_ceo.save()

        # Trưởng phòng Nghiệp vụ
        cls.nv_tp = NhanVien.objects.create(
            ho_ten="Trần Nghiệp Vụ",
            phong_ban=pb_nv, chuc_danh=cd_manager,
            trang_thai_lam_viec='CHINHTHUC',
            email="tp@scmd.vn"
        )
        cls.user_tp = cls.nv_tp.user
<<<<<<< HEAD
        assert cls.user_tp is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        cls.user_tp.set_password('password123')
        cls.user_tp.save()

        # Nhân viên Nhân sự
        cls.nv_staff = NhanVien.objects.create(
            ho_ten="Lê Nhân Sự",
            phong_ban=pb_ns, chuc_danh=cd_staff,
            trang_thai_lam_viec='CHINHTHUC',
            email="ns@scmd.vn"
        )
        cls.user_staff = cls.nv_staff.user
<<<<<<< HEAD
        assert cls.user_staff is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        cls.user_staff.set_password('password123')
        cls.user_staff.save()

        # 3. TẠO MỤC TIÊU BẢO VỆ
        cls.muc_tieu = MucTieu.objects.create(
            ten_muc_tieu="Nhà máy Samsung Thái Nguyên",
            dia_chi="KCN Yên Bình, Phổ Yên",
            quan_ly_muc_tieu=cls.nv_tp
        )

        # 4. TẠO 500 NHÂN VIÊN BẢO VỆ (MASS DATA)
        print("-> Đang tuyển dụng 500 bảo vệ ảo...")
        # Sử dụng bulk_create để tăng tốc (nhưng sẽ KHÔNG kích hoạt save() -> không có User)
        # Vì test này chỉ cần danh sách nhân viên để chọn (Select2) chứ không cần login từng người
        guards = []
        for i in range(1, 501):
            guards.append(NhanVien(
                ma_nhan_vien=f"BV{i:04d}",
                ho_ten=f"Nguyễn Bảo Vệ {i}",
                phong_ban=pb_nv,
                chuc_danh=cd_guard,
                trang_thai_lam_viec='CHINHTHUC'
            ))
        NhanVien.objects.bulk_create(guards)
        print(f"-> Đã tạo xong {NhanVien.objects.count()} nhân sự trong hệ thống.")

    def setUp(self):
        self.client = Client()

    # --- TEST CASE 1: QUY TRÌNH DUYỆT ĐỀ XUẤT ĐA CẤP ---
    def test_approval_workflow(self):
        print("\nTEST 1: QUY TRÌNH DUYỆT ĐA CẤP (NV -> TP -> CEO)")
        
        # BƯỚC 1: NV Nhân sự tạo tờ trình
        # Login bằng username tự sinh (thường là mã nhân viên)
<<<<<<< HEAD
        assert self.user_staff is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        self.client.login(username=self.user_staff.username, password='password123')
        create_url = reverse('workflow:proposal_create')
        data = {
            'loai_de_xuat': 'MUA_SAM',
            'tieu_de': 'Tờ trình mua máy in mới',
            'noi_dung': 'Máy cũ hỏng, xin mua Canon 2900 giá 3.5tr.',
<<<<<<< HEAD
            'nguoi_duyet_hien_tai': self.nv_tp.pk, # Kính trình TP
=======
            'nguoi_duyet_hien_tai': self.nv_tp.id, # Kính trình TP
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            'file_dinh_kem': ''
        }
        self.client.post(create_url, data)
        
        prop = Proposal.objects.get(tieu_de='Tờ trình mua máy in mới')
        self.assertEqual(prop.trang_thai, 'CHO_DUYET')
        self.assertEqual(prop.nguoi_duyet_hien_tai, self.nv_tp)
        print("✓ NV đã tạo tờ trình, đang chờ Trưởng phòng duyệt.")

        # BƯỚC 2: Trưởng phòng vào xem và CHUYỂN TIẾP lên CEO
        self.client.logout()
<<<<<<< HEAD
        assert self.user_tp is not None
        self.client.login(username=self.user_tp.username, password='password123')
        
        action_url = reverse('workflow:proposal_action', args=[prop.pk])
        action_data = {
            'hanh_dong': 'CHUYEN_TIEP',
            'y_kien': 'Đồng ý chủ trương, kính chuyển Tổng Giám Đốc phê duyệt chi.',
            'nguoi_tiep_theo': self.nv_ceo.pk
=======
        self.client.login(username=self.user_tp.username, password='password123')
        
        action_url = reverse('workflow:proposal_action', args=[prop.id])
        action_data = {
            'hanh_dong': 'CHUYEN_TIEP',
            'y_kien': 'Đồng ý chủ trương, kính chuyển Tổng Giám Đốc phê duyệt chi.',
            'nguoi_tiep_theo': self.nv_ceo.id
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        }
        self.client.post(action_url, action_data)
        
        prop.refresh_from_db()
        self.assertEqual(prop.nguoi_duyet_hien_tai, self.nv_ceo)
<<<<<<< HEAD
        self.assertEqual(getattr(prop, 'logs').count(), 2) 
=======
        self.assertEqual(prop.logs.count(), 2) 
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        print("✓ Trưởng phòng đã chuyển tiếp lên CEO.")

        # BƯỚC 3: CEO vào xem và PHÊ DUYỆT
        self.client.logout()
<<<<<<< HEAD
        assert self.user_ceo is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        self.client.login(username=self.user_ceo.username, password='password123')
        
        final_data = {
            'hanh_dong': 'DUYET_KET_THUC',
            'y_kien': 'Đồng ý. Chuyển Kế toán thanh toán ngay.',
            'nguoi_tiep_theo': ''
        }
        self.client.post(action_url, final_data)
        
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'DA_DUYET')
        self.assertIsNone(prop.nguoi_duyet_hien_tai) 
<<<<<<< HEAD
        print(f"✓ CEO đã phê duyệt. Trạng thái cuối: {getattr(prop, 'get_trang_thai_display')()}")
=======
        print(f"✓ CEO đã phê duyệt. Trạng thái cuối: {prop.get_trang_thai_display()}")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    # --- TEST CASE 2: GIAO VIỆC CHO NHÂN SỰ (TASK) ---
    def test_task_assignment(self):
        print("\nTEST 2: GIAO VIỆC & PHỐI HỢP")
<<<<<<< HEAD
        assert self.user_tp is not None
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        self.client.login(username=self.user_tp.username, password='password123')
        
        guards = NhanVien.objects.filter(chuc_danh__ten_chuc_danh="Nhân viên Bảo vệ")[:3]
        main_guard = guards[0]
<<<<<<< HEAD
        support_guards = [guards[1].pk, guards[2].pk]
=======
        support_guards = [guards[1].id, guards[2].id]
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        
        create_url = reverse('workflow:task_create')
        data = {
            'tieu_de': 'Tăng cường tuần tra đêm Noel',
            'noi_dung': 'Trực chiến 100% quân số tại cổng chính.',
<<<<<<< HEAD
            'nguoi_nhan': main_guard.pk,
            'nguoi_phoi_hop': support_guards,
            'muc_tieu': self.muc_tieu.pk,
=======
            'nguoi_nhan': main_guard.id,
            'nguoi_phoi_hop': support_guards,
            'muc_tieu': self.muc_tieu.id,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            'uu_tien': 'CAO',
            'han_chot': (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        }
        self.client.post(create_url, data)
        
        task = Task.objects.first()
<<<<<<< HEAD
        assert task is not None
        self.assertEqual(task.nguoi_nhan, main_guard)
        self.assertEqual(getattr(task, 'nguoi_phoi_hop').count(), 2)
=======
        self.assertEqual(task.nguoi_nhan, main_guard)
        self.assertEqual(task.nguoi_phoi_hop.count(), 2)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        print(f"✓ Đã giao việc cho {main_guard.ho_ten} và 2 người phối hợp.")

    # --- TEST CASE 3: BẢO MẬT PHÂN QUYỀN ---
    def test_security_access(self):
        print("\nTEST 3: KIỂM TRA BẢO MẬT (HACK ATTEMPT)")
        
        prop = Proposal.objects.create(
            tieu_de="Tờ trình mật",
            nguoi_de_xuat=self.nv_tp,
            nguoi_duyet_hien_tai=self.nv_ceo,
            trang_thai='CHO_DUYET'
        )
        
<<<<<<< HEAD
        assert self.user_staff is not None
        self.client.login(username=self.user_staff.username, password='password123')
        
        action_url = reverse('workflow:proposal_action', args=[prop.pk])
=======
        self.client.login(username=self.user_staff.username, password='password123')
        
        action_url = reverse('workflow:proposal_action', args=[prop.id])
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        response = self.client.post(action_url, {
            'hanh_dong': 'DUYET_KET_THUC', 
            'y_kien': 'Hack duyệt!'
        }, follow=True)
        
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'CHO_DUYET') 
        
        messages = list(response.context['messages'])
        self.assertTrue(any("không có quyền" in str(m) for m in messages))
<<<<<<< HEAD
        print("✓ HỆ THỐNG AN TOÀN: Nhân viên không thể duyệt thay CEO.")

    # --- TEST CASE 4: QUY TRÌNH TỪ CHỐI & YÊU CẦU SỬA ---
    def test_proposal_rejection_and_revision(self):
        print("\nTEST 4: QUY TRÌNH TỪ CHỐI & YÊU CẦU SỬA")
        # BƯỚC 1: NV Nhân sự tạo tờ trình
        assert self.user_staff is not None
        self.client.login(username=self.user_staff.username, password='password123')
        data = {
            'loai_de_xuat': 'KE_HOACH',
            'tieu_de': 'Kế hoạch nghỉ mát 2026',
            'noi_dung': 'Xin kinh phí đi nghỉ mát cho 500 nhân sự.',
            'nguoi_duyet_hien_tai': self.nv_tp.pk,
        }
        self.client.post(reverse('workflow:proposal_create'), data)
        prop = Proposal.objects.get(tieu_de='Kế hoạch nghỉ mát 2026')

        # BƯỚC 2: Trưởng phòng yêu cầu sửa đổi
        self.client.logout()
        assert self.user_tp is not None
        self.client.login(username=self.user_tp.username, password='password123')
        action_url = reverse('workflow:proposal_action', args=[prop.pk])
        self.client.post(action_url, {
            'han_dong': 'YEU_CAU_SUA',
            'y_kien': 'Kinh phí quá cao, cần tối ưu lại danh sách.'
        })
        
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'YEU_CAU_SUA')
        self.assertEqual(prop.nguoi_duyet_hien_tai, self.nv_staff) # Phải trả về người đề xuất
        print("✓ Trưởng phòng đã yêu cầu sửa đổi, tờ trình quay về NV.")

        # BƯỚC 3: Trưởng phòng từ chối (giả sử trường hợp không thể duyệt)
        self.client.post(action_url, {
            'han_dong': 'TU_CHOI',
            'y_kien': 'Không duyệt do thắt chặt chi tiêu trong giai đoạn này.'
        })
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'TU_CHOI')
        self.assertIsNone(prop.nguoi_duyet_hien_tai)
        print("✓ Trưởng phòng đã từ chối tờ trình thành công.")

    # --- TEST CASE 5: TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI TASK ---
    def test_task_auto_status_transition(self):
        print("\nTEST 5: TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI TASK")
        task = Task.objects.create(
            tieu_de="Kiểm tra camera cổng chính",
            noi_dung="Vệ sinh và kiểm tra góc quay",
            nguoi_giao=self.nv_tp,
            nguoi_nhan=self.nv_staff,
            trang_thai='MOI',
            tien_do=0
        )
        
        # Cập nhật tiến độ -> Trạng thái phải tự nhảy sang DANG_LAM (theo logic models.py)
        task.tien_do = 50
        task.save()
        self.assertEqual(task.trang_thai, 'DANG_LAM')
        
        # Cập nhật tiến độ 100% -> Trạng thái phải sang CHO_DUYET
        task.tien_do = 100
        task.save()
        self.assertEqual(task.trang_thai, 'CHO_DUYET')
        print("✓ Trạng thái Task tự động chuyển đổi theo tiến độ: Mới -> Đang làm -> Chờ nghiệm thu.")

    # --- TEST CASE 6: KIỂM TRA MẪU IN TỜ TRÌNH ---
    def test_proposal_print_view(self):
        print("\nTEST 6: KIỂM TRA MẪU IN TỜ TRÌNH")
        assert self.user_tp is not None
        self.client.login(username=self.user_tp.username, password='password123')
        prop = Proposal.objects.create(tieu_de="Tờ trình in test", nguoi_de_xuat=self.nv_staff, trang_thai='DA_DUYET')
        response = self.client.get(reverse('workflow:proposal_print', args=[prop.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tờ trình in test")
        print("✓ Trang in tờ trình hiển thị đúng nội dung.")

    # --- TEST CASE 4: QUY TRÌNH TỪ CHỐI & YÊU CẦU SỬA ---
    def test_proposal_rejection_and_revision(self):
        print("\nTEST 4: QUY TRÌNH TỪ CHỐI & YÊU CẦU SỬA")
        # BƯỚC 1: NV Nhân sự tạo tờ trình
        self.client.login(username=self.user_staff.username, password='password123')
        data = {
            'loai_de_xuat': 'KE_HOACH',
            'tieu_de': 'Kế hoạch nghỉ mát 2026',
            'noi_dung': 'Xin kinh phí đi nghỉ mát cho 500 nhân sự.',
            'nguoi_duyet_hien_tai': self.nv_tp.id,
        }
        self.client.post(reverse('workflow:proposal_create'), data)
        prop = Proposal.objects.get(tieu_de='Kế hoạch nghỉ mát 2026')

        # BƯỚC 2: Trưởng phòng yêu cầu sửa đổi
        self.client.logout()
        self.client.login(username=self.user_tp.username, password='password123')
        action_url = reverse('workflow:proposal_action', args=[prop.id])
        self.client.post(action_url, {
            'han_dong': 'YEU_CAU_SUA',
            'y_kien': 'Kinh phí quá cao, cần tối ưu lại danh sách.'
        })
        
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'YEU_CAU_SUA')
        self.assertEqual(prop.nguoi_duyet_hien_tai, self.nv_staff) # Phải trả về người đề xuất
        print("✓ Trưởng phòng đã yêu cầu sửa đổi, tờ trình quay về NV.")

        # BƯỚC 3: Trưởng phòng từ chối (giả sử trường hợp không thể duyệt)
        self.client.post(action_url, {
            'han_dong': 'TU_CHOI',
            'y_kien': 'Không duyệt do thắt chặt chi tiêu trong giai đoạn này.'
        })
        prop.refresh_from_db()
        self.assertEqual(prop.trang_thai, 'TU_CHOI')
        self.assertIsNone(prop.nguoi_duyet_hien_tai)
        print("✓ Trưởng phòng đã từ chối tờ trình thành công.")

    # --- TEST CASE 5: TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI TASK ---
    def test_task_auto_status_transition(self):
        print("\nTEST 5: TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI TASK")
        task = Task.objects.create(
            tieu_de="Kiểm tra camera cổng chính",
            noi_dung="Vệ sinh và kiểm tra góc quay",
            nguoi_giao=self.nv_tp,
            nguoi_nhan=self.nv_staff,
            trang_thai='MOI',
            tien_do=0
        )
        
        # Cập nhật tiến độ -> Trạng thái phải tự nhảy sang DANG_LAM (theo logic models.py)
        task.tien_do = 50
        task.save()
        self.assertEqual(task.trang_thai, 'DANG_LAM')
        
        # Cập nhật tiến độ 100% -> Trạng thái phải sang CHO_DUYET
        task.tien_do = 100
        task.save()
        self.assertEqual(task.trang_thai, 'CHO_DUYET')
        print("✓ Trạng thái Task tự động chuyển đổi theo tiến độ: Mới -> Đang làm -> Chờ nghiệm thu.")

    # --- TEST CASE 6: KIỂM TRA MẪU IN TỜ TRÌNH ---
    def test_proposal_print_view(self):
        print("\nTEST 6: KIỂM TRA MẪU IN TỜ TRÌNH")
        self.client.login(username=self.user_tp.username, password='password123')
        prop = Proposal.objects.create(tieu_de="Tờ trình in test", nguoi_de_xuat=self.nv_staff, trang_thai='DA_DUYET')
        response = self.client.get(reverse('workflow:proposal_print', args=[prop.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tờ trình in test")
        print("✓ Trang in tờ trình hiển thị đúng nội dung.")
=======
        print("✓ HỆ THỐNG AN TOÀN: Nhân viên không thể duyệt thay CEO.")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
