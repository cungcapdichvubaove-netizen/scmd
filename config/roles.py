# -*- coding: utf-8 -*-
"""
SCMD Pro rolepermissions role definitions.

This module is the RBAC SSOT for business roles resolved by rolepermissions.
"""

from rolepermissions.roles import AbstractUserRole


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
