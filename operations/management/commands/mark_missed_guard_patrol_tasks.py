# -*- coding: utf-8 -*-
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from operations.application.guard_patrol_use_cases import MarkMissedGuardPatrolTasksUseCase


class Command(BaseCommand):
    help = "Persist trạng thái MISSED cho nhiệm vụ tuần tra đã quá grace deadline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="target_date",
            default=None,
            help="Ngày cần xử lý theo định dạng YYYY-MM-DD. Mặc định là hôm nay.",
        )

    def handle(self, *args, **options):
        raw_date = options.get("target_date")
        try:
            target_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError as exc:
            raise CommandError("--date phải theo định dạng YYYY-MM-DD.") from exc

        summary = MarkMissedGuardPatrolTasksUseCase.execute(
            target_date=target_date,
            system_actor_label="system.mark_missed_guard_patrol_tasks",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Mark missed guard patrol tasks OK: "
                f"date={summary['target_date'].isoformat()} "
                f"updated_tasks={summary['updated_task_count']}"
            )
        )
