# -*- coding: utf-8 -*-

from unittest import TestCase

from core.policy_result import (
    ACCESS_SCOPE_ERROR_CODES,
    ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
    ERR_SCOPE_SITE_OUT_OF_SCOPE,
    AccessScopeDenied,
    PolicyResult,
)


class PolicyResultTests(TestCase):
    def test_allow_returns_allowed_true_without_error_code(self):
        result = PolicyResult.allow(
            message="Allowed",
            details={"operation": "view_own_profile"},
            effective_scope_level="SELF",
            scope_source="CONSERVATIVE_DEFAULT",
        )

        self.assertTrue(result.allowed)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.message, "Allowed")
        self.assertEqual(result.details["operation"], "view_own_profile")
        self.assertEqual(result.effective_scope_level, "SELF")
        self.assertEqual(result.scope_source, "CONSERVATIVE_DEFAULT")

    def test_deny_returns_allowed_false_and_preserves_context(self):
        result = PolicyResult.deny(
            ERR_SCOPE_SITE_OUT_OF_SCOPE,
            "Mục tiêu này nằm ngoài phạm vi quản lý của bạn.",
            details={"required_scope": "SITE"},
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, ERR_SCOPE_SITE_OUT_OF_SCOPE)
        self.assertEqual(result.message, "Mục tiêu này nằm ngoài phạm vi quản lý của bạn.")
        self.assertEqual(result.details, {"required_scope": "SITE"})

    def test_to_api_response_for_denial_matches_contract_shape(self):
        result = PolicyResult.deny(
            ERR_SCOPE_SITE_OUT_OF_SCOPE,
            "Không có quyền truy cập mục tiêu này.",
            details={"required_scope": "SITE:Mục tiêu A"},
        )

        self.assertEqual(
            result.to_api_response(request_id="req-123"),
            {
                "success": False,
                "error_code": ERR_SCOPE_SITE_OUT_OF_SCOPE,
                "message": "Không có quyền truy cập mục tiêu này.",
                "details": {"required_scope": "SITE:Mục tiêu A"},
                "request_id": "req-123",
            },
        )

    def test_low_privilege_denial_does_not_leak_object_existence(self):
        result = PolicyResult.deny(
            ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
            "Không tìm thấy dữ liệu hoặc bạn không có quyền truy cập.",
            details={"object_type": "staff"},
        )
        payload = result.to_api_response(request_id="req-safe")

        self.assertEqual(payload["error_code"], ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE)
        self.assertNotIn("object_id", payload["details"])
        self.assertNotIn("staff_id", payload["details"])
        self.assertNotIn("site_id", payload["details"])

    def test_raise_if_denied_raises_access_scope_denied(self):
        result = PolicyResult.deny(
            ERR_SCOPE_SITE_OUT_OF_SCOPE,
            "Denied",
        )

        with self.assertRaises(AccessScopeDenied) as context:
            result.raise_if_denied()

        self.assertIs(context.exception.result, result)

    def test_error_code_registry_contains_contract_codes(self):
        expected_codes = {
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
        }

        self.assertEqual(ACCESS_SCOPE_ERROR_CODES, expected_codes)
