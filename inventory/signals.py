# -*- coding: utf-8 -*-
"""
Inventory cache invalidation signals.

Inventory views cache dashboard aggregates and category master data. These
signals invalidate by namespace version so the logic remains compatible across
cache backends.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache_utils import invalidate_inventory_cache
from .models import (
    ChiTietPhieuNhap,
    ChiTietPhieuXuat,
    LoaiVatTu,
    PhieuNhap,
    PhieuXuat,
    VatTu,
)

logger = logging.getLogger(__name__)


def _schedule_inventory_cache_invalidation():
    transaction.on_commit(invalidate_inventory_cache)


@receiver([post_save, post_delete], sender=PhieuNhap)
@receiver([post_save, post_delete], sender=ChiTietPhieuNhap)
@receiver([post_save, post_delete], sender=PhieuXuat)
@receiver([post_save, post_delete], sender=ChiTietPhieuXuat)
@receiver([post_save, post_delete], sender=VatTu)
@receiver([post_save, post_delete], sender=LoaiVatTu)
def invalidate_inventory_dashboard_cache(sender, instance, **kwargs):
    """
    Invalidate inventory caches after committed stock or master-data changes.
    """
    try:
        _schedule_inventory_cache_invalidation()
        logger.info(
            "[Cache-Invalidation] Inventory cache invalidated after %s change.",
            sender.__name__,
        )
    except Exception:
        logger.exception(
            "[Cache-Error] Failed to schedule inventory cache invalidation."
        )
