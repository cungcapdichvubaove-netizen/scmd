# -*- coding: utf-8 -*-
"""
SCMD Pro - Security & Release Checks
-----------------------------------
Custom system checks to enforce production security invariants.
"""

import os
from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, register
from django.urls import NoReverseMatch, reverse

from config.settings import is_insecure_default


def _is_production_environment():
    return os.environ.get("ENVIRONMENT", "development").lower() == "production"


_DANGEROUS_ALLOWED_HOSTS = {"*", "localhost", "127.0.0.1", "0.0.0.0"}
_LOCAL_ORIGIN_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def _normalize_host(value):
    return (value or "").strip().lower()


def _normalize_origin(value):
    return (value or "").strip().lower()


def _host_without_port(value):
    host = _normalize_host(value)
    if host.startswith("[") and "]" in host:
        return host.split("]", 1)[0] + "]"
    return host.split(":", 1)[0]


def _collect_insecure_allowed_hosts(hosts):
    insecure_hosts = []
    for host in hosts or []:
        normalized = _normalize_host(host)
        if not normalized:
            continue
        if normalized in _DANGEROUS_ALLOWED_HOSTS or _host_without_port(normalized) in _LOCAL_ORIGIN_HOSTS:
            insecure_hosts.append(host)
    return insecure_hosts


def _origin_is_insecure(origin):
    normalized = _normalize_origin(origin)
    if not normalized:
        return False

    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if host in _LOCAL_ORIGIN_HOSTS:
        return True
    if parsed.scheme != "https":
        return True
    return False


def _collect_insecure_origins(origins):
    return [origin for origin in origins or [] if _origin_is_insecure(origin)]


@register()
def check_production_security_settings(app_configs, **kwargs):
    """
    Fail fast when production security invariants drift.

    This check intentionally covers only deterministic application/runtime
    settings. Nginx/private-media routing is locked separately by static tests.
    """
    if not _is_production_environment():
        return []

    errors = []

    if settings.DEBUG:
        errors.append(
            Error(
                "DEBUG mode is enabled in a production environment.",
                hint="Set DEBUG=False for production deployments.",
                id="scmd.E001",
            )
        )

    insecure_allowed_hosts = _collect_insecure_allowed_hosts(settings.ALLOWED_HOSTS)
    if not settings.ALLOWED_HOSTS or insecure_allowed_hosts:
        errors.append(
            Error(
                "ALLOWED_HOSTS contains insecure development values in a production environment.",
                hint=(
                    "Set explicit production hostnames only. "
                    f"Invalid values: {', '.join(map(str, insecure_allowed_hosts or settings.ALLOWED_HOSTS))}"
                ),
                id="scmd.E002",
            )
        )

    if is_insecure_default(
        settings.SECRET_KEY,
        insecure_defaults=(
            "django-insecure-local-dev-key",
            "your-very-secret-key-here-change-this-in-production!",
            "change-me",
        ),
    ):
        errors.append(
            Error(
                "SECRET_KEY is still using a development placeholder in production.",
                hint="Provide a high-entropy SECRET_KEY through environment variables.",
                id="scmd.E003",
            )
        )

    dangerous_files = ("reset_project.py", "reset_db.sh")
    for filename in dangerous_files:
        if os.path.exists(os.path.join(settings.BASE_DIR, filename)):
            errors.append(
                Error(
                    f"Dangerous reset script '{filename}' is present in a production image.",
                    hint="Remove reset/bootstrap destroy helpers from the production artifact.",
                    id="scmd.E004",
                )
            )

    insecure_cors_origins = _collect_insecure_origins(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    if insecure_cors_origins:
        errors.append(
            Error(
                "CORS_ALLOWED_ORIGINS contains development or non-HTTPS origins in production.",
                hint=(
                    "Set CORS_ALLOWED_ORIGINS to explicit HTTPS production domains only. "
                    f"Invalid origins: {', '.join(insecure_cors_origins)}"
                ),
                id="scmd.E005",
            )
        )

    insecure_csrf_origins = _collect_insecure_origins(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))
    if insecure_csrf_origins:
        errors.append(
            Error(
                "CSRF_TRUSTED_ORIGINS contains development or non-HTTPS origins in production.",
                hint=(
                    "Set CSRF_TRUSTED_ORIGINS to explicit HTTPS production domains only. "
                    f"Invalid origins: {', '.join(insecure_csrf_origins)}"
                ),
                id="scmd.E012",
            )
        )

    if not settings.SECURE_SSL_REDIRECT:
        errors.append(
            Error(
                "SECURE_SSL_REDIRECT is disabled in production.",
                hint="Enable HTTPS redirect unless a documented front-proxy exception exists.",
                id="scmd.E006",
            )
        )

    if not settings.SESSION_COOKIE_SECURE:
        errors.append(
            Error(
                "SESSION_COOKIE_SECURE is disabled in production.",
                hint="Mark session cookies secure in production deployments.",
                id="scmd.E007",
            )
        )

    if not settings.CSRF_COOKIE_SECURE:
        errors.append(
            Error(
                "CSRF_COOKIE_SECURE is disabled in production.",
                hint="Mark CSRF cookies secure in production deployments.",
                id="scmd.E008",
            )
        )

    try:
        media_auth_url = reverse("internal_media_auth")
    except NoReverseMatch:
        errors.append(
            Error(
                "Internal media authorization route is not registered.",
                hint="Wire '/_internal/media-auth/' in config/urls.py for Nginx auth_request.",
                id="scmd.E009",
            )
        )
    else:
        if media_auth_url != "/_internal/media-auth/":
            errors.append(
                Error(
                    "Internal media authorization route does not match the locked deploy contract.",
                    hint="Keep the route path exactly '/_internal/media-auth/' for Nginx auth_request.",
                    id="scmd.E010",
                )
            )

    return errors


@register()
def check_manager_ssot_compliance(app_configs, **kwargs):
    """
    Ensure domain models keep organization-scope manager ownership in core.
    """
    from django.apps import apps

    from core.managers import TenantAwareManager, TenantScopedModel

    errors = []
    internal_apps = ["main", "users", "clients", "operations", "inventory", "inspection", "accounting"]

    for model in apps.get_models():
        if model._meta.app_label not in internal_apps:
            continue

        if issubclass(model, TenantScopedModel) and model is not TenantScopedModel:
            if not isinstance(model.objects, TenantAwareManager):
                errors.append(
                    Error(
                        f"Model '{model._meta.label}' does not use TenantAwareManager as its default manager.",
                        hint=(
                            f"Declare 'objects = TenantAwareManager()' on model "
                            f"'{model.__name__}' in {model._meta.app_label}/models.py."
                        ),
                        id="scmd.E011",
                    )
                )

    return errors
