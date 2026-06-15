# -*- coding: utf-8 -*-
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from operations.application.guard_patrol_use_cases import MaterializeGuardPatrolTasksUseCase


class Command(BaseCommand):
    help = "Materialize nhiệm vụ tuần tra theo lịch vận hành cho một ngày cụ thể."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="target_date",
            default=None,
            help="Ngày cần materialize theo định dạng YYYY-MM-DD. Mặc định là hôm nay.",
        )

    def handle(self, *args, **options):
        raw_date = options.get("target_date")
        try:
            target_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError as exc:
            raise CommandError("--date phải theo định dạng YYYY-MM-DD.") from exc

        summary = MaterializeGuardPatrolTasksUseCase.execute_for_date(
            target_date=target_date,
            system_actor_label="system.materialize_guard_patrol_tasks",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Materialize guard patrol tasks OK: "
                f"date={summary['target_date'].isoformat()} "
                f"eligible_shifts={summary['eligible_shift_count']} "
                f"created_tasks={summary['created_task_count']} "
                f"touched_tasks={summary['touched_task_count']}"
            )
        )
