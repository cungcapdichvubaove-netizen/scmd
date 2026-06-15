# -*- coding: utf-8 -*-
"""Authorization policy for customer payment and receivable settlement.

Phase E v2 hardening: financial workflow authorization belongs in the
application layer, not only in Django admin permissions. Customer payments and
allocations are source records for receivable settlement, so authenticated-only
or generic staff access is not sufficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from rolepermissions.checkers import has_role


@dataclass(frozen=True)
class CustomerPaymentPermissionDecision:
    allowed: bool
    reason: str = ""
    code: str = "CUSTOMER_PAYMENT_FORBIDDEN"


class CustomerPaymentPermissionPolicy:
    """Least-privilege policy for customer payment lifecycle actions."""

    MUTATION_ROLES = ("ban_giam_doc", "ke_toan")
    REPORT_ROLES = ("ban_giam_doc", "ke_toan", "nhan_vien_kinh_doanh")

    @staticmethod
    def _is_authenticated(user: Any) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False))

    @classmethod
    def _has_any_role(cls, user: Any, roles) -> bool:
        return bool(user is not None and has_role(user, list(roles)))

    @staticmethod
    def _allow(reason: str = "allowed") -> CustomerPaymentPermissionDecision:
        return CustomerPaymentPermissionDecision(True, reason, "OK")

    @staticmethod
    def _deny(reason: str, code: str = "CUSTOMER_PAYMENT_FORBIDDEN") -> CustomerPaymentPermissionDecision:
        return CustomerPaymentPermissionDecision(False, reason, code)

    @classmethod
    def can_mutate_payment(cls, user: Any) -> CustomerPaymentPermissionDecision:
        if not cls._is_authenticated(user):
            return cls._deny(str(_("Bạn cần đăng nhập để thao tác thanh toán khách hàng.")), "NOT_AUTHENTICATED")
        if getattr(user, "is_superuser", False) or cls._has_any_role(user, cls.MUTATION_ROLES):
            return cls._allow("finance_payment_operator")
        return cls._deny(
            str(_("Bạn không có quyền kế toán/ban giám đốc để thao tác thanh toán khách hàng.")),
            "MISSING_FINANCE_ROLE",
        )

    @classmethod
    def can_receive(cls, user: Any) -> CustomerPaymentPermissionDecision:
        return cls.can_mutate_payment(user)

    @classmethod
    def can_allocate(cls, user: Any) -> CustomerPaymentPermissionDecision:
        return cls.can_mutate_payment(user)

    @classmethod
    def can_cancel(cls, user: Any) -> CustomerPaymentPermissionDecision:
        return cls.can_mutate_payment(user)

    @classmethod
    def can_recalculate(cls, user: Any) -> CustomerPaymentPermissionDecision:
        return cls.can_mutate_payment(user)

    @classmethod
    def can_view_report(cls, user: Any) -> CustomerPaymentPermissionDecision:
        if not cls._is_authenticated(user):
            return cls._deny(str(_("Bạn cần đăng nhập để xem báo cáo công nợ khách hàng.")), "NOT_AUTHENTICATED")
        if getattr(user, "is_superuser", False) or cls._has_any_role(user, cls.REPORT_ROLES):
            return cls._allow("receivable_report_viewer")
        return cls._deny(
            str(_("Bạn không có quyền xem báo cáo công nợ khách hàng.")),
            "MISSING_RECEIVABLE_REPORT_ROLE",
        )

    @classmethod
    def enforce_receive(cls, user: Any) -> None:
        decision = cls.can_receive(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_allocate(cls, user: Any) -> None:
        decision = cls.can_allocate(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_cancel(cls, user: Any) -> None:
        decision = cls.can_cancel(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_recalculate(cls, user: Any) -> None:
        decision = cls.can_recalculate(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    @classmethod
    def enforce_report(cls, user: Any) -> None:
        decision = cls.can_view_report(user)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)


__all__ = ["CustomerPaymentPermissionDecision", "CustomerPaymentPermissionPolicy"]
