# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/permissions_config.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Cấu hình danh sách Nhóm quyền hạn (Permission Groups).
             REFACTOR: Áp dụng i18n (gettext_lazy) cho các mô tả.
"""

from django.utils.translation import gettext_lazy as _

# Định nghĩa các nhóm chức năng để hiển thị trên Ma trận
PERMISSION_GROUPS = {
    "1. VẬN HÀNH (OPERATIONS)": {
        "description": _("Quản lý lịch trực, sự cố, chấm công và tuần tra mục tiêu"),
        "models": [
            ("operations", "phancongcatruc", _("Lịch trực")),
            ("operations", "baocaosuco", _("Báo cáo Sự cố")),
            ("operations", "chamcong", _("Dữ liệu Chấm công")),
            ("operations", "kiemtraquanso", _("Kiểm tra Quân số (Alive Check)")),
            ("operations", "lichtuantravanhanh", _("Lịch tuần tra theo ca")),
            ("operations", "nhiemvutuantraca", _("Nhiệm vụ tuần tra theo ca")),
            ("inspection", "loaituantra", _("Tuyến/điểm QR tuần tra vận hành (legacy table)")),
            ("inspection", "luottuantra", _("Lượt tuần tra bảo vệ (legacy table, linked to operations)")),
        ]
    },
    "2. THANH TRA & GIÁM SÁT (INSPECTION)": {
        "description": _("Kế hoạch kiểm tra mục tiêu, biên bản, vi phạm và kiến nghị khắc phục"),
        "models": [
            ("inspection", "dotthanhtra", _("Kế hoạch/đợt kiểm tra mục tiêu")),
            ("inspection", "bienbanthanhtra", _("Biên bản kiểm tra mục tiêu")),
            ("inspection", "bienbanvipham", _("Biên bản Vi phạm/Kỷ luật")),
        ]
    },
    "3. NHÂN SỰ (HR)": {
        "description": _("Quản lý Hồ sơ nhân viên & Hợp đồng"),
        "models": [
            ("users", "nhanvien", _("Hồ sơ Nhân viên")),
            ("users", "lichsucongtac", _("Lịch sử Điều động")),
            ("users", "phongban", _("Phòng ban")),
            ("users", "chucdanh", _("Chức danh")),
        ]
    },
    "4. TÀI CHÍNH & KHO": {
        "description": _("Lương, Thưởng, Cấp phát"),
        "models": [
            ("accounting", "bangluongthang", _("Bảng Lương")),
            ("accounting", "soquy", _("Sổ Quỹ")),
            ("inventory", "vattu", _("Kho Vật tư")),
            ("inventory", "phieuxuat", _("Phiếu Xuất/Cấp phát")),
        ]
    },
    "5. KHÁCH HÀNG": {
        "description": _("Quản lý Mục tiêu & Hợp đồng"),
        "models": [
            ("clients", "muctieu", _("Mục tiêu Bảo vệ")),
            ("clients", "hopdong", _("Hợp đồng Dịch vụ")),
        ]
    }
}