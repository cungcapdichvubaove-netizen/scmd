# -*- coding: utf-8 -*-
"""Management command for safe inventory reconciliation."""

from django.conf import settings
from django.core.management.base import BaseCommand

from inventory.application.stock_reconciliation_use_case import StockReconciliationUseCase


class Command(BaseCommand):
    help = "Đối soát số liệu tồn kho thực tế và nhật ký giao dịch (dry-run mặc định)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Cập nhật VatTu.so_luong_ton khớp tổng ledger và ghi AuditLog.",
        )
        parser.add_argument(
            "--reason",
            default="",
            help="Lý do nghiệp vụ ghi vào AuditLog khi chạy --fix.",
        )

    def handle(self, *args, **options):
        fix = bool(options["fix"])
        mode = "FIX" if fix else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Đối soát kho SCMD Pro ({mode})..."))

        report = StockReconciliationUseCase.execute(
            fix_discrepancies=fix,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            reason=options.get("reason") or "Inventory reconciliation management command",
        )

        if not report["discrepancies"]:
            self.stdout.write(self.style.SUCCESS(
                f"Đối soát thành công. Đã kiểm tra {report['checked_count']} vật tư. Không có sai lệch."
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"Phát hiện {len(report['discrepancies'])} vật tư sai lệch trên {report['checked_count']} mục."
        ))
        header = f"{'ID':<5} | {'Tên Vật Tư':<30} | {'Hiện tại':<10} | {'Ledger':<10} | {'Lệch':<10}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for item in report["discrepancies"]:
            self.stdout.write(
                f"{item['id']:<5} | {item['name'][:30]:<30} | {item['current']:<10} | {item['expected']:<10} | {item['variance']:<10}"
            )

        if fix:
            self.stdout.write(self.style.SUCCESS(f"Đã cập nhật {report['fixed_count']} vật tư và ghi AuditLog."))
        else:
            self.stdout.write(self.style.WARNING("Dry-run: chưa cập nhật tồn kho. Chạy lại với --fix nếu đã đối chiếu."))
