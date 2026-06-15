# -*- coding: utf-8 -*-
"""
Cache namespace helpers for inventory dashboard and inventory reports.

Versioned keys keep invalidation backend-compatible across cache backends that
do not implement wildcard delete semantics.
"""

from django.core.cache import cache


INVENTORY_CACHE_NAMESPACE = "inventory"
INVENTORY_DASHBOARD_VERSION_KEY = f"{INVENTORY_CACHE_NAMESPACE}:dashboard:version"
INVENTORY_CATEGORY_VERSION_KEY = f"{INVENTORY_CACHE_NAMESPACE}:categories:version"


def _get_cache_version(version_key):
    version = cache.get(version_key)
    if version is None:
        version = 1
        cache.set(version_key, version, None)
    return version


def _invalidate_versioned_namespace(version_key):
    try:
        cache.incr(version_key)
    except ValueError:
        current_version = cache.get(version_key, 1)
        cache.set(version_key, current_version + 1, None)


def build_dashboard_cache_key(org_id, user_id=None):
    """Build a versioned inventory dashboard cache key.

    Backward compatible:
    - old callers passed only ``user_id``; that value remains part of the key.
    - scoped callers pass ``org_id, user_id`` to avoid cross-user/cache leakage.
    """
    version = _get_cache_version(INVENTORY_DASHBOARD_VERSION_KEY)
    if user_id is None:
        return f"{INVENTORY_CACHE_NAMESPACE}:dashboard:v{version}:u{org_id}"
    return f"{INVENTORY_CACHE_NAMESPACE}:dashboard:v{version}:org:{org_id}:u:{user_id}"


def build_category_cache_key(org_id, user_id=None):
    """Build a versioned inventory category cache key scoped by organization/user."""
    version = _get_cache_version(INVENTORY_CATEGORY_VERSION_KEY)
    if user_id is None:
        return f"{INVENTORY_CACHE_NAMESPACE}:categories:v{version}:u{org_id}"
    return f"{INVENTORY_CACHE_NAMESPACE}:categories:v{version}:org:{org_id}:u:{user_id}"


def invalidate_dashboard_cache():
    _invalidate_versioned_namespace(INVENTORY_DASHBOARD_VERSION_KEY)


def invalidate_category_cache():
    _invalidate_versioned_namespace(INVENTORY_CATEGORY_VERSION_KEY)


def invalidate_inventory_cache():
    invalidate_dashboard_cache()
    invalidate_category_cache()
