# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro rolepermissions role definitions.

This module is the RBAC SSOT for business roles resolved by rolepermissions.
=======
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: scmd_project/roles.py
Author: Mr. Anh (CTO)
Updated Date: 2026-03-21
Description: Hệ thống phân quyền đa tầng (Multi-tier RBAC) cho Công ty An ninh chuyên nghiệp.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
"""

from rolepermissions.roles import AbstractUserRole

<<<<<<< HEAD

GUARD_OPERATIONS = {
    "check_in_out": True,
    # Legacy permission kept for one transition release. Canonical permission
    # for guard patrol is thuc_hien_tuan_tra_bao_ve.
    "gui_bao_cao_tuan_tra": True,
    "thuc_hien_tuan_tra_bao_ve": True,
    "bao_cao_su_co_khan_cap": True,
    "xem_lich_truc_ca_nhan": True,
}

SITE_MANAGEMENT = {
    "giao_ca_truc": True,
    "duyet_don_nghi_phep": True,
    "danh_gia_nhan_vien": True,
    "xem_so_truc_muc_tieu": True,
    "lap_bien_ban_vi_pham": True,
    "quan_ly_tuyen_tuan_tra_van_hanh": True,
    "quan_ly_lich_tuan_tra_van_hanh": True,
    "xem_doi_soat_tuan_tra_van_hanh": True,
    "xu_ly_canh_bao_tuan_tra_van_hanh": True,
}

REGIONAL_OPERATIONS = {
    "tao_muc_tieu_moi": True,
    "thiet_lap_geofencing": True,
    "dieu_dong_nhan_su_lien_vung": True,
    "xem_bao_cao_phan_tich_rui_ro": True,
    "duyet_phu_cap_doc_hai": True,
}

SALES_CRM = {
    "quan_ly_khach_hang": True,
    "soan_thao_hop_dong": True,
    "xem_doanh_thu_du_kien": True,
}

FINANCIAL_ADMIN = {
    "xem_bang_luong_tong": True,
    "xuat_hoa_don_hop_dong": True,
    "quan_ly_thu_chi_nghiep_vu": True,
}

INVENTORY_PERMISSIONS = {
    "xem_ton_kho": True,
    "lap_phieu_nhap_xuat_kho": True,
    "doi_soat_ton_kho": True,
}

HR_PERMISSIONS = {
    "xem_ho_so_nhan_su": True,
    "cap_nhat_ho_so_nhan_su": True,
    "xu_ly_dieu_chuyen_nhan_su": True,
}

EXECUTIVE_VIEW = {
    "xem_dashboard_tong_the": True,
    "truy_xuat_audit_log": True,
    "phe_duyet_chi_phi_lon": True,
}


class NhanVienBaoVe(AbstractUserRole):
    available_permissions = GUARD_OPERATIONS


class DoiTruong(AbstractUserRole):
    available_permissions = {**GUARD_OPERATIONS, **SITE_MANAGEMENT}


class QuanLyVung(AbstractUserRole):
    available_permissions = {
        **GUARD_OPERATIONS,
        **SITE_MANAGEMENT,
        **REGIONAL_OPERATIONS,
    }


class NhanVienKinhDoanh(AbstractUserRole):
    available_permissions = SALES_CRM


class KeToan(AbstractUserRole):
    available_permissions = FINANCIAL_ADMIN


INSPECTION_PERMISSIONS = {
    "lap_ke_hoach_thanh_tra": True,
    "thuc_hien_thanh_tra_muc_tieu": True,
    "lap_bien_ban_thanh_tra": True,
    "duyet_bien_ban_thanh_tra": True,
    "theo_doi_khac_phuc_sau_thanh_tra": True,
    "lap_bien_ban_vi_pham": True,
}


class ThanhTra(AbstractUserRole):
    # Thanh tra owns inspection/checking workflows. It does not inherit
    # operations patrol schedule management by default.
    available_permissions = INSPECTION_PERMISSIONS


class NghiepVu(AbstractUserRole):
    available_permissions = {**SITE_MANAGEMENT, **REGIONAL_OPERATIONS}


class ThuKho(AbstractUserRole):
    available_permissions = INVENTORY_PERMISSIONS


class NhanSu(AbstractUserRole):
    available_permissions = HR_PERMISSIONS


class BanGiamDoc(AbstractUserRole):
    available_permissions = {
        **REGIONAL_OPERATIONS,
        **SALES_CRM,
        **FINANCIAL_ADMIN,
        **INVENTORY_PERMISSIONS,
        **HR_PERMISSIONS,
        **EXECUTIVE_VIEW,
        "toan_quyen_he_thong": True,
    }
=======
# ==============================================================================
# 1. TẬP HỢP QUYỀN THEO NGHIỆP VỤ (PERMISSION BUNDLES)
# ==============================================================================

# Quyền cơ bản cho Nhân viên bảo vệ (Security Guard)
GUARD_OPERATIONS = {
    'check_in_out': True,           # Quẹt thẻ, chấm công GPS
    'gui_bao_cao_tuan_tra': True,    # Gửi báo cáo theo ca
    'bao_cao_su_co_khan_cap': True,  # Nút bấm khẩn cấp SOS
    'xem_lich_truc_ca_nhan': True,
}

# Quyền cho Đội trưởng / Chỉ huy trưởng (Site Manager)
SITE_MANAGEMENT = {
    'giao_ca_truc': True,            # Sắp xếp lịch trực tại mục tiêu
    'duyet_don_nghi_phep': True,     # Duyệt nghỉ phép nội bộ đội
    'danh_gia_nhan_vien': True,      # Chấm điểm KPI nhân viên
    'xem_so_truc_muc_tieu': True,    # Xem toàn bộ lịch sử mục tiêu đó
}

# Quyền cho Phòng nghiệp vụ / Quản lý vùng (Operations Department)
REGIONAL_OPERATIONS = {
    'tao_muc_tieu_moi': True,        # Khởi tạo mục tiêu bảo vệ
    'thiet_lap_geofencing': True,    # Cấu hình tọa độ GPS/Bán kính bảo vệ
    'dieu_dong_nhan_su_lien_vung': True,
    'xem_bao_cao_phan_tich_rui_ro': True,
    'duyet_phu_cap_doc_hai': True,
}

# Quyền cho Khối kinh doanh & CRM (Sales & CRM)
SALES_CRM = {
    'quan_ly_khach_hang': True,
    'soan_thao_hop_dong': True,
    'xem_doanh_thu_du_kien': True,
}

# Quyền cho Khối tài chính - Kế toán (Accounting)
FINANCIAL_ADMIN = {
    'xem_bang_luong_tong': True,
    'xuat_hoa_don_hop_dong': True,
    'quan_ly_thu_chi_nghiep_vu': True,
}

# Quyền cho Ban Giám đốc (Board of Directors)
EXECUTIVE_VIEW = {
    'xem_dashboard_tong_the': True,
    'truy_xuat_audit_log': True,     # Kiểm tra lịch sử chỉnh sửa của mọi user
    'phe_duyet_chi_phi_lon': True,
}

# ==============================================================================
# 2. ĐỊNH NGHĨA VAI TRÒ (ROLES HIERARCHY)
# ==============================================================================

class NhanVienBaoVe(AbstractUserRole):
    """Cấp độ 1: Nhân viên thực thi tại mục tiêu"""
    available_permissions = GUARD_OPERATIONS

class DoiTruong(AbstractUserRole):
    """Cấp độ 2: Chỉ huy tại mục tiêu (Kế thừa Guard)"""
    available_permissions = {**GUARD_OPERATIONS, **SITE_MANAGEMENT}

class QuanLyVung(AbstractUserRole):
    """Cấp độ 3: Quản lý vận hành khu vực (Kế thừa Site Management)"""
    available_permissions = {**GUARD_OPERATIONS, **SITE_MANAGEMENT, **REGIONAL_OPERATIONS}

class NhanVienKinhDoanh(AbstractUserRole):
    """Khối văn phòng: Sales"""
    available_permissions = SALES_CRM

class KeToan(AbstractUserRole):
    """Khối văn phòng: Tài chính"""
    available_permissions = FINANCIAL_ADMIN

class BanGiamDoc(AbstractUserRole):
    """Cấp độ tối cao: CEO/CTO (Toàn quyền hệ thống)"""
    available_permissions = {
        **REGIONAL_OPERATIONS, 
        **SALES_CRM, 
        **FINANCIAL_ADMIN, 
        **EXECUTIVE_VIEW,
        'toan_quyen_he_thong': True
    }
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
