# -*- coding: utf-8 -*-
"""
Application-layer policy for incident lifecycle transitions.
"""


class IncidentTransitionPolicy:
    """
    Enforces the incident lifecycle contract for BaoCaoSuCo.

    Closed incidents must not be edited directly. Reopening is an explicit
    status transition that requires a reason and moves the incident back into
    active processing.
    """

    STATUS_CHO_XU_LY = "CHO_XU_LY"
    STATUS_DANG_XU_LY = "DANG_XU_LY"
    STATUS_DA_XU_LY = "DA_XU_LY"
    STATUS_CHO_DEN_BU = "CHO_DEN_BU"
    STATUS_HOAN_TAT = "HOAN_TAT"
    STATUS_HUY = "HUY"

    CLOSED_STATUSES = {STATUS_HOAN_TAT, STATUS_HUY}
    REOPEN_TARGET_STATUS = STATUS_DANG_XU_LY

    PRIMARY_FIELDS = {
        "tieu_de",
        "muc_do",
        "nhan_vien_bao_cao",
        "muc_tieu",
        "ca_truc",
        "thoi_gian_phat_hien",
        "mo_ta_chi_tiet",
        "hinh_anh_1",
        "hinh_anh_2",
        "file_ghi_am",
        "tong_thiet_hai",
        "cong_ty_chi_tra",
        "nhan_vien_co_loi",
        "phai_thu_nhan_vien",
        "nguoi_xu_ly",
        "ghi_chu_quan_ly",
    }

    ALLOWED_TRANSITIONS = {
        STATUS_CHO_XU_LY: {STATUS_DANG_XU_LY, STATUS_HUY},
        STATUS_DANG_XU_LY: {STATUS_DA_XU_LY, STATUS_CHO_DEN_BU, STATUS_HOAN_TAT, STATUS_HUY},
        STATUS_DA_XU_LY: {STATUS_DANG_XU_LY, STATUS_CHO_DEN_BU, STATUS_HOAN_TAT, STATUS_HUY},
        STATUS_CHO_DEN_BU: {STATUS_DANG_XU_LY, STATUS_HOAN_TAT, STATUS_HUY},
        STATUS_HOAN_TAT: {REOPEN_TARGET_STATUS},
        STATUS_HUY: {REOPEN_TARGET_STATUS},
    }

    @classmethod
    def is_closed(cls, status):
        return status in cls.CLOSED_STATUSES

    @classmethod
    def requires_reason(cls, previous_status, new_status):
        return previous_status != new_status

    @classmethod
    def is_reopen(cls, previous_status, new_status):
        return cls.is_closed(previous_status) and new_status == cls.REOPEN_TARGET_STATUS

    @classmethod
    def get_locked_fields_for_closed_incident(cls):
        return cls.PRIMARY_FIELDS

    @classmethod
    def validate_transition(cls, previous_status, new_status):
        if previous_status == new_status:
            return

        allowed_statuses = cls.ALLOWED_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed_statuses:
            raise ValueError(
                f"Không được chuyển trạng thái sự cố từ {previous_status} sang {new_status}."
            )

    @classmethod
    def validate_closed_incident_edit(cls, previous_status, new_status, changed_fields):
        changed_fields = set(changed_fields)

        if not cls.is_closed(previous_status):
            return

        allowed_when_closed = {"trang_thai"}
        disallowed_fields = changed_fields - allowed_when_closed
        if disallowed_fields:
            raise ValueError(
                "Sự cố đã đóng chỉ được phép reopen. Không được sửa trực tiếp các trường nội dung chính."
            )

        if changed_fields and not cls.is_reopen(previous_status, new_status):
            raise ValueError(
                "Sự cố đã đóng chỉ được chuyển về trạng thái đang xử lý để reopen."
            )
