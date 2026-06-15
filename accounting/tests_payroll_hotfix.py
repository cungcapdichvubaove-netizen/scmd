# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
<<<<<<< HEAD
from unittest.mock import MagicMock, patch

from django.conf import settings
=======
from unittest.mock import patch

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.test import TestCase
from django.utils import timezone

from accounting.application.payroll_use_cases import CalculatePayrollUseCase
<<<<<<< HEAD
from accounting.domain.payroll_rate import PayrollRateConfigurationError, calculate_hourly_rate
from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong, KhoanKhauTruNhanVien
from accounting.models_soquy import SoQuy
from accounting.services.payroll import PayrollService
from accounting.tasks import accounting_calculate_monthly_payroll
from clients.models import HopDong, MucTieu, MucTieuDonGiaHistory
=======
from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from accounting.models_soquy import SoQuy
from accounting.services.payroll import PayrollService
from clients.models import HopDong, MucTieu
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot, BaoCaoSuCo
from users.models import NhanVien


class PayrollHotfixTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.today = today
<<<<<<< HEAD
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        self.nhan_vien = NhanVien.objects.create(
            ma_nhan_vien="PAY001",
            ho_ten="Nhan vien Payroll",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec="CHINHTHUC",
            sdt_chinh="+84999999999",
<<<<<<< HEAD
            tenant_id=self.tenant_id
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        CauHinhLuong.objects.create(
            nhan_vien=self.nhan_vien,
            phu_cap_trach_nhiem=500000,
            phu_cap_xang_xe=200000,
            phu_cap_an_uong=300000,
        )
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-PAY-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
<<<<<<< HEAD
            tenant_id=self.tenant_id
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu Payroll",
            dia_chi="Dia chi test",
            sdt_lien_he="0123",
            luong_khoan_bao_ve=7200000,
            so_gio_mot_ngay=8,
<<<<<<< HEAD
            # Most payroll hotfix tests assert base wage/allowance/deduction
            # behavior; they opt out of attendance incentive unless explicitly
            # testing the incentive contract.
            tien_chuyen_can=0,
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Cong chinh",
<<<<<<< HEAD
            tenant_id=self.tenant_id
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca A",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
<<<<<<< HEAD
            tenant_id=self.tenant_id
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        self.bang_luong = BangLuongThang.objects.create(
            ten_bang_luong=f"Bang luong {today.month}/{today.year}",
            thang=today.month,
            nam=today.year,
<<<<<<< HEAD
            tenant_id=self.tenant_id
        )

    def _create_attendance(self, hours, day=None):
        ngay_truc = day or self.today
=======
        )

    def _create_attendance(self, hours):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
<<<<<<< HEAD
            ngay_truc=ngay_truc,
            tenant_id=self.tenant_id
=======
            ngay_truc=self.today,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )
        return ChamCong.objects.create(
            ca_truc=phan_cong,
            thoi_gian_check_in=timezone.make_aware(
<<<<<<< HEAD
                datetime.combine(ngay_truc, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(ngay_truc, datetime.strptime("14:00", "%H:%M").time())
            ),
            thuc_lam_gio=hours,
            tenant_id=self.tenant_id
=======
                datetime.combine(self.today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("14:00", "%H:%M").time())
            ),
            thuc_lam_gio=hours,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )

    def test_calculate_payroll_maps_to_current_model_fields(self):
        self._create_attendance(8)

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.tong_gio_lam, 8.0)
        self.assertEqual(phieu.luong_chinh, Decimal("240000"))
        self.assertEqual(phieu.phu_cap_khac, Decimal("1000000"))
        self.assertEqual(phieu.tong_phu_cap, Decimal("1000000"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1240000"))
<<<<<<< HEAD
        self.assertEqual(phieu.nguon_du_lieu_snapshot["attendance_count"], 1)
        self.assertEqual(Decimal(str(phieu.nguon_du_lieu_snapshot["attendance"][0]["gio_lam"])), Decimal("8.0"))
        self.assertEqual(
            phieu.nguon_du_lieu_snapshot["attendance"][0]["don_gia_hieu_luc_tu"],
            self.hop_dong.ngay_hieu_luc.isoformat(),
        )

    def test_calculate_payroll_snapshots_effective_date_for_retroactive_rate_change(self):
        first_day = self.today.replace(day=1)
        second_half_day = self.today.replace(day=15)
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.muc_tieu,
            ngay_hieu_luc=first_day,
            luong_khoan_bao_ve=Decimal("6200000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.muc_tieu,
            ngay_hieu_luc=second_half_day,
            luong_khoan_bao_ve=Decimal("9300000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        self._create_attendance(8, day=first_day)
        self._create_attendance(8, day=second_half_day)

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        attendance_snapshot = phieu.nguon_du_lieu_snapshot["attendance"]
        self.assertEqual(attendance_snapshot[0]["don_gia_hieu_luc_tu"], first_day.isoformat())
        self.assertEqual(attendance_snapshot[1]["don_gia_hieu_luc_tu"], second_half_day.isoformat())
        self.assertEqual(attendance_snapshot[0]["nguon_don_gia"], "RATE_HISTORY")
        self.assertEqual(attendance_snapshot[1]["nguon_don_gia"], "RATE_HISTORY")
        self.assertEqual(
            Decimal(attendance_snapshot[0]["luong_khoan_bao_ve_thang"]),
            Decimal("6200000"),
        )
        self.assertEqual(
            Decimal(attendance_snapshot[1]["luong_khoan_bao_ve_thang"]),
            Decimal("9300000"),
        )
        expected_early = (
            calculate_hourly_rate(
                monthly_salary=Decimal("6200000"),
                standard_hours_per_day=Decimal("8.00"),
                month=first_day.month,
                year=first_day.year,
            )
            * Decimal("8")
        )
        expected_late = (
            calculate_hourly_rate(
                monthly_salary=Decimal("9300000"),
                standard_hours_per_day=Decimal("8.00"),
                month=second_half_day.month,
                year=second_half_day.year,
            )
            * Decimal("8")
        )
        self.assertEqual(
            phieu.luong_chinh,
            ChiTietLuong.to_decimal_safe(expected_early + expected_late),
        )

    def test_calculate_payroll_rejects_history_without_baseline_before_work_date(self):
        first_day = self.today.replace(day=1)
        later_day = self.today.replace(day=15)
        if first_day == later_day:
            later_day = self.today.replace(day=2)
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.muc_tieu,
            ngay_hieu_luc=later_day,
            luong_khoan_bao_ve=Decimal("9300000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        self._create_attendance(8, day=first_day)

        with self.assertRaisesMessage(
            PayrollRateConfigurationError,
            "baseline đơn giá hiệu lực",
        ):
            CalculatePayrollUseCase.execute(
                nhan_vien=self.nhan_vien,
                bang_luong=self.bang_luong,
                tenant_id=self.bang_luong.tenant_id,
            )

    def test_retroactive_rate_snapshot_includes_rate_record_identity(self):
        work_day = self.today.replace(day=1)
        rate = MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.muc_tieu,
            ngay_hieu_luc=work_day,
            luong_khoan_bao_ve=Decimal("9300000"),
            so_gio_mot_ngay=Decimal("8.00"),
            ghi_chu="Dieu chinh hoi to co doi soat",
        )
        self._create_attendance(8, day=work_day)

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        attendance_snapshot = phieu.nguon_du_lieu_snapshot["attendance"][0]
        self.assertEqual(attendance_snapshot["nguon_don_gia"], "RATE_HISTORY")
        self.assertEqual(attendance_snapshot["rate_record_id"], rate.id)
        self.assertEqual(
            attendance_snapshot["don_gia_hieu_luc_tu"],
            work_day.isoformat(),
        )

    def test_calculate_payroll_does_not_deduct_incident_field_without_approved_deduction_record(self):
=======

    def test_calculate_payroll_collects_current_deduction_sources(self):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        self._create_attendance(10)
        BienBanViPham.objects.create(
            doi_tuong_vi_pham=self.nhan_vien,
            muc_tieu=self.muc_tieu,
            hinh_thuc_xu_ly="PHAT_TIEN",
            so_tien_phat=50000,
            trang_thai="DA_DUYET",
            ngay_vi_pham=timezone.now(),
        )
        SoQuy.objects.create(
            ma_phieu="SQ-PAY-001",
            loai_phieu="CHI",
            hang_muc="TAM_UNG",
            so_tien=100000,
            ngay_lap=timezone.now(),
            nhan_vien=self.nhan_vien,
            dien_giai="Tam ung test",
            trang_thai="DA_DUYET",
        )
        PhieuXuat.objects.create(
            ma_phieu="PX-PAY-001",
            loai_xuat="BAN_TRU_LUONG",
            ngay_xuat=timezone.now(),
            nhan_vien_nhan=self.nhan_vien,
            ghi_chu="Dong phuc",
            tong_tien_phai_thu=50000,
            trang_thai_thanh_toan="CHUA_TRU",
        )
        BaoCaoSuCo.objects.create(
            tieu_de="Su co test",
            muc_tieu=self.muc_tieu,
            nhan_vien_bao_cao=self.nhan_vien,
            nhan_vien_co_loi=self.nhan_vien,
            thoi_gian_phat_hien=timezone.now(),
            trang_thai="CHO_DEN_BU",
            phai_thu_nhan_vien=75000,
        )

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.luong_chinh, Decimal("300000"))
        self.assertEqual(phieu.phat_vi_pham, Decimal("50000"))
        self.assertEqual(phieu.ung_luong, Decimal("100000"))
        self.assertEqual(phieu.tien_dong_phuc, Decimal("50000"))
<<<<<<< HEAD
        self.assertEqual(phieu.tien_den_bu, Decimal("0"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1100000"))

    def test_calculate_payroll_uses_approved_incident_deduction_without_double_counting_incident_field(self):
        self._create_attendance(10)
        BaoCaoSuCo.objects.create(
            tieu_de="Su co co khoan khau tru",
            muc_tieu=self.muc_tieu,
            nhan_vien_bao_cao=self.nhan_vien,
            nhan_vien_co_loi=self.nhan_vien,
            thoi_gian_phat_hien=timezone.now(),
            trang_thai="HOAN_TAT",
            phai_thu_nhan_vien=75000,
        )
        KhoanKhauTruNhanVien.objects.create(
            nhan_vien=self.nhan_vien,
            so_chung_tu="KKT-PAY-001",
            loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.DEN_BU,
            bang_luong_du_kien=self.bang_luong,
            ngay_ap_dung=timezone.localdate(),
            so_tien=75000,
            trang_thai=KhoanKhauTruNhanVien.TrangThai.APPROVED,
            tenant_id=self.tenant_id,
        )

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.tien_den_bu, Decimal("75000"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1225000"))
=======
        self.assertEqual(phieu.tien_den_bu, Decimal("75000"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1025000"))
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    @patch("accounting.services.payroll.AuditPayrollUseCase.execute")
    def test_payroll_service_degrades_cleanly_when_audit_fails(self, mock_audit):
        mock_audit.return_value = {"status": "error", "message": "audit unavailable"}
        self._create_attendance(8)

        success, message = PayrollService.tinh_luong_thang(
            self.today.month,
            self.today.year,
        )

        self.assertTrue(success)
        self.assertIn("hau kiem payroll chua chay duoc", message.lower())
        self.assertTrue(
            ChiTietLuong.objects.filter(
                bang_luong__thang=self.today.month,
                bang_luong__nam=self.today.year,
                nhan_vien=self.nhan_vien,
            ).exists()
        )
<<<<<<< HEAD

    def test_calculate_payroll_rejects_locked_period(self):
        self._create_attendance(8)
        self.bang_luong.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.bang_luong.save(update_fields=["trang_thai"])

        with self.assertRaisesMessage(ValueError, "Không thể tính lại kỳ lương"):
            CalculatePayrollUseCase.execute(
                nhan_vien=self.nhan_vien,
                bang_luong=self.bang_luong,
                tenant_id=self.bang_luong.tenant_id,
            )

    def test_build_batch_context_aggregates_attendance_per_employee(self):
        other_nv = NhanVien.objects.create(
            ma_nhan_vien="PAY002",
            ho_ten="Nhan vien Payroll 2",
            ngay_sinh="1991-01-01",
            trang_thai_lam_viec="CHINHTHUC",
            sdt_chinh="+84999999998",
        )
        self._create_attendance(8)

        other_phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=other_nv,
            ca_lam_viec=self.ca_lam,
            ngay_truc=self.today,
        )
        ChamCong.objects.create(
            ca_truc=other_phan_cong,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("12:00", "%H:%M").time())
            ),
            thuc_lam_gio=6,
        )

        batch_context = CalculatePayrollUseCase.build_batch_context(
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
            nhan_vien_ids=[self.nhan_vien.id, other_nv.id],
        )

        self.assertEqual(
            batch_context["attendance_count_by_employee"][self.nhan_vien.id], 1
        )
        self.assertEqual(
            batch_context["attendance_count_by_employee"][other_nv.id], 1
        )
        self.assertEqual(
            batch_context["base_salary_by_employee"][self.nhan_vien.id],
            Decimal("240000"),
        )
        self.assertEqual(
            batch_context["base_salary_by_employee"][other_nv.id],
            Decimal("180000"),
        )

    def test_attendance_incentive_uses_distinct_assigned_work_days_instead_of_calendar_days(self):
        self.muc_tieu.tien_chuyen_can = Decimal("1000000")
        self.muc_tieu.save(update_fields=["tien_chuyen_can"])
        second_day = self.today.replace(day=1) if self.today.day != 1 else self.today.replace(day=2)
        first_assignment = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=self.today,
        )
        second_assignment = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=second_day,
        )
        ChamCong.objects.create(
            ca_truc=first_assignment,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("14:00", "%H:%M").time())
            ),
            thuc_lam_gio=8,
        )

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.thuong_chuyen_can, Decimal("600000"))
        self.assertEqual(
            phieu.nguon_du_lieu_snapshot["chuyen_can"]["expected_work_days"],
            2,
        )
        self.assertEqual(
            phieu.nguon_du_lieu_snapshot["chuyen_can"]["actual_work_days"],
            1,
        )
        self.assertEqual(
            phieu.nguon_du_lieu_snapshot["chuyen_can"]["attendance_record_count"],
            1,
        )
        self.assertEqual(
            phieu.nguon_du_lieu_snapshot["chuyen_can"]["absent_days"],
            1,
        )

    def test_payroll_service_returns_configuration_error_for_invalid_standard_hours(self):
        self.muc_tieu.so_gio_mot_ngay = 0
        self.muc_tieu.save(update_fields=["so_gio_mot_ngay"])
        self._create_attendance(8)

        success, message = PayrollService.tinh_luong_thang(
            self.today.month,
            self.today.year,
        )

        self.assertFalse(success)
        self.assertIn("Tổng giờ chuẩn phải lớn hơn 0.", message)

    def test_calculate_payroll_use_case_surfaces_payroll_rate_configuration_error(self):
        self.muc_tieu.so_gio_mot_ngay = 0
        self.muc_tieu.save(update_fields=["so_gio_mot_ngay"])
        self._create_attendance(8)

        with self.assertRaises(PayrollRateConfigurationError):
            CalculatePayrollUseCase.execute(
                nhan_vien=self.nhan_vien,
                bang_luong=self.bang_luong,
                tenant_id=self.bang_luong.tenant_id,
            )

    @patch("accounting.tasks.PayrollService.tinh_luong_thang")
    @patch("accounting.tasks.timezone.now")
    def test_monthly_payroll_task_does_not_retry_locked_period(self, mock_now, mock_service):
        mock_now.return_value = timezone.make_aware(datetime(2026, 6, 1, 1, 0, 0))
        mock_service.return_value = (False, "Bang luong thang 5/2026 da khoa so.")
        mock_task = MagicMock()

        with patch.object(accounting_calculate_monthly_payroll, "retry") as mock_retry:
            result = accounting_calculate_monthly_payroll.run()

        self.assertEqual(result, "Bang luong thang 5/2026 da khoa so.")
        mock_retry.assert_not_called()

    def test_payroll_service_can_scope_benchmark_employees(self):
        other_nv = NhanVien.objects.create(
            ma_nhan_vien="PAY003",
            ho_ten="Nhan vien ngoai pham vi",
            ngay_sinh="1992-01-01",
            trang_thai_lam_viec="CHINHTHUC",
            sdt_chinh="+84999999997",
        )
        self._create_attendance(8)

        success, message = PayrollService.tinh_luong_thang(
            self.today.month,
            self.today.year,
            nhan_vien_queryset=NhanVien.objects.filter(id=self.nhan_vien.id),
            batch_size=1,
        )

        self.assertTrue(success, message)
        self.assertTrue(
            ChiTietLuong.objects.filter(
                bang_luong__thang=self.today.month,
                bang_luong__nam=self.today.year,
                nhan_vien=self.nhan_vien,
            ).exists()
        )
        self.assertFalse(
            ChiTietLuong.objects.filter(
                bang_luong__thang=self.today.month,
                bang_luong__nam=self.today.year,
                nhan_vien=other_nv,
            ).exists()
        )

    def test_payroll_service_includes_probation_employee_from_status_ssot(self):
        self.nhan_vien.trang_thai_lam_viec = NhanVien.TrangThaiLamViec.THU_VIEC
        self.nhan_vien.save(update_fields=["trang_thai_lam_viec"])
        self._create_attendance(8)

        success, message = PayrollService.tinh_luong_thang(
            self.today.month,
            self.today.year,
        )

        self.assertTrue(success, message)
        self.assertTrue(
            ChiTietLuong.objects.filter(
                bang_luong__thang=self.today.month,
                bang_luong__nam=self.today.year,
                nhan_vien=self.nhan_vien,
            ).exists()
        )
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
