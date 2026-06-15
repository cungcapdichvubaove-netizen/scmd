"""Digital Twin dataset orchestration."""

from django.db import transaction

from seed.orchestrator.side_effects import suppress_operational_side_effects

from seed.ai_alerts.factories import seed_ai_alerts
from seed.contracts.factories import seed_contracts
from seed.customers.factories import seed_customers
from seed.finance.factories import seed_finance
from seed.hr.factories import seed_hr
from seed.incidents.factories import seed_incidents
from seed.inventory.factories import seed_inventory
from seed.master_data.factories import seed_master_data
from seed.orchestrator.context import DigitalTwinContext
from seed.patrol.factories import seed_patrol_and_attendance
from seed.sites.factories import seed_sites

MODULE_ORDER = [
    "master-data",
    "hr",
    "customers",
    "contracts",
    "sites",
    "inventory",
    "patrol",
    "incidents",
    "ai-alerts",
    "finance",
]


def run_dataset_generation(ctx: DigitalTwinContext, modules=None):
    selected = set(modules or MODULE_ORDER)
    outputs = {}
    if ctx.dry_run:
        return {"dry_run": True, "profile": ctx.profile, "scale": ctx.scale.__dict__}

    # Keep one top-level transaction for small/smoke. Full profile intentionally
    # commits per module to avoid holding long-running locks during load-test seeding.
    atomic = transaction.atomic() if ctx.profile in {"smoke", "small"} else _nullcontext()
    with suppress_operational_side_effects(ctx.suppress_side_effects), atomic:
        if "master-data" in selected:
            outputs["master"] = seed_master_data(ctx)
        else:
            outputs["master"] = seed_master_data(ctx)
        if "hr" in selected:
            outputs["hr"] = seed_hr(ctx, outputs["master"])
        if "customers" in selected:
            outputs["customers"] = seed_customers(ctx, outputs["hr"])
        if "contracts" in selected:
            outputs["contracts"] = seed_contracts(ctx, outputs["customers"])
        if "sites" in selected:
            outputs["sites"] = seed_sites(ctx, outputs["contracts"], outputs["hr"])
        if "inventory" in selected:
            outputs["inventory"] = seed_inventory(ctx, outputs["hr"], outputs["sites"])
        if "patrol" in selected:
            outputs["patrol"] = seed_patrol_and_attendance(ctx, outputs["hr"], outputs["sites"])
        if "incidents" in selected:
            outputs["incidents"] = seed_incidents(ctx, outputs["hr"], outputs["sites"], outputs.get("patrol", {}))
        if "ai-alerts" in selected:
            outputs["ai_alerts"] = seed_ai_alerts(ctx, outputs["sites"])
        if "finance" in selected:
            outputs["finance"] = seed_finance(ctx, outputs["hr"])
    return {"profile": ctx.profile, "counters": ctx.counters, "exports": str(ctx.export_dir)}


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
