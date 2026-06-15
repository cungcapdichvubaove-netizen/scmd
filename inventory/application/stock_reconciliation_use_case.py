# -*- coding: utf-8 -*-
"""Safe stock reconciliation application use case for SCMD Pro."""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from inventory.models import VatTu
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog

logger = logging.getLogger(__name__)


class StockReconciliationUseCase:
    """Reconcile VatTu.so_luong_ton against immutable InventoryLedgerEntry.

    Default mode is dry-run. Fix mode is explicit and writes an AuditLog entry
    for every corrected stock item. This use case never accepts arbitrary
    request-supplied tenant scope; callers should pass the fixed organization
    id or let it default to settings.SCMD_ORGANIZATION_ID.
    """

    DEFAULT_REASON = "Inventory reconciliation: align VatTu.so_luong_ton with ledger total"

    @staticmethod
    def execute(
        fix_discrepancies: bool = False,
        *,
        tenant_id=None,
        actor_user=None,
        reason: str = "",
    ):
        scoped_tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        reason = (reason or StockReconciliationUseCase.DEFAULT_REASON).strip()

        if fix_discrepancies:
            with transaction.atomic():
                return StockReconciliationUseCase._run(
                    fix_discrepancies=True,
                    tenant_id=scoped_tenant_id,
                    actor_user=actor_user,
                    reason=reason,
                )

        return StockReconciliationUseCase._run(
            fix_discrepancies=False,
            tenant_id=scoped_tenant_id,
            actor_user=actor_user,
            reason=reason,
        )

    @staticmethod
    def _run(*, fix_discrepancies: bool, tenant_id, actor_user=None, reason: str):
        results = {
            "checked_count": 0,
            "discrepancies": [],
            "fixed_count": 0,
            "mode": "fix" if fix_discrepancies else "dry_run",
            "tenant_id": str(tenant_id),
        }

        ledger_stats = (
            InventoryLedgerEntry.objects.for_tenant(tenant_id)
            .values("vat_tu_id")
            .annotate(ledger_total=Sum("quantity_delta"))
        )
        ledger_map = {item["vat_tu_id"]: item["ledger_total"] or 0 for item in ledger_stats}

        vattu_queryset = VatTu.objects.for_tenant(tenant_id).order_by("pk")
        if fix_discrepancies:
            vattu_queryset = vattu_queryset.select_for_update()

        for vt in vattu_queryset:
            results["checked_count"] += 1
            current_stock = int(vt.so_luong_ton or 0)
            expected_stock = int(ledger_map.get(vt.pk, 0) or 0)

            if current_stock == expected_stock:
                continue

            delta = expected_stock - current_stock
            discrepancy = {
                "id": vt.pk,
                "name": vt.ten_vat_tu,
                "current": current_stock,
                "expected": expected_stock,
                "variance": current_stock - expected_stock,
                "delta": delta,
            }
            results["discrepancies"].append(discrepancy)

            if not fix_discrepancies:
                continue

            logger.warning(
                "[Stock-Reconcile] Fix VatTu %s tenant=%s: %s -> %s",
                vt.pk,
                tenant_id,
                current_stock,
                expected_stock,
            )
            VatTu.objects.for_tenant(tenant_id).filter(pk=vt.pk).update(
                so_luong_ton=expected_stock
            )
            AuditLog.objects.create(
                user=actor_user,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="VatTu",
                object_id=str(vt.pk),
                tenant_id=tenant_id,
                note=reason,
                changes={
                    "old_stock": current_stock,
                    "expected_stock": expected_stock,
                    "delta": delta,
                    "reason": reason,
                    "source": "stock_reconciliation",
                },
            )
            results["fixed_count"] += 1

        return results
