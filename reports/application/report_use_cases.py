# -*- coding: utf-8 -*-
"""
Application-layer report queries for the reports module.

SCMD currently runs as single-organization hardened. Models without a direct
tenant field remain explicit single-organization exceptions until schema scope
is modeled there.
"""

import calendar

from clients.models import MucTieu
from operations.models import BaoCaoSuCo, ChamCong
from users.models import NhanVien


class GetMonthlyAttendanceMatrixUseCase:
    @staticmethod
    def execute(thang: int, nam: int, tenant_id):
        _, num_days = calendar.monthrange(nam, thang)
        days_in_month = range(1, num_days + 1)

        nhan_vien_list = NhanVien.objects.filter(trang_thai_lam_viec="dang_lam_viec")
        report_data = []

        for nv in nhan_vien_list:
            row = {"nhan_vien": nv, "days": {}}
            total_cong = 0

            cham_cong_qs = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__nhan_vien=nv,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .select_related("ca_truc")
            )
            cc_map = {cc.ca_truc.ngay_truc.day: cc for cc in cham_cong_qs}

            for day in days_in_month:
                cc = cc_map.get(day)
                if cc:
                    status = "X"
                    if cc.thoi_gian_check_in and cc.thoi_gian_check_out:
                        total_cong += 1
                    elif not cc.thoi_gian_check_out:
                        status = "NoOut"
                    row["days"][day] = status
                else:
                    row["days"][day] = ""

            row["total_cong"] = total_cong
            report_data.append(row)

        return {"report_data": report_data, "days_in_month": days_in_month}


class GetPersonalAttendanceReportUseCase:
    @staticmethod
    def execute(thang: int, nam: int, nhan_vien_id, tenant_id):
        selected_nv = None
        report_data = None

        if nhan_vien_id:
            selected_nv = NhanVien.objects.filter(id=nhan_vien_id).first()
            report_data = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__nhan_vien_id=nhan_vien_id,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .order_by("ca_truc__ngay_truc")
            )

        return {
            "nhan_vien_list": NhanVien.objects.filter(
                trang_thai_lam_viec__in=["THUVIEC", "CHINHTHUC", "TAMHOAN", "NGHIVIEC"]
            ).order_by("ho_ten"),
            "selected_nv": selected_nv,
            "report_data": report_data,
        }


class GetTargetAttendanceReportUseCase:
    @staticmethod
    def execute(thang: int, nam: int, muc_tieu_id, tenant_id):
        report_data = None
        selected_muc_tieu = None

        if muc_tieu_id:
            report_data = (
                ChamCong.objects.for_tenant(tenant_id)
                .filter(
                    ca_truc__vi_tri_chot__muc_tieu_id=muc_tieu_id,
                    ca_truc__ngay_truc__month=thang,
                    ca_truc__ngay_truc__year=nam,
                )
                .order_by("ca_truc__ngay_truc", "ca_truc__nhan_vien__ho_ten")
            )
            selected_muc_tieu = (
                MucTieu.objects.for_tenant(tenant_id).filter(id=muc_tieu_id).first()
            )

        return {
            "muc_tieu_list": MucTieu.objects.for_tenant(tenant_id).order_by("ten_muc_tieu"),
            "selected_muc_tieu": selected_muc_tieu,
            "report_data": report_data,
        }


class GetIncidentReportUseCase:
    @staticmethod
    def execute(thang: int, nam: int, tenant_id):
        return (
            BaoCaoSuCo.objects.for_tenant(tenant_id)
            .filter(created_at__month=thang, created_at__year=nam)
            .select_related("muc_tieu", "nhan_vien_bao_cao")
            .order_by("-created_at")
        )
