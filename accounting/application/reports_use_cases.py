# -*- coding: utf-8 -*-
"""
Application Layer: Deduction Audit Use Case.
Description: Đối soát chênh lệch giữa Khấu trừ lương và Phiếu chi thực tế.
"""

import logging
from django.db.models import Sum, Q
from accounting.models import BangLuongThang, ChiTietLuong
from accounting.models_soquy import SoQuy
<<<<<<< HEAD
from main.decorators import application_audit_log
from main.models import AuditLog
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

logger = logging.getLogger(__name__)

class DeductionAuditUseCase:
    """
    Đối soát khoản 'Tạm ứng' (Advance) và 'Khấu trừ khác'.
    Kế hoạch: So sánh Sum(ChiTietLuong.ung_luong) vs Sum(SoQuy.so_tien WHERE hang_muc='TAM_UNG')
    """

    @staticmethod
<<<<<<< HEAD
    @application_audit_log(
        module="accounting",
        model_name="BangLuongThang",
        action=AuditLog.Action.EXECUTE,
        object_id_field="bang_luong_id"
    )
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def execute(bang_luong_id: int, tenant_id: str):
        try:
            # 1. Lấy thông tin bảng lương
            bl = BangLuongThang.objects.for_tenant(tenant_id).get(id=bang_luong_id)
            
            # 2. Tổng hợp Khấu trừ từ Bảng Lương (Payroll Side)
<<<<<<< HEAD
            payroll_deductions = ChiTietLuong.objects.for_tenant(tenant_id).filter(bang_luong=bl).values('nhan_vien_id').annotate(
=======
            payroll_deductions = ChiTietLuong.objects.filter(bang_luong=bl).values('nhan_vien_id').annotate(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                total_payroll_advance=Sum('ung_luong')
            )
            payroll_map = {item['nhan_vien_id']: item['total_payroll_advance'] for item in payroll_deductions}

            # 3. Tổng hợp Chi thực tế từ Sổ Quỹ (Cash Side)
<<<<<<< HEAD
            # Lọc các phiếu CHI - TAM_UNG trong tháng của kỳ lương - Bổ sung for_tenant() để đảm bảo Isolation
            cash_advances = SoQuy.objects.for_tenant(tenant_id).filter(
=======
            # Lọc các phiếu CHI - TAM_UNG trong tháng của kỳ lương
            cash_advances = SoQuy.objects.filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                loai_phieu='CHI',
                hang_muc='TAM_UNG',
                trang_thai='DA_DUYET',
                ngay_lap__year=bl.nam,
                ngay_lap__month=bl.thang
            ).values('nhan_vien_id').annotate(
                total_cash_disbursed=Sum('so_tien')
            )
            cash_map = {item['nhan_vien_id']: item['total_cash_disbursed'] for item in cash_advances}

            # 4. So khớp và tìm chênh lệch
            audit_results = []
            all_employee_ids = set(list(payroll_map.keys()) + list(cash_map.keys()))
            
            from users.models import NhanVien
<<<<<<< HEAD
            nhan_viens = {nv.id: nv for nv in NhanVien.objects.for_tenant(tenant_id).filter(id__in=all_employee_ids)}
=======
            nhan_viens = {nv.id: nv for nv in NhanVien.objects.filter(id__in=all_employee_ids)}
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

            for nv_id in all_employee_ids:
                payroll_val = payroll_map.get(nv_id, 0)
                cash_val = cash_map.get(nv_id, 0)
                diff = payroll_val - cash_val

                if diff != 0 or payroll_val > 0:
                    nv = nhan_viens.get(nv_id)
                    audit_results.append({
                        "nhan_vien": nv.ho_ten if nv else "N/A",
                        "ma_nv": nv.ma_nhan_vien if nv else "N/A",
                        "khau_tru_luong": float(payroll_val),
                        "thuc_chi_so_quy": float(cash_val),
                        "chenh_lech": float(diff),
                        "is_warning": diff != 0
                    })

            return {
                "status": "success",
                "bang_luong": bl.ten_bang_luong,
                "ky_luong": f"{bl.thang}/{bl.nam}",
                "data": audit_results,
                "summary": {
                    "total_variance": sum(r['chenh_lech'] for r in audit_results)
                }
            }
        except Exception as e:
            logger.error(f"DeductionAuditError: {str(e)}")
            return {"status": "error", "message": str(e)}