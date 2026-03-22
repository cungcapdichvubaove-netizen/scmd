# file: accounting/services/payroll.py
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/services/payroll.py
Author: Mr. Anh
Created Date: 2025-12-02 (Updated 2025-12-04)
Description: Service xử lý logic tính toán chấm công và lương.
             - TimesheetCalculator: Tính toán chi tiết 1 ca (Legacy).
             - PayrollService: Tính toán tổng hợp lương tháng (New).
"""

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

# Import Models
from operations.models import ChamCong
from inspection.models import BienBanViPham
from accounting.models import BangLuongThang, ChiTietLuong, CauHinhLuong
from accounting.models_soquy import SoQuy
from users.models import NhanVien

class TimesheetCalculator:
    """
    Class chuyên dụng để tính toán số liệu từ một bản ghi Chấm công (Legacy).
    Giữ nguyên để không ảnh hưởng các chức năng cũ.
    """
    @staticmethod
    def analyze_shift(cham_cong: ChamCong):
        if not cham_cong.thoi_gian_check_in:
            return {'status': 'MISSING_IN', 'thuc_lam_gio': 0, 'di_muon_phut': 0, 've_som_phut': 0}

        ca_lam = cham_cong.ca_truc.ca_lam_viec
        ngay_truc = cham_cong.ca_truc.ngay_truc
        
        start_standard = datetime.combine(ngay_truc, ca_lam.gio_bat_dau)
        if ca_lam.gio_ket_thuc < ca_lam.gio_bat_dau:
            end_standard = datetime.combine(ngay_truc + timedelta(days=1), ca_lam.gio_ket_thuc)
        else:
            end_standard = datetime.combine(ngay_truc, ca_lam.gio_ket_thuc)

        if timezone.is_naive(start_standard): start_standard = timezone.make_aware(start_standard)
        if timezone.is_naive(end_standard): end_standard = timezone.make_aware(end_standard)

        check_in = cham_cong.thoi_gian_check_in
        check_out = cham_cong.thoi_gian_check_out
        
        di_muon_phut = 0
        if check_in > start_standard + timedelta(minutes=5):
            di_muon_phut = int((check_in - start_standard).total_seconds() / 60)

        ve_som_phut = 0
        thuc_lam_giay = 0
        if check_out:
            if check_out < end_standard - timedelta(minutes=5):
                ve_som_phut = int((end_standard - check_out).total_seconds() / 60)
            thuc_lam_giay = (check_out - check_in).total_seconds()
        
        return {
            'check_in': check_in, 'check_out': check_out,
            'thuc_lam_gio': round(thuc_lam_giay / 3600, 2),
            'di_muon_phut': di_muon_phut, 've_som_phut': ve_som_phut,
            'ghi_chu': cham_cong.ghi_chu
        }

# --- CLASS MỚI: TÍNH LƯƠNG TỰ ĐỘNG ---
class PayrollService:
    """Cỗ máy tính lương trung tâm"""

    @staticmethod
    def tinh_luong_thang(thang, nam):
        # 1. Khởi tạo bảng lương
        bang_luong, created = BangLuongThang.objects.get_or_create(
            thang=thang, nam=nam,
            defaults={'ten_bang_luong': f"Bảng lương tháng {thang}/{nam}"}
        )

        if bang_luong.trang_thai == 'DA_PHAT_HANH':
            return False, "Bảng lương đã phát hành, không thể tính lại!"

        # Xóa dữ liệu cũ của tháng này để tính lại (Reset)
        ChiTietLuong.objects.filter(bang_luong=bang_luong).delete()

        nhan_viens = NhanVien.objects.filter(trang_thai_lam_viec__in=['CHINHTHUC', 'THU_VIEC'])
        count = 0

        for nv in nhan_viens:
            # 2. Lấy Cấu hình Phụ cấp (Từ CauHinhLuong)
            try:
                config = nv.cau_hinh_luong
                # Tổng hợp các loại phụ cấp vào field 'phu_cap_khac'
                tong_phu_cap = config.phu_cap_trach_nhiem + config.phu_cap_xang_xe + config.phu_cap_an_uong
            except:
                tong_phu_cap = Decimal(0)

            # 3. TÍNH LƯƠNG CHÍNH (Logic Đa Mục Tiêu)
            # Lấy tất cả ca đã hoàn thành trong tháng
            cham_congs = ChamCong.objects.filter(
                ca_truc__nhan_vien=nv,
                thoi_gian_check_in__month=thang,
                thoi_gian_check_in__year=nam,
                thoi_gian_check_out__isnull=False
            ).select_related('ca_truc__vi_tri_chot__muc_tieu')
            
            tong_gio_lam_thang = 0.0
            tong_luong_chinh = Decimal(0)
            
            for cc in cham_congs:
                duration_seconds = (cc.thoi_gian_check_out - cc.thoi_gian_check_in).total_seconds()
                gio_lam_ca = round(duration_seconds / 3600, 2)
                
                if gio_lam_ca > 0:
                    # Lấy đơn giá từ Mục tiêu
                    muc_tieu = cc.ca_truc.vi_tri_chot.muc_tieu
                    don_gia_muc_tieu = Decimal(0)
                    
                    # Gọi hàm tính giá có sẵn trong model MucTieu (clients app)
                    if muc_tieu:
                        val = muc_tieu.get_don_gia_gio_thuc_te(thang, nam)
                        don_gia_muc_tieu = Decimal(str(val)) if val else Decimal(0)
                    
                    tien_ca_nay = Decimal(gio_lam_ca) * don_gia_muc_tieu
                    
                    tong_gio_lam_thang += gio_lam_ca
                    tong_luong_chinh += tien_ca_nay

            # 4. Tính Tiền Phạt (Từ Inspection)
            phat_vi_pham = BienBanViPham.objects.filter(
                doi_tuong_vi_pham=nv,
                created_at__month=thang,
                created_at__year=nam,
                trang_thai='DA_DUYET'
            ).aggregate(Sum('so_tien_phat'))['so_tien_phat__sum'] or 0

            # 5. Tính Tạm Ứng (Từ SoQuy)
            tam_ung = SoQuy.objects.filter(
                nhan_vien=nv,
                loai_phieu='CHI',
                hang_muc='TAM_UNG',
                ngay_lap__month=thang,
                ngay_lap__year=nam,
                trang_thai='DA_DUYET'
            ).aggregate(Sum('so_tien'))['so_tien__sum'] or 0

            # 6. Lưu kết quả vào ChiTietLuong (Chỉ tạo nếu có dữ liệu)
            if tong_gio_lam_thang > 0 or tam_ung > 0 or phat_vi_pham > 0 or tong_phu_cap > 0:
                ChiTietLuong.objects.create(
                    bang_luong=bang_luong,
                    nhan_vien=nv,
                    tong_gio_lam=tong_gio_lam_thang,
                    luong_chinh=tong_luong_chinh,
                    phu_cap_khac=tong_phu_cap, # Đổ phụ cấp vào đây
                    phat_vi_pham=phat_vi_pham,
                    ung_luong=tam_ung
                )
                count += 1

        # Cập nhật tổng quan bảng lương
        tong_ket = ChiTietLuong.objects.filter(bang_luong=bang_luong).aggregate(
            Sum('thuc_lanh'), Sum('tong_gio_lam')
        )
        bang_luong.tong_chi_tra = tong_ket['thuc_lanh__sum'] or 0
        bang_luong.tong_gio_cong = tong_ket['tong_gio_lam__sum'] or 0
        bang_luong.save()

        return True, f"Đã tính lương thành công cho {count} nhân viên."