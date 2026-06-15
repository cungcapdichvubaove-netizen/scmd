# -*- coding: utf-8 -*-
"""
Cache namespace helpers for operations dashboard data.

Versioned keys allow safe invalidation across Django cache backends without
relying on wildcard delete support.
"""

import hashlib

from django.core.cache import cache
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy


DASHBOARD_CACHE_NAMESPACE = "operations:dashboard_data"
DASHBOARD_CACHE_VERSION_KEY = f"{DASHBOARD_CACHE_NAMESPACE}:version"


def get_dashboard_cache_version():
    version = cache.get(DASHBOARD_CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(DASHBOARD_CACHE_VERSION_KEY, version, None)
    return version


def _hash_scope_values(values):
    raw = ",".join(str(value) for value in values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _scoped_target_hash(user):
    site_ids = list(
        SiteVisibilityPolicy.managed_sites(user)
        .order_by("id")
        .values_list("id", flat=True)
    )
    return _hash_scope_values(site_ids), len(site_ids)


def resolve_dashboard_cache_scope(user, *, tenant_id=None):
    """Return a cache scope descriptor that can be safely shared.

    Global dashboard viewers share one organization-scoped key. Region/team
    viewers share only when their resolved target id set is identical. Unknown
    or alias-only viewers fall back to a user-specific key to avoid data leaks.
    """

    tenant_scope = tenant_id or "org"
    if getattr(user, "is_superuser", False):
        return f"org:{tenant_scope}:global:superuser"
    if has_role(user, "ban_giam_doc"):
        return f"org:{tenant_scope}:global:ban_giam_doc"
    if getattr(user, "is_staff", False):
        return f"org:{tenant_scope}:global:staff"

    if has_role(user, "quan_ly_vung") or has_role(user, "doi_truong"):
        try:
            scope_hash, scope_count = _scoped_target_hash(user)
        except Exception:
            return f"org:{tenant_scope}:user:{getattr(user, 'id', 'anonymous')}"
        role_scope = "quan_ly_vung" if has_role(user, "quan_ly_vung") else "doi_truong"
        return f"org:{tenant_scope}:scoped:{role_scope}:{scope_count}:{scope_hash}"

    return f"org:{tenant_scope}:user:{getattr(user, 'id', 'anonymous')}"


def build_dashboard_cache_key(*, user=None, user_id=None, target_date=None, muc_tieu_id=None, tenant_id=None, dashboard_name="operations"):
    version = get_dashboard_cache_version()
    target_scope = muc_tieu_id or "all"
    if user is not None:
        scope = resolve_dashboard_cache_scope(user, tenant_id=tenant_id)
    else:
        scope = f"org:{tenant_id or 'org'}:user:{user_id or 'anonymous'}"
    return (
        f"{DASHBOARD_CACHE_NAMESPACE}:v{version}:dashboard:{dashboard_name}:"
        f"{scope}:d:{target_date}:m:{target_scope}"
    )


def invalidate_dashboard_cache():
    try:
        cache.incr(DASHBOARD_CACHE_VERSION_KEY)
    except ValueError:
        current_version = cache.get(DASHBOARD_CACHE_VERSION_KEY, 1)
        cache.set(DASHBOARD_CACHE_VERSION_KEY, current_version + 1, None)
