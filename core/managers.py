# -*- coding: utf-8 -*-
"""
Shared organization-scope managers for the single-organization SCMD ERP runtime.
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


class TenantAwareManager(models.Manager):
    """
    Legacy-name SSOT for organization-scoped queries.

    The current product is single-organization hardened. `tenant_id` remains the
    schema field name, but it is enforced against `SCMD_ORGANIZATION_ID`.
    """

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
