# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: reports/services.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Service xử lý xuất báo cáo (PDF/Excel).
             - Sử dụng WeasyPrint để tạo PDF từ HTML template.
             - Sử dụng OpenPyXL để tạo báo cáo Excel chuyên nghiệp.
"""

import io
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from weasyprint import HTML, CSS
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc

class ReportService:
    
    @staticmethod
    def generate_incident_pdf(incident_id, request=None):
        """
        Tạo file PDF cho một sự cố cụ thể.
        """
        try:
            incident = BaoCaoSuCo.objects.get(id=incident_id)
            
            # 1. Render HTML từ template
            context = {
                'incident': incident,
                'company_info': {
                    'name': "CÔNG TY DỊCH VỤ BẢO VỆ SCMD",
                    'address': "123 Đường Số 1, Quận 1, TP.HCM",
                    'hotline': "1900 1234"
                },
                'print_time': timezone.now()
            }
            
            # Sử dụng template dành riêng cho in ấn (cần tạo file này)
            html_string = render_to_string('reports/print/incident_pdf.html', context, request=request)
            
            # 2. Convert HTML sang PDF bằng WeasyPrint
            # Base_url là cần thiết để load ảnh/css từ static
            base_url = request.build_absolute_uri('/') if request else settings.BASE_DIR
            
            pdf_file = io.BytesIO()
            HTML(string=html_string, base_url=base_url).write_pdf(target=pdf_file)
            
            pdf_file.seek(0)
            return pdf_file, f"SuCo_{incident.ma_su_co}.pdf"
            
        except BaoCaoSuCo.DoesNotExist:
            return None, None

    @staticmethod
    def generate_attendance_excel(month, year, muc_tieu_id=None):
        """
        Xuất báo cáo chấm công tháng ra Excel.
        """
        # 1. Khởi tạo Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"ChamCong_T{month}_{year}"
        
        # 2. Định dạng Style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        border_style = Side(style='thin')
        full_border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)
        
        # 3. Tiêu đề Báo cáo
        ws.merge_cells('A1:G1')
        ws['A1'] = f"BẢNG TỔNG HỢP CHẤM CÔNG - THÁNG {month}/{year}"
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # 4. Header Cột
        headers = ["STT", "Ngày trực", "Nhân viên", "Mục tiêu", "Ca trực", "Giờ vào/ra", "Trạng thái"]
        ws.append([]) # Dòng trống
        ws.append(headers)
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # 5. Lấy dữ liệu
        queryset = PhanCongCaTruc.objects.filter(
            ngay_truc__month=month, 
            ngay_truc__year=year
        ).select_related('nhan_vien', 'vi_tri_chot__muc_tieu', 'ca_lam_viec')
        
        if muc_tieu_id:
            queryset = queryset.filter(vi_tri_chot__muc_tieu_id=muc_tieu_id)
            
        queryset = queryset.order_by('ngay_truc', 'nhan_vien__ho_ten')
        
        # 6. Ghi dữ liệu
        for idx, pc in enumerate(queryset, 1):
            # Lấy thông tin chấm công (nếu có)
            cc_info = "Chưa chấm"
            status = "Vắng"
            if hasattr(pc, 'chamcong'):
                cc = pc.chamcong
                if cc.thoi_gian_check_in:
                    in_time = cc.thoi_gian_check_in.strftime('%H:%M')
                    out_time = cc.thoi_gian_check_out.strftime('%H:%M') if cc.thoi_gian_check_out else "--:--"
                    cc_info = f"{in_time} - {out_time}"
                    status = "Hoàn thành" if cc.thoi_gian_check_out else "Đang trực"
            
            row_data = [
                idx,
                pc.ngay_truc.strftime('%d/%m/%Y'),
                pc.nhan_vien.ho_ten,
                pc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                pc.ca_lam_viec.ten_ca,
                cc_info,
                status
            ]
            ws.append(row_data)
            
            # Kẻ khung
            for col in range(1, 8):
                ws.cell(row=3 + idx, column=col).border = full_border

        # Auto-size cột (cơ bản)
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['F'].width = 20

        # Xuất ra BytesIO
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        return excel_file, f"BangCong_T{month}_{year}.xlsx"