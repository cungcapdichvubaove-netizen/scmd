# -*- coding: utf-8 -*-
"""
Access Scope foundation for SCMD Pro.

Phase A deliberately stays conservative: it defines the stable scope types and a
resolver skeleton without querying business tables or widening access. Direct
visibility, temporary delegation, historical assignment and action policies must
be added in later phases at the authoritative locations documented under
``docs/access_scope``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any


class ScopeLevel(IntEnum):
    """Ordered scope hierarchy used for Phase A comparisons.

    NOTE: HR, PAYROLL and INVENTORY are included because the Phase 1 contract
    lists them as operational scope values. Later domain policies must still
    check business domain boundaries instead of relying on numeric ordering
    alone for cross-domain authorization.
    """

    SELF = 10
    SITE = 20
    REGION = 30
    OPERATIONS = 40
    HR = 50
    PAYROLL = 60
    INVENTORY = 70
    EXECUTIVE = 80
    TECHNICAL_ADMIN = 90

    @classmethod
    def coerce(cls, value: "ScopeLevel | str") -> "ScopeLevel":
        if isinstance(value, ScopeLevel):
            return value
        normalized = str(value).strip().upper()
        if normalized == "TECHNICAL":
            normalized = "TECHNICAL_ADMIN"
        return cls[normalized]


class ScopeType(str, Enum):
    SELF = "SELF"
    SITE = "SITE"
    REGION = "REGION"
    OPERATIONS = "OPERATIONS"
    HR = "HR"
    PAYROLL = "PAYROLL"
    INVENTORY = "INVENTORY"
    EXECUTIVE = "EXECUTIVE"
    TECHNICAL_ADMIN = "TECHNICAL_ADMIN"


class ScopeSource(str, Enum):
    CONSERVATIVE_DEFAULT = "CONSERVATIVE_DEFAULT"
    DIRECT = "DIRECT"
    DELEGATED = "DELEGATED"
    HISTORICAL = "HISTORICAL"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class ResolvedScope:
    """Resolved access-scope snapshot for one user at one point in time."""

    user_id: int | None
    is_authenticated: bool
    effective_scope_level: ScopeLevel | None
    scope_type: ScopeType | None
    scope_source: ScopeSource
    at_time: datetime | None = None
    delegation_id: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_scope_level_name(self) -> str | None:
        return self.effective_scope_level.name if self.effective_scope_level else None

    def has_level(self, required_level: ScopeLevel | str) -> bool:
        if not self.is_authenticated or self.effective_scope_level is None:
            return False
        return self.effective_scope_level >= ScopeLevel.coerce(required_level)

    def explain(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "is_authenticated": self.is_authenticated,
            "effective_scope_level": self.effective_scope_level_name,
            "scope_type": self.scope_type.value if self.scope_type else None,
            "scope_source": self.scope_source.value,
            "delegation_id": self.delegation_id,
            "at_time": self.at_time.isoformat() if self.at_time else None,
            "details": dict(self.details),
        }


class ScopeResolver:
    """Conservative Phase A resolver.

    This resolver intentionally does not query NhanVien, MucTieu,
    PhanCongCaTruc, delegation or historical assignment tables in Phase A.
    Missing model data must result in SELF-only authenticated scope, never a
    broad fallback. Later phases should extend this class through scoped policy
    helpers and documented use cases, not via Model.objects.all().
    """

    @staticmethod
    def _is_authenticated(user: Any) -> bool:
        return bool(user is not None and getattr(user, "is_authenticated", False))

    @staticmethod
    def _user_id(user: Any) -> int | None:
        value = getattr(user, "pk", None) or getattr(user, "id", None)
        return int(value) if isinstance(value, int) else value

    @classmethod
    def resolve_user_scope(
        cls,
        user: Any,
        at_time: datetime | None = None,
    ) -> ResolvedScope:
        if not cls._is_authenticated(user):
            return ResolvedScope(
                user_id=cls._user_id(user),
                is_authenticated=False,
                effective_scope_level=None,
                scope_type=None,
                scope_source=ScopeSource.CONSERVATIVE_DEFAULT,
                at_time=at_time,
                details={
                    "reason": "Unauthenticated or missing user; no business scope granted.",
                    "phase": "A",
                },
            )

        # TODO Phase B/C/D/E:
        # - Resolve direct staff/site/region scope from authoritative assignment
        #   policies without using unscoped Model.objects.all().
        # - Merge active temporary delegation from delegation.application.
        # - Apply historical staff-site assignment at event time.
        # - Apply override boundaries with audit context.
        return ResolvedScope(
            user_id=cls._user_id(user),
            is_authenticated=True,
            effective_scope_level=ScopeLevel.SELF,
            scope_type=ScopeType.SELF,
            scope_source=ScopeSource.CONSERVATIVE_DEFAULT,
            at_time=at_time,
            details={
                "reason": "Phase A conservative default; no direct/delegated/historical scope resolved yet.",
                "phase": "A",
            },
        )

    @classmethod
    def user_has_scope_level(
        cls,
        user: Any,
        required_level: ScopeLevel | str,
        at_time: datetime | None = None,
    ) -> bool:
        return cls.resolve_user_scope(user, at_time=at_time).has_level(required_level)

    @classmethod
    def explain_scope(
        cls,
        user: Any,
        at_time: datetime | None = None,
    ) -> dict[str, Any]:
        return cls.resolve_user_scope(user, at_time=at_time).explain()


__all__ = [
    "ResolvedScope",
    "ScopeLevel",
    "ScopeResolver",
    "ScopeSource",
    "ScopeType",
]
