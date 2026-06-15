"""Generate SCMD Pro Digital Twin datasets."""

from django.core.management.base import BaseCommand, CommandError

from seed.orchestrator.config import SCALES
from seed.orchestrator.context import DigitalTwinContext
from seed.orchestrator.reset import reset_digital_twin_dataset
from seed.orchestrator.runner import MODULE_ORDER, run_dataset_generation


class Command(BaseCommand):
    help = "Generate an idempotent Digital Twin dataset for QA/UAT/performance testing."

    def add_arguments(self, parser):
        parser.add_argument("--profile", choices=sorted(SCALES), default="smoke")
        parser.add_argument("--seed", type=int, default=20260609)
        parser.add_argument("--batch-size", type=int, default=1000)
        parser.add_argument("--reset", action="store_true", help="Reset Digital Twin records before generating.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--allow-side-effects",
            action="store_true",
            help="Allow production Celery/WebSocket/cache signals during seed. Default is disabled for safety.",
        )
        parser.add_argument(
            "--module",
            action="append",
            choices=MODULE_ORDER,
            help="Limit generation to one or more modules. Repeat the flag for multiple modules.",
        )
        parser.add_argument(
            "--allow-full-scale",
            action="store_true",
            help="Required when --profile=full to avoid accidental 500k+ row generation.",
        )

    def handle(self, *args, **options):
        if options["profile"] == "full" and not options["allow_full_scale"]:
            raise CommandError("Full Digital Twin scale requires --allow-full-scale.")
        if options["reset"] and not options["dry_run"]:
            self.stdout.write(self.style.WARNING("Resetting Digital Twin records only; AuditLog is preserved."))
            reset_digital_twin_dataset()
        ctx = DigitalTwinContext(
            profile=options["profile"],
            seed=options["seed"],
            dry_run=options["dry_run"],
            batch_size=options["batch_size"],
            suppress_side_effects=not options["allow_side_effects"],
        )
        result = run_dataset_generation(ctx, modules=options.get("module"))
        self.stdout.write(self.style.SUCCESS("Digital Twin generation completed."))
        self.stdout.write(str(result))
