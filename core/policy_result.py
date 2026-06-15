# -*- coding: utf-8 -*-
"""
PolicyResult SSOT for SCMD Pro access-scope decisions.

SCMD Pro is a single-organization hardened layered monolith. This module only
standardizes policy allow/deny results and API denial payloads. It does not
resolve organization scope and must not accept tenant_id/request tenant input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ERR_SCOPE_STAFF_OUT_OF_SCOPE = "ERR_SCOPE_STAFF_OUT_OF_SCOPE"
ERR_SCOPE_SITE_OUT_OF_SCOPE = "ERR_SCOPE_SITE_OUT_OF_SCOPE"
ERR_SCOPE_SHIFT_OUT_OF_SCOPE = "ERR_SCOPE_SHIFT_OUT_OF_SCOPE"
ERR_SCOPE_DELEGATION_REQUIRED = "ERR_SCOPE_DELEGATION_REQUIRED"
ERR_SCOPE_DELEGATION_EXPIRED = "ERR_SCOPE_DELEGATION_EXPIRED"
ERR_SCOPE_DELEGATION_OUT_OF_SCOPE = "ERR_SCOPE_DELEGATION_OUT_OF_SCOPE"
ERR_SCOPE_HISTORICAL_OUT_OF_SCOPE = "ERR_SCOPE_HISTORICAL_OUT_OF_SCOPE"
ERR_OVERRIDE_HIGHER_SCOPE_LOCK = "ERR_OVERRIDE_HIGHER_SCOPE_LOCK"
ERR_PAYROLL_LOCKED = "ERR_PAYROLL_LOCKED"
ERR_EXPORT_PERMISSION_REQUIRED = "ERR_EXPORT_PERMISSION_REQUIRED"
ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE = "ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE"

ACCESS_SCOPE_ERROR_CODES: frozenset[str] = frozenset(
    {
        ERR_SCOPE_STAFF_OUT_OF_SCOPE,
        ERR_SCOPE_SITE_OUT_OF_SCOPE,
        ERR_SCOPE_SHIFT_OUT_OF_SCOPE,
        ERR_SCOPE_DELEGATION_REQUIRED,
        ERR_SCOPE_DELEGATION_EXPIRED,
        ERR_SCOPE_DELEGATION_OUT_OF_SCOPE,
        ERR_SCOPE_HISTORICAL_OUT_OF_SCOPE,
        ERR_OVERRIDE_HIGHER_SCOPE_LOCK,
        ERR_PAYROLL_LOCKED,
        ERR_EXPORT_PERMISSION_REQUIRED,
        ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
    }
)


class AccessScopeDenied(PermissionError):
    """Raised when a denied PolicyResult must be converted to exception flow."""

    def __init__(self, result: "PolicyResult") -> None:
        self.result = result
        super().__init__(result.message)


@dataclass(frozen=True)
class PolicyResult:
    """Stable allow/deny result for access-scope policies.

    Sensitive workflows must not return bare booleans. This object preserves the
    stable denial code, safe user-facing message and non-sensitive context needed
    by API/HTMX/template callers.
    """

    allowed: bool
    error_code: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    delegation_id: int | None = None
    effective_scope_level: str | None = None
    scope_source: str | None = None

    def __post_init__(self) -> None:
        if self.allowed and self.error_code is not None:
            raise ValueError("Allowed PolicyResult must not include error_code.")
        if not self.allowed:
            if not self.error_code:
                raise ValueError("Denied PolicyResult requires error_code.")
            if self.error_code not in ACCESS_SCOPE_ERROR_CODES:
                raise ValueError(f"Unknown access-scope error_code: {self.error_code}")

    @classmethod
    def allow(
        cls,
        *,
        message: str = "",
        details: dict[str, Any] | None = None,
        delegation_id: int | None = None,
        effective_scope_level: str | None = None,
        scope_source: str | None = None,
    ) -> "PolicyResult":
        return cls(
            allowed=True,
            error_code=None,
            message=message,
            details=dict(details or {}),
            delegation_id=delegation_id,
            effective_scope_level=effective_scope_level,
            scope_source=scope_source,
        )

    @classmethod
    def deny(
        cls,
        error_code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        delegation_id: int | None = None,
        effective_scope_level: str | None = None,
        scope_source: str | None = None,
    ) -> "PolicyResult":
        return cls(
            allowed=False,
            error_code=error_code,
            message=message,
            details=dict(details or {}),
            delegation_id=delegation_id,
            effective_scope_level=effective_scope_level,
            scope_source=scope_source,
        )

    def to_api_response(self, *, request_id: str | None = None) -> dict[str, Any]:
        """Return the standard API/HTMX response shape from the contract."""
        if self.allowed:
            payload: dict[str, Any] = {
                "success": True,
                "message": self.message,
                "details": dict(self.details),
            }
        else:
            payload = {
                "success": False,
                "error_code": self.error_code,
                "message": self.message,
                "details": dict(self.details),
                "request_id": request_id or "",
            }

        if self.delegation_id is not None:
            payload["delegation_id"] = self.delegation_id
        if self.effective_scope_level is not None:
            payload["effective_scope_level"] = self.effective_scope_level
        if self.scope_source is not None:
            payload["scope_source"] = self.scope_source
        return payload

    def raise_if_denied(self) -> None:
        if not self.allowed:
            raise AccessScopeDenied(self)


__all__ = [
    "ACCESS_SCOPE_ERROR_CODES",
    "AccessScopeDenied",
    "PolicyResult",
    "ERR_SCOPE_STAFF_OUT_OF_SCOPE",
    "ERR_SCOPE_SITE_OUT_OF_SCOPE",
    "ERR_SCOPE_SHIFT_OUT_OF_SCOPE",
    "ERR_SCOPE_DELEGATION_REQUIRED",
    "ERR_SCOPE_DELEGATION_EXPIRED",
    "ERR_SCOPE_DELEGATION_OUT_OF_SCOPE",
    "ERR_SCOPE_HISTORICAL_OUT_OF_SCOPE",
    "ERR_OVERRIDE_HIGHER_SCOPE_LOCK",
    "ERR_PAYROLL_LOCKED",
    "ERR_EXPORT_PERMISSION_REQUIRED",
    "ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE",
]
