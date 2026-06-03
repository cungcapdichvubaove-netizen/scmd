# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: reports/services.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Service xá»­ lÃ½ xuáº¥t bÃ¡o cÃ¡o (PDF/Excel).
             - Sá»­ dá»¥ng WeasyPrint Ä‘á»ƒ táº¡o PDF tá»« HTML template.
             - Sá»­ dá»¥ng OpenPyXL Ä‘á»ƒ táº¡o bÃ¡o cÃ¡o Excel chuyÃªn nghiá»‡p.
"""

import io

import openpyxl
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from weasyprint import HTML

from operations.models import BaoCaoSuCo, PhanCongCaTruc


class ReportService:
    @staticmethod
    def generate_incident_pdf(incident_id, request=None, tenant_id=None):
        """
        Táº¡o file PDF cho má»™t sá»± cá»‘ cá»¥ thá»ƒ.
        """
        try:
            scoped_tenant_id = tenant_id or getattr(settings, "SCMD_ORGANIZATION_ID", None)
            incident = BaoCaoSuCo.objects.for_tenant(scoped_tenant_id).get(id=incident_id)

            context = {
                "incident": incident,
                "company_info": {
                    "name": "CÃ”NG TY Dá»ŠCH Vá»¤ Báº¢O Vá»† SCMD",
                    "address": "123 ÄÆ°á»ng Sá»‘ 1, Quáº­n 1, TP.HCM",
                    "hotline": "1900 1234",
                },
                "print_time": timezone.now(),
            }
            html_string = render_to_string("reports/print/incident_pdf.html", context, request=request)
            base_url = request.build_absolute_uri("/") if request else settings.BASE_DIR

            pdf_file = io.BytesIO()
            HTML(string=html_string, base_url=base_url).write_pdf(target=pdf_file)
            pdf_file.seek(0)
            return pdf_file, f"SuCo_{incident.ma_su_co}.pdf"

        except BaoCaoSuCo.DoesNotExist:
            return None, None

    @staticmethod
    def generate_attendance_excel(month, year, muc_tieu_id=None, tenant_id=None):
        """
        Xuáº¥t bÃ¡o cÃ¡o cháº¥m cÃ´ng thÃ¡ng ra Excel.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"ChamCong_T{month}_{year}"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        border_style = Side(style="thin")
        full_border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)

        ws.merge_cells("A1:G1")
        ws["A1"] = f"Báº¢NG Tá»”NG Há»¢P CHáº¤M CÃ”NG - THÃNG {month}/{year}"
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")

        headers = ["STT", "NgÃ y trá»±c", "NhÃ¢n viÃªn", "Má»¥c tiÃªu", "Ca trá»±c", "Giá» vÃ o/ra", "Tráº¡ng thÃ¡i"]
        ws.append([])
        ws.append(headers)

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        scoped_tenant_id = tenant_id or getattr(settings, "SCMD_ORGANIZATION_ID", None)
        queryset = (
            PhanCongCaTruc.objects.for_tenant(scoped_tenant_id)
            .filter(ngay_truc__month=month, ngay_truc__year=year)
            .select_related("nhan_vien", "vi_tri_chot__muc_tieu", "ca_lam_viec")
        )

        if muc_tieu_id:
            queryset = queryset.filter(vi_tri_chot__muc_tieu_id=muc_tieu_id)

        queryset = queryset.order_by("ngay_truc", "nhan_vien__ho_ten")

        for idx, pc in enumerate(queryset, 1):
            cc_info = "ChÆ°a cháº¥m"
            status = "Váº¯ng"
            if hasattr(pc, "chamcong"):
                cc = pc.chamcong
                if cc.thoi_gian_check_in:
                    in_time = cc.thoi_gian_check_in.strftime("%H:%M")
                    out_time = cc.thoi_gian_check_out.strftime("%H:%M") if cc.thoi_gian_check_out else "--:--"
                    cc_info = f"{in_time} - {out_time}"
                    status = "HoÃ n thÃ nh" if cc.thoi_gian_check_out else "Äang trá»±c"

            ws.append(
                [
                    idx,
                    pc.ngay_truc.strftime("%d/%m/%Y"),
                    pc.nhan_vien.ho_ten,
                    pc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                    pc.ca_lam_viec.ten_ca,
                    cc_info,
                    status,
                ]
            )

            for col in range(1, 8):
                ws.cell(row=3 + idx, column=col).border = full_border

        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 25
        ws.column_dimensions["D"].width = 30
        ws.column_dimensions["F"].width = 20

        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        return excel_file, f"BangCong_T{month}_{year}.xlsx"
