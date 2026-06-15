# -*- coding: utf-8 -*-
"""Compatibility import for the relocated reconcile_inventory command.

The Django management command lives at
``inventory/management/commands/reconcile_inventory.py``. Keep this shim so any
legacy import path fails safe without duplicating command logic.
"""

from inventory.management.commands.reconcile_inventory import Command

__all__ = ["Command"]
