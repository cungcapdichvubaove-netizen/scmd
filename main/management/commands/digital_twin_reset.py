"""Reset Digital Twin dataset records."""

from django.core.management.base import BaseCommand

from seed.orchestrator.reset import reset_digital_twin_dataset


class Command(BaseCommand):
    help = "Reset deterministic Digital Twin records without mutating append-only AuditLog."

    def add_arguments(self, parser):
        parser.add_argument("--keep-exports", action="store_true")

    def handle(self, *args, **options):
        reset_digital_twin_dataset(remove_exports=not options["keep_exports"])
        self.stdout.write(self.style.SUCCESS("Digital Twin records reset completed."))
