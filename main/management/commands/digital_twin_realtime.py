"""Run realtime Digital Twin simulator."""

from django.core.management.base import BaseCommand

from seed.realtime.simulator import REALTIME_PROFILES, run_realtime_simulation


class Command(BaseCommand):
    help = "Emit realtime GPS/patrol/camera/incident/attendance synthetic events."

    def add_arguments(self, parser):
        parser.add_argument("--level", choices=sorted(REALTIME_PROFILES), default="LOW")
        parser.add_argument("--ticks", type=int, default=10)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        total = run_realtime_simulation(
            level=options["level"],
            ticks=options["ticks"],
            dry_run=options["dry_run"],
            stdout=self.stdout,
        )
        self.stdout.write(self.style.SUCCESS(f"Realtime simulator emitted {total} events."))
