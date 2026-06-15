# -*- coding: utf-8 -*-
import uuid
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings

class Command(BaseCommand):
    """
    SCMD Pro Repair Tool
    -------------------
    Tự động sửa lỗi tenant_id để đảm bảo tính nhất quán của tổ chức.
    """
    help = 'Tự động sửa các bản ghi có tenant_id sai lệch về giá trị cấu hình hệ thống.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- SCMD Pro: Bắt đầu sửa lỗi tính toàn vẹn ---"))

        target_tenant_id_str = getattr(settings, 'SCMD_ORGANIZATION_ID', None)
        if not target_tenant_id_str:
            self.stderr.write(self.style.ERROR("LỖI: SCMD_ORGANIZATION_ID chưa được thiết lập."))
            return

        target_uuid = uuid.UUID(str(target_tenant_id_str))
        total_fixed = 0

        all_models = apps.get_models()
        for model in all_models:
            field_names = [f.name for f in model._meta.fields]
            if 'tenant_id' not in field_names:
                continue

            # AuditLog is append-only. Do not mutate historical audit records;
            # integrity verification must report mismatches instead.
            if model._meta.app_label == "main" and model.__name__ == "AuditLog":
                count = model.objects.exclude(tenant_id=target_uuid).count()
                if count > 0:
                    self.stdout.write(self.style.WARNING(
                        f"Bỏ qua {count} bản ghi main.AuditLog lệch tenant_id vì AuditLog là append-only."
                    ))
                continue

            # Tìm các bản ghi sai lệch
            bad_records = model.objects.exclude(tenant_id=target_uuid)
            count = bad_records.count()

            if count > 0:
                self.stdout.write(f"Đang sửa {count} bản ghi tại {model._meta.app_label}.{model.__name__}...")
                
                # Chúng ta cần gọi .save() từng bản ghi để trigger logic generate_checksum 
                # (đặc biệt quan trọng với AuditLog)
                for obj in bad_records:
                    try:
                        # Phương thức save() mới sẽ tự động gán lại tenant_id đúng
                        obj.save()
                        total_fixed += 1
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"  - Lỗi khi sửa PK {obj.pk}: {str(e)}"))
                
                self.stdout.write(self.style.SUCCESS(f"  -> Đã sửa xong {model.__name__}"))

        if total_fixed > 0:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nTHÀNH CÔNG: Đã sửa tổng cộng {total_fixed} bản ghi."))
        else:
            self.stdout.write(self.style.SUCCESS("\nKhông tìm thấy bản ghi nào cần sửa."))

        self.stdout.write(self.style.MIGRATE_HEADING("--- Hoàn tất ---"))