# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
Shared organization-scope managers for the single-organization SCMD Pro runtime.
"""

import logging
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, ValidationError
=======
Shared organization-scope managers for the single-organization SCMD ERP runtime.
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.db import models

logger = logging.getLogger(__name__)


<<<<<<< HEAD
def organization_id():
    """Return the fixed organization scope for single-organization runtime data."""
    if not hasattr(settings, "SCMD_ORGANIZATION_ID"):
        raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
    return settings.SCMD_ORGANIZATION_ID


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class TenantAwareManager(models.Manager):
    """
    Legacy-name SSOT for organization-scoped queries.

    The current product is single-organization hardened. `tenant_id` remains the
    schema field name, but it is enforced against `SCMD_ORGANIZATION_ID`.
    """

<<<<<<< HEAD
    @staticmethod
    def _organization_id():
        if not hasattr(settings, "SCMD_ORGANIZATION_ID"):
            raise ImproperlyConfigured(
                "SCMD_ORGANIZATION_ID is not defined in settings."
            )
        return settings.SCMD_ORGANIZATION_ID

    def get_queryset(self):
        """Return the default queryset constrained to SCMD_ORGANIZATION_ID when possible.

        This is the low-level organization guard for TenantScopedModel records.
        It intentionally filters only models that physically own a ``tenant_id``
        field. Models such as ``clients.MucTieu`` are scoped indirectly through
        their own manager because the organization id lives on ``HopDong``.
        """
        queryset = super().get_queryset()
        try:
            self.model._meta.get_field("tenant_id")
        except FieldDoesNotExist:
            return queryset
        return queryset.filter(tenant_id=self._organization_id())

    def bulk_create(self, objs, *args, **kwargs):
        """Apply the fixed organization scope for bulk inserts.

        Django bulk_create() intentionally bypasses model.save(), so this guard
        prevents organization-scoped records from receiving the field default
        instead of the configured SCMD organization id.
        """
        organization_id = self._organization_id()
        for obj in objs:
            if hasattr(obj, "tenant_id"):
                obj.tenant_id = organization_id
        return super().bulk_create(objs, *args, **kwargs)

    def for_current(self):
        """Return records for the configured single organization.

        This shorthand keeps runtime code aligned with the single-organization
        contract. The database field remains named `tenant_id` for legacy
        compatibility, but queries must resolve to SCMD_ORGANIZATION_ID.
        """
        return self.for_tenant(self._organization_id())

    def selected_from_queryset(self, queryset):
        """Re-read a selected admin queryset through the organization-scoped manager.

        Admin bulk actions receive a queryset from the changelist. Re-reading by
        primary key through ``for_current()`` keeps organization scoping in the
        manager SSOT while preserving the selected object set. This method is
        intentionally organization-scope only; object/action authorization must
        remain in the relevant policy/use case layer.
        """
        if queryset is None:
            return self.for_current().none()
        selected_ids = queryset.values_list("pk", flat=True)
        return self.for_current().filter(pk__in=selected_ids)

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def for_tenant(self, tenant_id):
        if not hasattr(settings, "SCMD_ORGANIZATION_ID"):
            raise ImproperlyConfigured(
                "SCMD_ORGANIZATION_ID is not defined in settings."
            )

        if not tenant_id:
            logger.critical(
                "SECURITY ALERT: organization-scoped query attempted without tenant_id."
            )
            return self.get_queryset().none()

        if str(tenant_id) != str(settings.SCMD_ORGANIZATION_ID):
            logger.critical(
                "SECURITY ALERT: attempted cross-organization query for tenant_id=%s; "
                "expected=%s",
                tenant_id,
                settings.SCMD_ORGANIZATION_ID,
            )
            return self.get_queryset().none()

        return self.get_queryset().filter(tenant_id=tenant_id)


OrganizationScopedManager = TenantAwareManager
<<<<<<< HEAD



class TenantScopedModel(models.Model):
    """
    Abstract base model for single-organization scoped runtime data.

    `tenant_id` is a legacy schema name. It represents the fixed SCMD
    organization scope configured by `SCMD_ORGANIZATION_ID`, not a SaaS tenant
    supplied by requests or payloads.
    """

    tenant_id = models.UUIDField(
        "Tenant ID",
        db_index=True,
        default=organization_id,
        editable=False,
    )

    objects = TenantAwareManager()

    class Meta:
        abstract = True

    @staticmethod
    def organization_id():
        return organization_id()

    def clean(self):
        organization_id = self.organization_id()
        if self.tenant_id and str(self.tenant_id) != str(organization_id):
            raise ValidationError(
                f"Tenant ID must be {organization_id} for this organization."
            )
        super().clean()

    def save(self, *args, **kwargs):
        self.tenant_id = self.organization_id()
        super().save(*args, **kwargs)



class MucTieuManager(TenantAwareManager):
    """Organization-scoped manager for targets scoped through HopDong."""

    def for_tenant(self, tenant_id):
        if not hasattr(settings, "SCMD_ORGANIZATION_ID"):
            raise ImproperlyConfigured(
                "SCMD_ORGANIZATION_ID is not defined in settings."
            )
        if not tenant_id:
            logger.critical(
                "SECURITY ALERT: target query attempted without tenant_id."
            )
            return self.get_queryset().none()
        if str(tenant_id) != str(settings.SCMD_ORGANIZATION_ID):
            logger.critical(
                "SECURITY ALERT: attempted cross-organization target query for tenant_id=%s; expected=%s",
                tenant_id,
                settings.SCMD_ORGANIZATION_ID,
            )
            return self.get_queryset().none()
        return self.get_queryset().filter(hop_dong__tenant_id=tenant_id)

    def get_queryset(self):
        return (
            models.Manager.get_queryset(self)
            .select_related("hop_dong")
            .filter(hop_dong__tenant_id=self._organization_id())
        )


class ViTriChotManager(TenantAwareManager):
    """Shared manager for post/location queries."""

    def get_queryset(self):
        return super().get_queryset().select_related("muc_tieu", "muc_tieu__hop_dong")


class PhanCongManager(TenantAwareManager):
    """Shared manager for shift assignment queries with N+1 guard."""

    def get_queryset(self):
        return super().get_queryset().select_related(
            "nhan_vien",
            "ca_lam_viec",
            "vi_tri_chot__muc_tieu",
            "vi_tri_chot__muc_tieu__hop_dong",
            "chamcong",
        )


class ChiTietLuongManager(TenantAwareManager):
    """Shared manager for payroll detail queries with N+1 guard."""

    def get_queryset(self):
        return super().get_queryset().select_related("nhan_vien", "bang_luong")
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
