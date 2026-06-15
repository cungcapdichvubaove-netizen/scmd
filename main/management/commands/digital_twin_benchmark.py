"""Benchmark current Digital Twin data volume."""

from time import perf_counter

from django.core.management.base import BaseCommand

from accounting.models import BangLuongThang, ChiTietLuong
from clients.models import HopDong, KhachHangTiemNang, MucTieu
from inspection.models import DiemTuanTra, LoaiTuanTra, LuotTuanTra
from inventory.models import VatTu
from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc
from users.models import NhanVien


class Command(BaseCommand):
    help = "Print Digital Twin dataset coverage and simple ORM count benchmark."

    def handle(self, *args, **options):
        models = [
            NhanVien,
            KhachHangTiemNang,
            HopDong,
            MucTieu,
            VatTu,
            PhanCongCaTruc,
            ChamCong,
            BaoCaoSuCo,
            LoaiTuanTra,
            DiemTuanTra,
            LuotTuanTra,
            BangLuongThang,
            ChiTietLuong,
        ]
        start = perf_counter()
        for model in models:
            count = model.objects.count()
            self.stdout.write(f"{model._meta.label}: {count}")
        self.stdout.write(self.style.SUCCESS(f"Benchmark count pass in {perf_counter() - start:.3f}s"))
