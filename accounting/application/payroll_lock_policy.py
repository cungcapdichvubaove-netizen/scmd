# -*- coding: utf-8 -*-
"""
Application Layer: Payroll lock policy.

Central guard for attendance/assignment mutation after a payroll period is
LOCKED or PAID. Kept in accounting.application because payroll period state is
the authority, while operations models/use cases only ask the policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class PayrollPeriodRef:
    id: int
    thang: int
    nam: int
    trang_thai: str
    is_locked: bool


def _default_tenant_id(tenant_id=None):
    return tenant_id or getattr(settings, "SCMD_ORGANIZATION_ID", None)


class PayrollLockPolicy:
    """SSOT for payroll lock checks that protect source operational truth."""

    LOCKED_MESSAGE = _(
        "Kỳ lương tháng %(month)s/%(year)s đã %(state)s. "
        "Không được sửa/xóa chấm công hoặc phân công ca trực trong kỳ đã khóa. "
        "Hãy xử lý bằng adjustment/reconciliation có audit trail."
    )

    @classmethod
    def get_period_for_work_date(cls, work_date, tenant_id=None):
        if not work_date:
            return None

        from accounting.models import BangLuongThang

        scoped_tenant_id = _default_tenant_id(tenant_id)
        if not scoped_tenant_id:
            return None

        return (
            BangLuongThang.objects.for_tenant(scoped_tenant_id)
            .filter(thang=work_date.month, nam=work_date.year)
            .only("id", "thang", "nam", "trang_thai", "tenant_id")
            .first()
        )

    @classmethod
    def snapshot_period(cls, period) -> Optional[PayrollPeriodRef]:
        if period is None:
            return None
        return PayrollPeriodRef(
            id=period.pk,
            thang=period.thang,
            nam=period.nam,
            trang_thai=period.trang_thai,
            is_locked=period.is_locked,
        )

    @classmethod
    def get_period_for_assignment(cls, assignment):
        work_date = getattr(assignment, "ngay_truc", None)
        tenant_id = getattr(assignment, "tenant_id", None)
        return cls.get_period_for_work_date(work_date, tenant_id=tenant_id)

    @classmethod
    def get_period_for_attendance(cls, attendance):
        ca_truc = getattr(attendance, "ca_truc", None)
        if ca_truc is None and getattr(attendance, "ca_truc_id", None):
            from operations.models import PhanCongCaTruc

            ca_truc = (
                PhanCongCaTruc.objects
                .select_related("ca_lam_viec")
                .filter(pk=attendance.ca_truc_id)
                .first()
            )
        if ca_truc is None:
            return None
        return cls.get_period_for_assignment(ca_truc)

    @classmethod
    def is_period_locked_for_assignment(cls, assignment):
        period = cls.get_period_for_assignment(assignment)
        return bool(period and period.is_locked)

    @classmethod
    def is_period_locked_for_attendance(cls, attendance):
        period = cls.get_period_for_attendance(attendance)
        return bool(period and period.is_locked)

    @classmethod
    def _raise_locked(cls, period):
        raise ValidationError(
            cls.LOCKED_MESSAGE
            % {
                "month": period.thang,
                "year": period.nam,
                "state": period.trang_thai,
            }
        )

    @classmethod
    def enforce_assignment_mutable(cls, assignment):
        period = cls.get_period_for_assignment(assignment)
        if period and period.is_locked:
            cls._raise_locked(period)
        return period

    @classmethod
    def enforce_attendance_mutable(cls, attendance):
        period = cls.get_period_for_attendance(attendance)
        if period and period.is_locked:
            cls._raise_locked(period)
        return period
