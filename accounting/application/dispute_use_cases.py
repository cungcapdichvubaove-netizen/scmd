# -*- coding: utf-8 -*-
from django.db import transaction
from django.core.exceptions import PermissionDenied
from accounting.models import ChiTietLuong, PhanHoiLuong

class CreateDisputeUseCase:
    """
    Application Layer: Logic tạo khiếu nại lương.
    Ràng buộc:
    1. Nhân viên chỉ được khiếu nại phiếu lương của chính mình.
    2. Chỉ được khiếu nại khi bảng lương đã ở trạng thái 'DA_PHAT_HANH'.
    3. Không được gửi quá nhiều khiếu nại 'MOI' cho cùng một phiếu lương.
    """
    
    @staticmethod
    def execute(user_nhan_vien, chi_tiet_luong_id: int, noi_dung: str, tenant_id):
        try:
            # 1. Lấy phiếu lương và kiểm tra quyền sở hữu
            chi_tiet = ChiTietLuong.objects.get(id=chi_tiet_luong_id, tenant_id=tenant_id)
            
            if chi_tiet.nhan_vien != user_nhan_vien:
                raise PermissionDenied("Bạn không có quyền khiếu nại phiếu lương này.")
                
            # 2. Kiểm tra trạng thái bảng lương
            if chi_tiet.bang_luong.trang_thai != 'DA_PHAT_HANH':
                return False, "Bảng lương chưa được phát hành chính thức, vui lòng đợi."

            # 3. Kiểm tra spam (đã có phản hồi đang chờ xử lý)
            has_pending = PhanHoiLuong.objects.filter(
                chi_tiet_luong=chi_tiet,
                trang_thai__in=['MOI', 'DANG_XU_LY']
            ).exists()
            
            if has_pending:
                return False, "Bạn đã có một khiếu nại đang được xử lý cho kỳ lương này."

            # 4. Tạo phản hồi
            with transaction.atomic():
                phan_hoi = PhanHoiLuong.objects.create(
                    tenant_id=tenant_id,
                    chi_tiet_luong=chi_tiet,
                    nhan_vien=user_nhan_vien,
                    noi_dung=noi_dung,
                    trang_thai='MOI'
                )
                return True, "Gửi phản hồi thành công. Kế toán sẽ xem xét và trả lời bạn sớm nhất."

        except ChiTietLuong.DoesNotExist:
            return False, "Không tìm thấy dữ liệu phiếu lương."
        except Exception as e:
            return False, str(e)