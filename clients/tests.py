<<<<<<< HEAD
import uuid
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from accounting.domain.payroll_rate import PayrollRateConfigurationError
from clients.models import HopDong, MucTieu, MucTieuDonGiaHistory


class MucTieuScopeManagerTest(TestCase):
    def setUp(self):
        self.org_id = settings.SCMD_ORGANIZATION_ID
        self.other_org_id = uuid.uuid4()

        self.hop_dong_same_org = HopDong.objects.create(
            so_hop_dong="HD-SCOPE-001",
            ngay_ky=timezone.now().date(),
            ngay_hieu_luc=timezone.now().date(),
            ngay_het_han=timezone.now().date(),
            gia_tri=1000000,
        )
        self.muc_tieu_same_org = MucTieu.objects.create(
            hop_dong=self.hop_dong_same_org,
            ten_muc_tieu="Muc tieu cung to chuc",
            dia_chi="Dia chi A",
        )

        self.hop_dong_other_org = HopDong.objects.create(
            so_hop_dong="HD-SCOPE-002",
            ngay_ky=timezone.now().date(),
            ngay_hieu_luc=timezone.now().date(),
            ngay_het_han=timezone.now().date(),
            gia_tri=2000000,
        )
        HopDong.objects.filter(pk=self.hop_dong_other_org.pk).update(
            tenant_id=self.other_org_id
        )
        self.hop_dong_other_org.refresh_from_db()
        self.muc_tieu_other_org = MucTieu.objects.create(
            hop_dong=self.hop_dong_other_org,
            ten_muc_tieu="Muc tieu khac to chuc",
            dia_chi="Dia chi B",
        )

    def test_for_tenant_uses_contract_scope_via_hop_dong(self):
        scoped_ids = set(
            MucTieu.objects.for_tenant(self.org_id).values_list("id", flat=True)
        )

        self.assertIn(self.muc_tieu_same_org.id, scoped_ids)
        self.assertNotIn(self.muc_tieu_other_org.id, scoped_ids)

    def test_for_tenant_rejects_cross_organization_id(self):
        self.assertFalse(MucTieu.objects.for_tenant(self.other_org_id).exists())


class MucTieuPayrollRateTest(TestCase):
    def setUp(self):
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-RATE-001",
            ngay_ky=timezone.now().date(),
            ngay_hieu_luc=timezone.now().date(),
            ngay_het_han=timezone.now().date(),
            gia_tri=1000000,
        )

    def test_get_don_gia_gio_thuc_te_uses_decimal_daily_hours(self):
        muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu 12h",
            dia_chi="Dia chi C",
            luong_khoan_bao_ve=Decimal("6000000"),
            so_gio_mot_ngay=Decimal("12.00"),
        )

        self.assertEqual(
            muc_tieu.get_don_gia_gio_thuc_te(3, 2025),
            Decimal("16129.0323"),
        )

    def test_get_don_gia_gio_thuc_te_supports_fractional_daily_hours(self):
        muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu 8.5h",
            dia_chi="Dia chi D",
            luong_khoan_bao_ve=Decimal("6000000"),
            so_gio_mot_ngay=Decimal("8.50"),
        )

        self.assertEqual(
            muc_tieu.get_don_gia_gio_thuc_te(3, 2025),
            Decimal("22770.3985"),
        )

    def test_get_payroll_rate_context_uses_effective_history_for_retroactive_rate(self):
        muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu retro",
            dia_chi="Dia chi E",
            luong_khoan_bao_ve=Decimal("9000000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=muc_tieu,
            ngay_hieu_luc=timezone.datetime(2025, 3, 1).date(),
            luong_khoan_bao_ve=Decimal("6000000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=muc_tieu,
            ngay_hieu_luc=timezone.datetime(2025, 3, 15).date(),
            luong_khoan_bao_ve=Decimal("9000000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )

        early_context = muc_tieu.get_payroll_rate_context(
            timezone.datetime(2025, 3, 10).date()
        )
        late_context = muc_tieu.get_payroll_rate_context(
            timezone.datetime(2025, 3, 20).date()
        )

        self.assertEqual(early_context["effective_date"].isoformat(), "2025-03-01")
        self.assertEqual(early_context["monthly_salary"], Decimal("6000000"))
        self.assertEqual(early_context["source"], "RATE_HISTORY")
        self.assertEqual(late_context["effective_date"].isoformat(), "2025-03-15")
        self.assertEqual(late_context["monthly_salary"], Decimal("9000000"))
        self.assertEqual(late_context["source"], "RATE_HISTORY")

    def test_get_payroll_rate_context_rejects_missing_baseline_before_first_history_row(self):
        muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu thieu baseline",
            dia_chi="Dia chi F",
            luong_khoan_bao_ve=Decimal("9000000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )
        MucTieuDonGiaHistory.objects.create(
            muc_tieu=muc_tieu,
            ngay_hieu_luc=timezone.datetime(2025, 3, 15).date(),
            luong_khoan_bao_ve=Decimal("9000000"),
            so_gio_mot_ngay=Decimal("8.00"),
        )

        with self.assertRaises(PayrollRateConfigurationError):
            muc_tieu.get_payroll_rate_context(timezone.datetime(2025, 3, 10).date())
=======
from django.test import TestCase

# Create your tests here.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
