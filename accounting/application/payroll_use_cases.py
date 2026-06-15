# -*- coding: utf-8 -*-
"""
Application Layer: Payroll Use Cases.
"""

import logging
from decimal import Decimal
<<<<<<< HEAD
from typing import TYPE_CHECKING, cast

from django.conf import settings
from django.db import transaction

from accounting.services.payroll_calculation import PayrollCalculationService
from main.decorators import application_audit_log
from main.models import AuditLog
from accounting.models import BangLuongThang, ChiTietLuong

if TYPE_CHECKING:
    from core.managers import TenantAwareManager
=======

from django.db import transaction
from django.db.models import Sum

from main.decorators import application_audit_log
from main.models import AuditLog
from accounting.models import BangLuongThang, ChiTietLuong
from accounting.models_soquy import SoQuy
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from operations.models import BaoCaoSuCo, ChamCong
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

logger = logging.getLogger(__name__)


class CalculatePayrollUseCase:
    """
    Hotfix SSOT for payroll calculation.
    """

    @staticmethod
<<<<<<< HEAD
    def build_batch_context(bang_luong, tenant_id, nhan_vien_ids):
        return PayrollCalculationService.build_batch_context(
            bang_luong=bang_luong,
            tenant_id=tenant_id,
            nhan_vien_ids=nhan_vien_ids,
        )

    @staticmethod
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    @application_audit_log(
        module="accounting",
        model_name="ChiTietLuong",
        action=AuditLog.Action.EXECUTE,
    )
<<<<<<< HEAD
    def execute(nhan_vien, bang_luong, tenant_id, batch_context=None, **kwargs):
        with transaction.atomic():
            tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
            bang_luong = (
                BangLuongThang.objects
                .for_tenant(tenant_id)
                .select_for_update()
                .get(pk=bang_luong.pk)
            )
            if not bang_luong.can_recalculate():
                raise ValueError(
                    f"Không thể tính lại kỳ lương {bang_luong.thang}/{bang_luong.nam} khi đã ở trạng thái {bang_luong.trang_thai}."
                )

            thang = bang_luong.thang
            nam = bang_luong.nam

            if batch_context is None:
                batch_context = CalculatePayrollUseCase.build_batch_context(
                    bang_luong=bang_luong,
                    tenant_id=tenant_id,
                    nhan_vien_ids=[nhan_vien.id],
                )

            calculation = PayrollCalculationService.calculate_detail(
                nhan_vien=nhan_vien,
                batch_context=batch_context,
            )

            chi_tiet_mgr = cast("TenantAwareManager", ChiTietLuong.objects).for_tenant(tenant_id)
            existing = chi_tiet_mgr.filter(bang_luong=bang_luong, nhan_vien=nhan_vien).first()
            snapshot = dict(calculation["snapshot"])
            existing_phase_c = None
            if existing and isinstance(existing.nguon_du_lieu_snapshot, dict):
                existing_phase_c = existing.nguon_du_lieu_snapshot.get("phase_c_reconciliation")
            if existing_phase_c:
                snapshot["phase_c_reconciliation"] = existing_phase_c
                snapshot["phase_d_reconciliation_status"] = {
                    "status": "NEEDS_RECONCILIATION",
                    "reason": "PAYROLL_RECALCULATED_AFTER_PHASE_C_SOURCE_RECONCILIATION",
                    "message": "CalculatePayrollUseCase preserved source reconciliation data but marked it stale; run PayrollSourceReconciliationUseCase before review/lock.",
                }

            chi_tiet, _ = chi_tiet_mgr.update_or_create(
=======
    def execute(nhan_vien, bang_luong, tenant_id, **kwargs):
        with transaction.atomic():
            thang = bang_luong.thang
            nam = bang_luong.nam

            attendance_qs = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__nhan_vien=nhan_vien,
                    thoi_gian_check_in__year=nam,
                    thoi_gian_check_in__month=thang,
                    thoi_gian_check_in__isnull=False,
                )
                .select_related("ca_truc__vi_tri_chot__muc_tieu")
            )

            tong_gio_lam = Decimal("0")
            luong_chinh = Decimal("0")
            for cham_cong in attendance_qs:
                gio_lam = Decimal(str(cham_cong.thuc_lam_gio or 0))
                muc_tieu = cham_cong.ca_truc.vi_tri_chot.muc_tieu
                don_gia_gio = Decimal(
                    str(muc_tieu.get_don_gia_gio_thuc_te(thang, nam) or 0)
                )

                tong_gio_lam += gio_lam
                luong_chinh += gio_lam * don_gia_gio

            salary_config = getattr(nhan_vien, "cau_hinh_luong", None)
            phu_cap_khac = Decimal("0")
            if salary_config:
                phu_cap_khac = (
                    ChiTietLuong.to_decimal_safe(salary_config.phu_cap_trach_nhiem)
                    + ChiTietLuong.to_decimal_safe(salary_config.phu_cap_xang_xe)
                    + ChiTietLuong.to_decimal_safe(salary_config.phu_cap_an_uong)
                )

            thuong_chuyen_can = Decimal("0")

            fines_data = BienBanViPham.objects.filter(
                doi_tuong_vi_pham=nhan_vien,
                ngay_vi_pham__month=thang,
                ngay_vi_pham__year=nam,
                trang_thai="DA_DUYET",
            ).aggregate(total_fines=Sum("so_tien_phat"))
            phat_vi_pham = ChiTietLuong.to_decimal_safe(fines_data.get("total_fines"))

            inventory_data = PhieuXuat.objects.filter(
                nhan_vien_nhan=nhan_vien,
                loai_xuat="BAN_TRU_LUONG",
                ngay_xuat__month=thang,
                ngay_xuat__year=nam,
                trang_thai_thanh_toan="CHUA_TRU",
            ).aggregate(total_inventory=Sum("tong_tien_phai_thu"))
            tien_dong_phuc = ChiTietLuong.to_decimal_safe(
                inventory_data.get("total_inventory")
            )

            advance_data = SoQuy.objects.filter(
                nhan_vien=nhan_vien,
                loai_phieu="CHI",
                hang_muc="TAM_UNG",
                trang_thai="DA_DUYET",
                ngay_lap__month=thang,
                ngay_lap__year=nam,
            ).aggregate(total_advance=Sum("so_tien"))
            ung_luong = ChiTietLuong.to_decimal_safe(advance_data.get("total_advance"))

            incident_data = BaoCaoSuCo.objects.filter(
                nhan_vien_co_loi=nhan_vien,
                thoi_gian_phat_hien__month=thang,
                thoi_gian_phat_hien__year=nam,
                trang_thai__in=["CHO_DEN_BU", "HOAN_TAT"],
                tenant_id=tenant_id,
            ).aggregate(total_compensation=Sum("phai_thu_nhan_vien"))
            tien_den_bu = ChiTietLuong.to_decimal_safe(
                incident_data.get("total_compensation")
            )

            bao_hiem = Decimal("0")
            phi_cong_doan = Decimal("0")

            thuc_lanh = (
                luong_chinh
                + thuong_chuyen_can
                + phu_cap_khac
                - ung_luong
                - phat_vi_pham
                - tien_dong_phuc
                - tien_den_bu
                - bao_hiem
                - phi_cong_doan
            )

            chi_tiet, _ = ChiTietLuong.objects.update_or_create(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                bang_luong=bang_luong,
                nhan_vien=nhan_vien,
                defaults={
                    "tenant_id": tenant_id,
<<<<<<< HEAD
                    "tong_gio_lam": calculation["tong_gio_lam"],
                    "so_ngay_nghi": calculation.get("so_ngay_nghi", 0),
                    "luong_chinh": calculation["luong_chinh"],
                    "thuong_chuyen_can": calculation["thuong_chuyen_can"],
                    "phu_cap_khac": calculation["phu_cap_khac"],
                    "ung_luong": calculation["ung_luong"],
                    "phat_vi_pham": calculation["phat_vi_pham"],
                    "tien_dong_phuc": calculation["tien_dong_phuc"],
                    "tien_den_bu": calculation["tien_den_bu"],
                    "bao_hiem": calculation["bao_hiem"],
                    "phi_cong_doan": calculation["phi_cong_doan"],
                    "thuc_lanh": calculation["thuc_lanh"],
                    "nguon_du_lieu_snapshot": snapshot,
                    "reconciliation_note": kwargs.get("reconciliation_note", "") or (
                        "Phase D: cần chạy lại đối soát nguồn trước khi review/lock." if existing_phase_c else ""
=======
                    "tong_gio_lam": float(tong_gio_lam),
                    "luong_chinh": ChiTietLuong.to_decimal_safe(luong_chinh),
                    "thuong_chuyen_can": ChiTietLuong.to_decimal_safe(
                        thuong_chuyen_can
                    ),
                    "phu_cap_khac": ChiTietLuong.to_decimal_safe(phu_cap_khac),
                    "ung_luong": ChiTietLuong.to_decimal_safe(ung_luong),
                    "phat_vi_pham": ChiTietLuong.to_decimal_safe(phat_vi_pham),
                    "tien_dong_phuc": ChiTietLuong.to_decimal_safe(tien_dong_phuc),
                    "tien_den_bu": ChiTietLuong.to_decimal_safe(tien_den_bu),
                    "bao_hiem": ChiTietLuong.to_decimal_safe(bao_hiem),
                    "phi_cong_doan": ChiTietLuong.to_decimal_safe(phi_cong_doan),
                    "thuc_lanh": max(
                        ChiTietLuong.to_decimal_safe(thuc_lanh), Decimal("0")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    ),
                },
            )

<<<<<<< HEAD
            if kwargs.get("reconcile_after_calculate"):
                from accounting.application.payroll_reconciliation_use_case import PayrollSourceReconciliationUseCase

                PayrollSourceReconciliationUseCase.execute(
                    bang_luong=bang_luong,
                    tenant_id=tenant_id,
                    employee_ids=[nhan_vien.id],
                    actor=kwargs.get("actor"),
                )
                chi_tiet.refresh_from_db()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            return chi_tiet


class AuditPayrollUseCase:
    """
    Post-calculation anomaly audit for payroll.
    """

    @staticmethod
<<<<<<< HEAD
    @application_audit_log(
        module="accounting",
        model_name="BangLuongThang",
        action=AuditLog.Action.ACCESS,
        object_id_field="bang_luong"
    )
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def execute(bang_luong, tenant_id, user=None):
        try:
            bang_luong_id = (
                bang_luong.pk if isinstance(bang_luong, BangLuongThang) else bang_luong
            )
            current_bl = BangLuongThang.objects.for_tenant(tenant_id).get(
                id=bang_luong_id
            )

            prev_thang = current_bl.thang - 1
            prev_nam = current_bl.nam
            if prev_thang == 0:
                prev_thang = 12
                prev_nam -= 1

            prev_bl = BangLuongThang.objects.for_tenant(tenant_id).filter(
                thang=prev_thang,
                nam=prev_nam,
            ).first()

            if not prev_bl:
                return {
                    "status": "info",
<<<<<<< HEAD
                    "message": f"Không có bảng lương tháng {prev_thang}/{prev_nam} để đối chiếu.",
                    "anomalies": [],
                }

            chi_tiet_mgr = cast("TenantAwareManager", ChiTietLuong.objects)
            current_details = chi_tiet_mgr.for_tenant(tenant_id).filter(
=======
                    "message": f"Khong co bang luong thang {prev_thang}/{prev_nam} de doi chieu.",
                    "anomalies": [],
                }

            current_details = ChiTietLuong.objects.for_tenant(tenant_id).filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                bang_luong=current_bl
            ).select_related("nhan_vien")
            prev_details_map = {
                detail.nhan_vien_id: detail.thuc_lanh
<<<<<<< HEAD
                for detail in chi_tiet_mgr.for_tenant(tenant_id).filter(
=======
                for detail in ChiTietLuong.objects.for_tenant(tenant_id).filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    bang_luong=prev_bl
                )
            }

            anomalies = []
            threshold = Decimal("0.20")
            total_checked = current_details.count()

            for detail in current_details:
                current_value = detail.thuc_lanh
                previous_value = prev_details_map.get(detail.nhan_vien_id)
                if previous_value is None or previous_value <= 0:
                    continue

                diff = abs(current_value - previous_value)
                percent_change = diff / previous_value
                if percent_change > threshold:
                    anomalies.append(
                        {
                            "nhan_vien": detail.nhan_vien.ho_ten,
                            "ma_nv": detail.nhan_vien.ma_nhan_vien,
                            "thuc_lanh_cu": float(previous_value),
                            "thuc_lanh_moi": float(current_value),
                            "bien_dong": float(percent_change * 100),
                            "ly_do": "Bien dong thuc linh > 20%",
                        }
                    )

            anomaly_count = len(anomalies)
            return {
                "status": "success" if not anomalies else "warning",
                "summary": {
                    "total_checked": total_checked,
                    "anomaly_count": anomaly_count,
                    "anomaly_rate": float(round((anomaly_count / total_checked) * 100, 2))
                    if total_checked > 0
                    else 0,
                },
                "anomalies": anomalies,
            }
        except Exception as exc:
<<<<<<< HEAD
            # Rule 9: Tránh dump raw exception chứa PII/payroll detail vào log.
            # Sử dụng structured logging để ghi lại ngữ cảnh kỹ thuật an toàn.
            logger.error(
                "An unexpected error occurred during AuditPayrollUseCase execution",
                exc_info=True,
                extra={
                    "bang_luong_id": bang_luong_id,
                    "tenant_id": tenant_id
                }
            )
            return {
                "status": "error", 
                "message": "Có lỗi hệ thống khi thực hiện đối soát bảng lương. Vui lòng liên hệ quản trị."
            }


class RecalculatePayrollBatchUseCase:
    @staticmethod
    def execute(bang_luong_ids, tenant_id):
        from accounting.services.payroll import PayrollService

        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        result = {
            "updated_count": 0,
            "warning_messages": [],
            "error_messages": [],
        }

        for bang_luong in BangLuongThang.objects.for_tenant(tenant_id).filter(
            id__in=list(bang_luong_ids)
        ):
            if bang_luong.is_locked:
                result["warning_messages"].append(
                    f"Cảnh báo: Bảng lương {bang_luong} đã khóa sổ!"
                )
                continue

            try:
                with transaction.atomic():
                    success, message = PayrollService.tinh_luong_thang(
                        bang_luong.thang,
                        bang_luong.nam,
                    )
                    if success:
                        result["updated_count"] += 1
                    else:
                        result["error_messages"].append(
                            f"Lỗi nghiệp vụ tại {bang_luong}: {message}"
                        )
            except Exception as exc:
                result["error_messages"].append(
                    f"Lỗi hệ thống khi xử lý {bang_luong}: {exc}"
                )

        return result


class LockPayrollBatchUseCase:
    @staticmethod
    def execute(bang_luong_ids, tenant_id):
        from accounting.services.payroll import PayrollService

        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        result = {
            "locked_count": 0,
            "error_messages": [],
        }

        eligible_statuses = [
            BangLuongThang.TrangThai.DRAFT,
            BangLuongThang.TrangThai.CALCULATED,
            BangLuongThang.TrangThai.REVIEWED,
        ]

        for bang_luong in BangLuongThang.objects.for_tenant(tenant_id).filter(
            id__in=list(bang_luong_ids),
            trang_thai__in=eligible_statuses,
        ):
            try:
                with transaction.atomic():
                    bang_luong.trang_thai = BangLuongThang.TrangThai.LOCKED
                    bang_luong.save(update_fields=["trang_thai"])
                    PayrollService.lock_related_records(bang_luong)
                    result["locked_count"] += 1
            except Exception as exc:
                result["error_messages"].append(
                    f"Lỗi khi khóa sổ {bang_luong}: {exc}"
                )

        return result
=======
            logger.error(f"Loi AuditPayrollUseCase: {str(exc)}")
            return {"status": "error", "message": str(exc)}
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
