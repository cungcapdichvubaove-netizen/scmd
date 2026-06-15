# -*- coding: utf-8 -*-
"""Contract state transition policy for SCMD Pro."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ContractTransitionPolicy:
    """Validate allowed HopDong.trang_thai transitions."""

    STATUS_ACTIVE = "HIEU_LUC"
    STATUS_EXPIRING = "SAP_HET_HAN"
    STATUS_CLOSED = "DA_THANH_LY"

    ALLOWED_TRANSITIONS = {
        STATUS_ACTIVE: {STATUS_ACTIVE, STATUS_EXPIRING, STATUS_CLOSED},
        STATUS_EXPIRING: {STATUS_EXPIRING, STATUS_ACTIVE, STATUS_CLOSED},
        STATUS_CLOSED: {STATUS_CLOSED},
    }

    @classmethod
    def validate_transition(cls, old_status: str | None, new_status: str | None) -> None:
        if old_status is None or old_status == new_status:
            return
        allowed = cls.ALLOWED_TRANSITIONS.get(old_status, {old_status})
        if new_status not in allowed:
            raise ValidationError(
                _(
                    "Không được chuyển trạng thái hợp đồng từ %(old)s sang %(new)s. "
                    "Hợp đồng đã thanh lý không được mở hiệu lực trực tiếp."
                ),
                params={"old": old_status, "new": new_status},
            )
