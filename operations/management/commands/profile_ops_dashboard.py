# -*- coding: utf-8 -*-
import json
import logging
import re
import time
from collections import Counter
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import ProgrammingError
from django.test.utils import CaptureQueriesContext
from django.utils.dateparse import parse_date

from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase

logger = logging.getLogger(__name__)

SQL_TRUNCATE_LIMIT = 240


def _truncate_sql(sql, limit=SQL_TRUNCATE_LIMIT):
    normalized = " ".join(str(sql or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _pattern_sql(sql):
    normalized = " ".join(str(sql or "").split())
    normalized = re.sub(r"'[^']*'", "'?'", normalized)
    normalized = re.sub(r'"[^"]*"', '"?"', normalized)
    normalized = re.sub(r"\b\d+\b", "?", normalized)
    return _truncate_sql(normalized)


def _query_time_ms(query):
    try:
        return float(query.get("time", 0) or 0) * 1000
    except (TypeError, ValueError):
        return 0.0


class Command(BaseCommand):
    help = "Profile SQL query governance for the Operations Dashboard use case."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="target_date",
            help="Operations date to profile in YYYY-MM-DD format. Defaults to today.",
        )
        parser.add_argument(
            "--username",
            dest="username",
            help="Username used to resolve dashboard permissions. Defaults to first superuser.",
        )
        parser.add_argument(
            "--max-queries",
            dest="max_queries",
            type=int,
            default=50,
            help="Fail when captured SQL query count exceeds this threshold. Default: 50.",
        )
        parser.add_argument(
            "--max-ms",
            dest="max_ms",
            type=int,
            default=800,
            help="Fail when wall time exceeds this threshold in milliseconds. Default: 800.",
        )
        parser.add_argument(
            "--json",
            dest="as_json",
            action="store_true",
            help="Emit machine-readable JSON instead of console text.",
        )

    def _resolve_target_date(self, raw_value):
        if not raw_value:
            return date.today()
        parsed = parse_date(raw_value)
        if parsed is None:
            raise CommandError("--date phải theo định dạng YYYY-MM-DD.")
        return parsed

    def _get_user_model(self):
        return get_user_model()

    def _ensure_postgis_runtime_ready(self):
        if not getattr(settings, "SCMD_DOCKER_PROD_MODE", False):
            return
        engine = connection.settings_dict.get("ENGINE", "")
        if connection.vendor != "postgresql" or engine != "django.contrib.gis.db.backends.postgis":
            raise CommandError(
                "profile_ops_dashboard trong docker-compose.prod.yml phải chạy trên PostGIS thật. "
                f"Detected vendor={connection.vendor!r}, ENGINE={engine!r}."
            )

    def _ensure_user_schema_ready(self):
        user_table = self._get_user_model()._meta.db_table
        existing_tables = set(connection.introspection.table_names())
        if user_table not in existing_tables:
            raise CommandError(
                "Schema auth chưa sẵn sàng cho profile_ops_dashboard: "
                f"thiếu bảng {user_table!r}. "
                "Hãy chạy `docker compose -f docker-compose.prod.yml run --rm migrate` "
                "trước khi profiling dashboard."
            )

    def _resolve_user(self, username):
        user_model = self._get_user_model()
        if username:
            user = user_model.objects.filter(username=username).first()
            if not user:
                raise CommandError(f"Không tìm thấy user --username={username!r}.")
            return user

        user = user_model.objects.filter(is_superuser=True).first()
        if not user:
            raise CommandError("Không tìm thấy tài khoản quản trị để thực hiện profiling.")
        return user

    def _build_report(self, queries, wall_time_ms):
        query_count = len(queries)
        sql_time_ms = sum(_query_time_ms(query) for query in queries)
        python_time_ms = max(wall_time_ms - sql_time_ms, 0.0)

        pattern_counts = Counter(_pattern_sql(query.get("sql", "")) for query in queries)
        duplicate_sql_patterns = [
            {"count": count, "sql": sql}
            for sql, count in pattern_counts.most_common()
            if count > 1
        ][:10]

        slow_sql = [
            {
                "time_ms": round(_query_time_ms(query), 3),
                "sql": _truncate_sql(query.get("sql", "")),
            }
            for query in sorted(queries, key=_query_time_ms, reverse=True)[:10]
        ]

        return {
            "query_count": query_count,
            "sql_time_ms": round(sql_time_ms, 3),
            "wall_time_ms": round(wall_time_ms, 3),
            "python_time_ms": round(python_time_ms, 3),
            "duplicate_sql_patterns": duplicate_sql_patterns,
            "slow_sql": slow_sql,
        }

    def _write_text_report(self, report, target_date, username, tenant_id):
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("KẾT QUẢ PROFILING - SCMD PRO OPERATIONAL TRUTH"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"Tenant:                 {tenant_id}")
        self.stdout.write(f"Ngày vận hành:          {target_date.isoformat()}")
        self.stdout.write(f"User:                   {username}")
        self.stdout.write(f"Tổng số truy vấn SQL:    {report['query_count']}")
        self.stdout.write(f"Tổng thời gian SQL:      {report['sql_time_ms']:.3f}ms")
        self.stdout.write(f"Thời gian thực tế Wall:  {report['wall_time_ms']:.3f}ms")
        self.stdout.write(f"Xử lý logic Python:      {report['python_time_ms']:.3f}ms")
        self.stdout.write("-" * 70)

        duplicates = report["duplicate_sql_patterns"]
        if duplicates:
            self.stdout.write(self.style.WARNING("TOP 10 duplicate_sql_patterns:"))
            for item in duplicates:
                self.stdout.write(f"  - [{item['count']} lần] {item['sql']}")
        else:
            self.stdout.write(self.style.SUCCESS("Không phát hiện mẫu truy vấn trùng lặp."))

        slow_sql = report["slow_sql"]
        if slow_sql:
            self.stdout.write(self.style.WARNING("TOP 10 slow_sql:"))
            for item in slow_sql:
                self.stdout.write(f"  - [{item['time_ms']:.3f}ms] {item['sql']}")
        self.stdout.write("=" * 70 + "\n")

    def handle(self, *args, **options):
        tenant_id = str(getattr(settings, "SCMD_ORGANIZATION_ID", ""))
        target_date = self._resolve_target_date(options.get("target_date"))
        try:
            self._ensure_postgis_runtime_ready()
            self._ensure_user_schema_ready()
            admin_user = self._resolve_user(options.get("username"))
        except ProgrammingError as exc:
            raise CommandError(
                "Schema auth chưa sẵn sàng cho profile_ops_dashboard. "
                "Hãy chạy `docker compose -f docker-compose.prod.yml run --rm migrate` "
                "và kiểm tra lại `python manage.py showmigrations --plan`."
            ) from exc
        max_queries = options["max_queries"]
        max_ms = options["max_ms"]

        start_wall = time.perf_counter()
        try:
            with CaptureQueriesContext(connection) as captured:
                GetOperationsDashboardUseCase.execute(
                    user=admin_user,
                    tenant_id=tenant_id,
                    target_date=target_date,
                )
        except Exception as exc:
            raise CommandError(f"Thực thi Use Case thất bại: {exc}") from exc
        wall_time_ms = (time.perf_counter() - start_wall) * 1000

        report = self._build_report(captured.captured_queries, wall_time_ms)
        report.update(
            {
                "tenant_id": tenant_id,
                "target_date": target_date.isoformat(),
                "username": getattr(admin_user, "username", ""),
                "max_queries": max_queries,
                "max_ms": max_ms,
            }
        )

        if options.get("as_json"):
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self._write_text_report(report, target_date, getattr(admin_user, "username", ""), tenant_id)

        failures = []
        if report["query_count"] > max_queries:
            failures.append(f"query_count={report['query_count']} vượt max_queries={max_queries}")
        if report["wall_time_ms"] > max_ms:
            failures.append(f"wall_time_ms={report['wall_time_ms']:.3f} vượt max_ms={max_ms}")
        if failures:
            raise CommandError("; ".join(failures))
