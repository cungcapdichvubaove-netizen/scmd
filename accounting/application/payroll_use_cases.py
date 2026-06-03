# -*- coding: utf-8 -*-
"""
Application Layer: Payroll Use Cases.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from main.decorators import application_audit_log
from main.models import AuditLog
from accounting.models import BangLuongThang, ChiTietLuong
from accounting.models_soquy import SoQuy
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from operations.models import BaoCaoSuCo, ChamCong

logger = logging.getLogger(__name__)


class CalculatePayrollUseCase:
    """
    Hotfix SSOT for payroll calculation.
    """

    @staticmethod
    @application_audit_log(
        module="accounting",
        model_name="ChiTietLuong",
        action=AuditLog.Action.EXECUTE,
    )
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
                bang_luong=bang_luong,
                nhan_vien=nhan_vien,
                defaults={
                    "tenant_id": tenant_id,
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
                    ),
                },
            )

            return chi_tiet


class AuditPayrollUseCase:
    """
    Post-calculation anomaly audit for payroll.
    """

    @staticmethod
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
                    "message": f"Khong co bang luong thang {prev_thang}/{prev_nam} de doi chieu.",
                    "anomalies": [],
                }

            current_details = ChiTietLuong.objects.for_tenant(tenant_id).filter(
                bang_luong=current_bl
            ).select_related("nhan_vien")
            prev_details_map = {
                detail.nhan_vien_id: detail.thuc_lanh
                for detail in ChiTietLuong.objects.for_tenant(tenant_id).filter(
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
            logger.error(f"Loi AuditPayrollUseCase: {str(exc)}")
            return {"status": "error", "message": str(exc)}
