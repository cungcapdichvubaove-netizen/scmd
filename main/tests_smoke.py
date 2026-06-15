# -*- coding: utf-8 -*-
"""
SCMD Pro - High-Level Smoke Tests
---------------------------------
Kiểm thử các luồng nghiệp vụ quan trọng trước khi phát hành:
- Login (Branding & UTF-8)
- Dashboards (Operations Cockpit & Accounting Dashboard)
- Technical Console (Admin)
- Mobile Attendance (Dashboard & API)
- Export (Audit Trail & Permissions)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

from main.models import AuditLog
from users.models import NhanVien
from clients.models import HopDong
from operations.models import CaLamViec, PhanCongCaTruc, MucTieu, ViTriChot
from accounting.models import BangLuongThang, ChiTietLuong

class SCMDProSmokeTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.client = Client()
        
        # 1. Thiết lập Superuser để kiểm tra Dashboard và Export
        self.admin_user = User.objects.create_superuser(
            username='smoke_admin', 
            email='admin@scmd.vn', 
            password='password123'
        )
        
        # 2. Thiết lập Nhân viên để kiểm tra Mobile Dashboard
        self.nv = NhanVien.objects.create(
            ho_ten="Nguyễn Văn Smoke",
            ma_nhan_vien="NV_SMOKE",
            tenant_id=self.tenant_id,
            trang_thai_lam_viec="CHINHTHUC"
        )
        self.nv_user = User.objects.create_user(username='nv_smoke', password='password123')
        self.nv.user = self.nv_user
        self.nv.save()

        # 3. Thiết lập hạ tầng vận hành mẫu
        self.hd = HopDong.objects.create(so_hop_dong="HD-SMOKE", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd, ten_muc_tieu="Mục tiêu Smoke Test", 
            tenant_id=self.tenant_id, vi_do=10.762622, kinh_do=106.660172
        )
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Chốt Chính", tenant_id=self.tenant_id)
        self.ca = CaLamViec.objects.create(
            ten_ca="Ca 12h", gio_bat_dau="06:00", gio_ket_thuc="18:00", tenant_id=self.tenant_id
        )
        
        # 4. Thiết lập dữ liệu kế toán mẫu
        self.bl = BangLuongThang.objects.create(
            thang=6, nam=2026, tenant_id=self.tenant_id,
            trang_thai=BangLuongThang.TrangThai.LOCKED
        )

    def test_login_surface_and_branding(self):
        """QA Login: Kiểm tra tên thương hiệu SCMD Pro và tiếng Việt chuẩn (Rule 10.1)."""
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        self.assertIn("SCMD Pro", content)
        self.assertIn("Phần mềm chỉ huy và quản trị", content)
        self.assertIn("Tài khoản", content) # Kiểm tra UTF-8

    def test_dashboards_access_and_scoping(self):
        """QA Dashboards: Kiểm tra khả năng truy cập Cockpit và Accounting Dashboard."""
        self.client.login(username='smoke_admin', password='password123')
        
        # Bảng điều hành vận hành
        response = self.client.get(reverse('operations:dashboard_vanhanh'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bảng điều hành vận hành", response.content.decode('utf-8'))
        
        # Dashboard Kế toán
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tháng này", response.content.decode('utf-8'))

    def test_admin_branding_and_access(self):
        """QA Admin: Kiểm tra tiêu đề Technical Console."""
        self.client.login(username='smoke_admin', password='password123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("Quản trị kỹ thuật SCMD", response.content.decode('utf-8'))

    def test_mobile_attendance_dashboard_smoke(self):
        """QA Mobile: Kiểm tra dashboard nhân viên hiện trường."""
        self.client.login(username='nv_smoke', password='password123')
        response = self.client.get(reverse('operations:mobile_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Lịch trực hôm nay", response.content.decode('utf-8'))

    def test_export_and_audit_smoke(self):
        """QA Export: Kiểm tra xuất file Excel và ghi Audit Log đối soát (Rule 8.2)."""
        self.client.login(username='smoke_admin', password='password123')
        
        url = reverse('accounting:export_doi_soat_khau_tru_excel', args=[self.bl.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        # Kiểm tra Audit Log phát sinh
        audit_exists = AuditLog.objects.filter(
            model_name="BangLuongThang",
            object_id=str(self.bl.pk),
            note__icontains="Export Excel"
        ).exists()
        self.assertTrue(audit_exists, "Mọi hành động xuất dữ liệu nhạy cảm phải được ghi log.")

    def test_notification_infrastructure_smoke(self):
        """QA Notifications: Kiểm tra hạ tầng thông báo qua context processor."""
        self.client.login(username='nv_smoke', password='password123')
        # Truy cập một trang bất kỳ có nạp notification_context
        response = self.client.get(reverse('operations:mobile_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Kiểm tra sự hiện diện của biến context từ notification_context
        self.assertIn('notifications_count', response.context)

    def test_notification_infrastructure_smoke(self):
        """QA Notifications: Kiểm tra hạ tầng thông báo qua context processor."""
        self.client.login(username='nv_smoke', password='password123')
        # Truy cập một trang bất kỳ có nạp notification_context
        response = self.client.get(reverse('operations:mobile_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Kiểm tra sự hiện diện của biến context từ notification_context
        self.assertIn('notifications_count', response.context)