"""Reset helpers for Digital Twin data.

Reset intentionally avoids deleting AuditLog because it is append-only by design.
Only deterministic Digital Twin records are removed; non-generated production or
manual QA data is left untouched.
"""

import shutil

from django.contrib.auth.models import User

from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from clients.models import CoHoiKinhDoanh, HopDong, KhachHangTiemNang, MucTieu, MucTieuDonGiaHistory
from inspection.models import DiemTuanTra, GhiNhanTuanTra, LoaiTuanTra, LuotTuanTra
from inventory.models import ChiTietPhieuNhap, ChiTietPhieuXuat, CongCuTaiMucTieu, LoaiVatTu, PhieuNhap, PhieuXuat, VatTu
from operations.models import BaoCaoSuCo, CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from seed.orchestrator.config import EXPORT_DIR
from users.models import BangCapChungChi, HocVan, LichSuCongTac, NhanVien


def reset_digital_twin_dataset(remove_exports=True):
    dt_users = User.objects.filter(username__startswith="dt_user_")
    dt_staff = NhanVien.objects.filter(user__in=dt_users)
    dt_contracts = HopDong.objects.filter(so_hop_dong__startswith="DT-HD-")
    dt_sites = MucTieu.objects.filter(ten_muc_tieu__startswith="DT-SITE-")
    dt_routes = LoaiTuanTra.objects.filter(ten_loai__startswith="DT-ROUTE-")
    dt_items = VatTu.objects.filter(ten_vat_tu__startswith="DT-SKU-")
    dt_receipts = PhieuNhap.objects.filter(ma_phieu__startswith="DT-PN-")
    dt_issues = PhieuXuat.objects.filter(ma_phieu__startswith="DT-PX-")

    GhiNhanTuanTra.objects.filter(luot_tuan_tra__loai_tuan_tra__in=dt_routes).delete()
    LuotTuanTra.objects.filter(loai_tuan_tra__in=dt_routes).delete()
    DiemTuanTra.objects.filter(loai_tuan_tra__in=dt_routes).delete()
    dt_routes.delete()

    ChamCong.objects.filter(ca_truc__nhan_vien__in=dt_staff).delete()
    BaoCaoSuCo.objects.filter(ma_su_co__startswith="DT-INC-").delete()
    PhanCongCaTruc.objects.filter(nhan_vien__in=dt_staff).delete()
    ViTriChot.objects.filter(muc_tieu__in=dt_sites).delete()

    ChiTietPhieuXuat.objects.filter(phieu_xuat__in=dt_issues).delete()
    ChiTietPhieuNhap.objects.filter(phieu_nhap__in=dt_receipts).delete()
    CongCuTaiMucTieu.objects.filter(muc_tieu__in=dt_sites).delete()
    dt_issues.delete()
    dt_receipts.delete()
    dt_items.delete()
    LoaiVatTu.objects.filter(ten_loai__startswith="DT - ").delete()

    ChiTietLuong.objects.filter(nhan_vien__in=dt_staff).delete()
    BangLuongThang.objects.filter(ten_bang_luong__startswith="Digital Twin payroll").delete()
    CauHinhLuong.objects.filter(nhan_vien__in=dt_staff).delete()

    MucTieuDonGiaHistory.objects.filter(muc_tieu__in=dt_sites).delete()
    dt_sites.delete()
    dt_contracts.delete()
    CoHoiKinhDoanh.objects.filter(ten_co_hoi__startswith="Gói dịch vụ bảo vệ").delete()
    KhachHangTiemNang.objects.filter(ten_cong_ty__contains="Digital Twin").delete()

    BangCapChungChi.objects.filter(nhan_vien__in=dt_staff).delete()
    HocVan.objects.filter(nhan_vien__in=dt_staff).delete()
    LichSuCongTac.objects.filter(nhan_vien__in=dt_staff).delete()
    dt_staff.delete()
    dt_users.delete()

    if remove_exports and EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
