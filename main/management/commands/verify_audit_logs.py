# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Management Command: verify_audit_logs.
Description: Quét toàn bộ AuditLog để kiểm tra tính toàn vẹn bằng checksum.
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from main.models import AuditLog

class Command(BaseCommand):
    help = _('Quét toàn bộ AuditLog để kiểm tra tính toàn vẹn bằng checksum.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(_("Bắt đầu kiểm tra tính toàn vẹn của AuditLog...")))

        total_logs = AuditLog.objects.count()
        compromised_logs = []

        for i, log_entry in enumerate(AuditLog.objects.all().select_related('user')):
            if i % 1000 == 0 and i > 0:
                self.stdout.write(f"Đã kiểm tra {i}/{total_logs} bản ghi...")

            if not log_entry.checksum:
                compromised_logs.append({
                    'id': log_entry.id,
                    'user': log_entry.user.username if log_entry.user else _("Hệ thống"),
                    'action': log_entry.action,
                    'timestamp': log_entry.timestamp,
                    'reason': _("Không có checksum")
                })
                continue

            calculated_checksum = log_entry.generate_checksum()
            if log_entry.checksum != calculated_checksum:
                compromised_logs.append({
                    'id': log_entry.id,
                    'user': log_entry.user.username if log_entry.user else _("Hệ thống"),
                    'action': log_entry.action,
                    'timestamp': log_entry.timestamp,
                    'reason': _("Checksum không khớp")
                })
        
        if compromised_logs:
            self.stdout.write(self.style.ERROR(_("\n--- PHÁT HIỆN BẢN GHI AUDIT LOG BỊ SAI LỆCH ---")))
            for entry in compromised_logs:
                self.stdout.write(self.style.WARNING(f"ID: {entry['id']} | User: {entry['user']} | Action: {entry['action']} | Time: {entry['timestamp']} | Lý do: {entry['reason']}"))
            self.stdout.write(self.style.ERROR(f"\nTổng cộng {len(compromised_logs)}/{total_logs} bản ghi Audit Log bị sai lệch."))
        else:
            self.stdout.write(self.style.SUCCESS(_("\n✅ Tất cả AuditLog đều hợp lệ. Không phát hiện sai lệch.")))

        return compromised_logs