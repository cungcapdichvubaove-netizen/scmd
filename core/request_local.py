"""Request-local cache helpers for per-user scope computations.

SCMD Pro keeps authorization scope strict per user. These helpers cache
scope-derived querysets on the authenticated user object for the lifetime of a
single request only; they do not widen visibility across users or requests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar


T = TypeVar("T")
_CACHE_ATTR = "_scmd_request_local_cache"


def get_request_local_value(user: Any, cache_key: tuple[Any, ...], builder: Callable[[], T]) -> T:
    """Return a request-local cached value attached to ``user``.

    Django instantiates a fresh authenticated user object per request in the
    normal session flow, so storing ephemeral scope results here avoids
    duplicate policy queries within the same response without leaking them to
    other users.
    """

    if user is None:
        return builder()

    cache = getattr(user, _CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(user, _CACHE_ATTR, cache)

    if cache_key not in cache:
        cache[cache_key] = builder()
    return cache[cache_key]
