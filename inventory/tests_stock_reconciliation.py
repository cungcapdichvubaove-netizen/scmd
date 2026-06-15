# -*- coding: utf-8 -*-
"""Regression tests for inventory stock reconciliation hardening."""

from __future__ import annotations

from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings

from inventory.application.stock_reconciliation_use_case import StockReconciliationUseCase
from inventory.models import LoaiVatTu, VatTu
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog


ORG_ID = UUID("00000000-0000-0000-0000-000000000936")
OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000937")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class StockReconciliationUseCaseTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="inventory-reconcile")
        self.category = LoaiVatTu.objects.create(tenant_id=ORG_ID, ten_loai="Đồng phục")

    def _item(self, name, stock):
        return VatTu.objects.create(
            tenant_id=ORG_ID,
            loai_vat_tu=self.category,
            ten_vat_tu=name,
            don_vi_tinh="Cái",
            so_luong_ton=stock,
        )

    def _ledger(self, item, qty):
        return InventoryLedgerEntry.objects.create(
            tenant_id=ORG_ID,
            vat_tu=item,
            document_type=InventoryLedgerEntry.DocumentType.RECEIPT,
            movement_type=InventoryLedgerEntry.MovementType.POSTING,
            direction=InventoryLedgerEntry.Direction.IN if qty >= 0 else InventoryLedgerEntry.Direction.OUT,
            quantity_delta=qty,
            stock_before=0,
            stock_after=qty,
            reason="Test ledger",
        )

    def _move_to_other_tenant(self, table_name, pk):
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table_name} SET tenant_id = %s WHERE id = %s",
                [str(OTHER_ORG_ID), pk],
            )

    def _fetch_stock(self, pk):
        with connection.cursor() as cursor:
            cursor.execute("SELECT so_luong_ton FROM inventory_vattu WHERE id = %s", [pk])
            return cursor.fetchone()[0]

    def test_dry_run_detects_discrepancy_without_changing_stock(self):
        item = self._item("Áo bảo vệ", 10)
        self._ledger(item, 7)

        result = StockReconciliationUseCase.execute(fix_discrepancies=False, tenant_id=ORG_ID)

        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(len(result["discrepancies"]), 1)
        item.refresh_from_db()
        self.assertEqual(item.so_luong_ton, 10)

    def test_fix_mode_updates_stock_and_writes_audit_log(self):
        item = self._item("Mũ bảo hộ", 2)
        self._ledger(item, 5)

        result = StockReconciliationUseCase.execute(
            fix_discrepancies=True,
            tenant_id=ORG_ID,
            actor_user=self.user,
            reason="Đối soát kho cuối tháng",
        )

        self.assertEqual(result["fixed_count"], 1)
        item.refresh_from_db()
        self.assertEqual(item.so_luong_ton, 5)
        audit = AuditLog.objects.get(module="inventory", model_name="VatTu", object_id=str(item.pk))
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.changes["old_stock"], 2)
        self.assertEqual(audit.changes["expected_stock"], 5)
        self.assertEqual(audit.changes["delta"], 3)

    def test_fix_mode_does_not_update_cross_tenant_rows(self):
        current_item = self._item("Bộ đàm hiện tại", 1)
        other_item = self._item("Bộ đàm tenant khác", 9)
        self._ledger(current_item, 4)
        self._ledger(other_item, 12)
        self._move_to_other_tenant("inventory_vattu", other_item.pk)
        self._move_to_other_tenant("inventory_inventoryledgerentry", other_item.ledger_entries.first().pk)

        StockReconciliationUseCase.execute(fix_discrepancies=True, tenant_id=ORG_ID)

        current_item.refresh_from_db()
        self.assertEqual(current_item.so_luong_ton, 4)
        self.assertEqual(self._fetch_stock(other_item.pk), 9)

    def test_matching_ledger_total_has_no_discrepancy(self):
        item = self._item("Dùi cui", 3)
        self._ledger(item, 1)
        self._ledger(item, 2)

        result = StockReconciliationUseCase.execute(tenant_id=ORG_ID)

        self.assertEqual(result["discrepancies"], [])
        self.assertEqual(result["fixed_count"], 0)

    def test_management_command_defaults_to_dry_run(self):
        item = self._item("Áo mưa", 10)
        self._ledger(item, 1)

        call_command("reconcile_inventory", verbosity=0)

        item.refresh_from_db()
        self.assertEqual(item.so_luong_ton, 10)
