# -*- coding: utf-8 -*-

from unittest import TestCase

from core.access_scope import ResolvedScope, ScopeLevel, ScopeResolver, ScopeSource, ScopeType


class DummyUser:
    def __init__(self, user_id=1, is_authenticated=True):
        self.pk = user_id
        self.is_authenticated = is_authenticated


class ScopeLevelTests(TestCase):
    def test_scope_level_ordering_required_for_phase_a(self):
        self.assertLess(ScopeLevel.SELF, ScopeLevel.SITE)
        self.assertLess(ScopeLevel.SITE, ScopeLevel.REGION)
        self.assertLess(ScopeLevel.REGION, ScopeLevel.OPERATIONS)
        self.assertLess(ScopeLevel.OPERATIONS, ScopeLevel.EXECUTIVE)

    def test_scope_level_coerce_accepts_string_and_legacy_technical_name(self):
        self.assertEqual(ScopeLevel.coerce("SELF"), ScopeLevel.SELF)
        self.assertEqual(ScopeLevel.coerce("technical"), ScopeLevel.TECHNICAL_ADMIN)


class ScopeResolverTests(TestCase):
    def test_authenticated_user_gets_self_only_conservative_default(self):
        resolved = ScopeResolver.resolve_user_scope(DummyUser(user_id=10))

        self.assertIsInstance(resolved, ResolvedScope)
        self.assertTrue(resolved.is_authenticated)
        self.assertEqual(resolved.user_id, 10)
        self.assertEqual(resolved.effective_scope_level, ScopeLevel.SELF)
        self.assertEqual(resolved.scope_type, ScopeType.SELF)
        self.assertEqual(resolved.scope_source, ScopeSource.CONSERVATIVE_DEFAULT)

    def test_scope_resolver_does_not_open_broad_access_when_data_missing(self):
        user = DummyUser(user_id=11)

        self.assertTrue(ScopeResolver.user_has_scope_level(user, ScopeLevel.SELF))
        self.assertFalse(ScopeResolver.user_has_scope_level(user, ScopeLevel.SITE))
        self.assertFalse(ScopeResolver.user_has_scope_level(user, ScopeLevel.REGION))
        self.assertFalse(ScopeResolver.user_has_scope_level(user, ScopeLevel.OPERATIONS))
        self.assertFalse(ScopeResolver.user_has_scope_level(user, ScopeLevel.EXECUTIVE))

    def test_unauthenticated_user_gets_no_scope(self):
        resolved = ScopeResolver.resolve_user_scope(DummyUser(user_id=12, is_authenticated=False))

        self.assertFalse(resolved.is_authenticated)
        self.assertIsNone(resolved.effective_scope_level)
        self.assertIsNone(resolved.scope_type)
        self.assertFalse(ScopeResolver.user_has_scope_level(DummyUser(is_authenticated=False), ScopeLevel.SELF))

    def test_explain_scope_returns_safe_conservative_details(self):
        explanation = ScopeResolver.explain_scope(DummyUser(user_id=13))

        self.assertEqual(explanation["user_id"], 13)
        self.assertEqual(explanation["effective_scope_level"], "SELF")
        self.assertEqual(explanation["scope_type"], "SELF")
        self.assertEqual(explanation["scope_source"], "CONSERVATIVE_DEFAULT")
        self.assertEqual(explanation["details"]["phase"], "A")
