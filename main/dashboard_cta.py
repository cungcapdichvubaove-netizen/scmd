"""Small helpers for dashboard CTAs.

Dashboard templates must not render fake actions. These helpers keep URL
resolution and dashboard-route authorization in one place without widening
backend permissions.
"""

from django.urls import NoReverseMatch, reverse
from rolepermissions.checkers import has_role

from main.dashboard_router import DashboardRouter


FIELD_OR_EXECUTIVE_ROLES_WITHOUT_ADMIN_CTA = (
    "ban_giam_doc",
    "nghiep_vu",
    "quan_ly_vung",
    "doi_truong",
    "nhan_vien_bao_ve",
)


def reverse_or_none(viewname, *, args=None, kwargs=None):
    """Return a resolved URL or None when the route is unavailable."""
    try:
        return reverse(viewname, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return None


def can_render_admin_cta(user, permission_codename):
    """Return whether a dashboard may render a Django Admin CTA.

    Admin CTAs require authenticated staff console access and the exact Django
    model permission. Field/executive business workspaces must use policy-aware
    dashboard/API routes instead of linking directly into Admin mutation pages.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_staff", False):
        return False
    if not user.has_perm(permission_codename):
        return False
    if not getattr(user, "is_superuser", False) and has_role(user, FIELD_OR_EXECUTIVE_ROLES_WITHOUT_ADMIN_CTA):
        return False
    return True


def admin_url_if_permitted(user, viewname, permission_codename, *, args=None, kwargs=None):
    """Resolve an admin URL only when the caller may use Django Admin.

    This prevents dashboard CTAs from linking non-staff business users or
    field/executive roles into admin login/403 pages. Superusers naturally pass
    ``has_perm``. Missing routes return ``None``.
    """
    if not can_render_admin_cta(user, permission_codename):
        return None
    return reverse_or_none(viewname, args=args, kwargs=kwargs)


def route_url_if_permitted(user, viewname, permission_check, *, args=None, kwargs=None):
    """Resolve a non-dashboard route only when its explicit policy permits it."""
    if not getattr(user, "is_authenticated", False):
        return None
    if not permission_check(user):
        return None
    return reverse_or_none(viewname, args=args, kwargs=kwargs)


def dashboard_route_url(user, route_name, *, viewname=None, args=None, kwargs=None):
    """Resolve a dashboard URL only if the user can access that dashboard route."""
    if not DashboardRouter.user_can_access(user, route_name):
        return None
    return reverse_or_none(viewname or route_name, args=args, kwargs=kwargs)
