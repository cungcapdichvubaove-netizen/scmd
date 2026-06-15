# -*- coding: utf-8 -*-
from django.utils import timezone
from ..models import PhanCongCaTruc

class GetAttendanceHistoryUseCase:
    """
    Application Layer: Lấy lịch sử chấm công của nhân viên.
    Dữ liệu chấm công là dữ liệu kiểm toán nhạy cảm (Rule 5).
    """
    @staticmethod
    def execute(nhan_vien, month=None, year=None):
        today = timezone.now().date()
        if month and year:
            start_date = today.replace(year=int(year), month=int(month), day=1)
        else:
            start_date = today.replace(day=1)
        
        lich_su = PhanCongCaTruc.objects.filter(
            nhan_vien=nhan_vien,
            ngay_truc__range=[start_date, today]
        ).select_related(
            'ca_lam_viec', 
            'vi_tri_chot__muc_tieu', 
            'chamcong'
        ).order_by('-ngay_truc')
        
        return {
            'lich_su': lich_su,
            'tong_cong': lich_su.filter(chamcong__thoi_gian_check_out__isnull=False).count(),
            'month': start_date.month,
            'year': start_date.year
        }