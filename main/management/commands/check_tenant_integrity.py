# -*- coding: utf-8 -*-
import uuid
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

class Command(BaseCommand):
    """
    SCMD Pro Integrity Tool
    -----------------------
    Kiểm tra tính toàn vẹn của organization scope (tenant_id).
    Đảm bảo mọi bản ghi tuân thủ Single-organization guard theo WHITEPAPER.md.
    """
    help = 'Kiểm tra tính toàn vẹn của tenant_id trên toàn bộ các model nghiệp vụ của SCMD Pro.'

    @staticmethod
    def _has_physical_tenant_column(model):
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table_name)
            }
        return "tenant_id" in columns

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- SCMD Pro: Bắt đầu kiểm tra tính toàn vẹn Tenant ID ---"))

        target_tenant_id_str = getattr(settings, 'SCMD_ORGANIZATION_ID', None)
        if not target_tenant_id_str:
            self.stderr.write(self.style.ERROR("LỖI: SCMD_ORGANIZATION_ID chưa được thiết lập trong settings."))
            return

        try:
            target_uuid = uuid.UUID(str(target_tenant_id_str))
        except ValueError:
            self.stderr.write(self.style.ERROR(f"LỖI: SCMD_ORGANIZATION_ID '{target_tenant_id_str}' không đúng định dạng UUID."))
            return

        self.stdout.write(f"Tenant ID mục tiêu: {self.style.SUCCESS(str(target_uuid))}")
        
        inconsistent_models = 0
        total_inconsistent_records = 0
        schema_drift_models = []

        # Lấy tất cả các model được đăng ký trong hệ thống
        all_models = apps.get_models()

        for model in all_models:
            # Chỉ kiểm tra các model có trường 'tenant_id'
            field_names = [f.name for f in model._meta.fields]
            if 'tenant_id' not in field_names:
                continue

            self.stdout.write(f"Đang quét model: {model._meta.app_label}.{model.__name__}...", ending="")

            try:
                if not self._has_physical_tenant_column(model):
                    schema_drift_models.append(f"{model._meta.app_label}.{model.__name__}")
                    self.stdout.write(self.style.WARNING(" BỎ QUA (schema drift: thiếu cột tenant_id trong DB)"))
                    continue
            except (ProgrammingError, OperationalError):
                schema_drift_models.append(f"{model._meta.app_label}.{model.__name__}")
                self.stdout.write(self.style.WARNING(" BỎ QUA (không introspect được bảng DB hiện tại)"))
                continue

            # Tìm các bản ghi có tenant_id khác với target hoặc bị Null
            # Lưu ý: Một số model legacy có thể dùng String thay vì UUID trong DB nên cần cast cẩn thận
            try:
                inconsistent_qs = model.objects.exclude(tenant_id=target_uuid)
                count = inconsistent_qs.count()
            except (ProgrammingError, OperationalError):
                schema_drift_models.append(f"{model._meta.app_label}.{model.__name__}")
                self.stdout.write(self.style.WARNING(" BỎ QUA (schema drift khi truy vấn tenant_id)"))
                continue

            if count > 0:
                self.stdout.write(self.style.ERROR(f" PHÁT HIỆN {count} BẢN GHI SAI LỆCH!"))
                inconsistent_models += 1
                total_inconsistent_records += count
                
                # Hiển thị 5 ID ví dụ để kỹ thuật viên kiểm tra
                sample_ids = list(inconsistent_qs.values_list('pk', flat=True)[:5])
                self.stdout.write(self.style.WARNING(f"   - Các PK lỗi ví dụ: {sample_ids}"))
            else:
                self.stdout.write(self.style.SUCCESS(" OK"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- KẾT QUẢ KIỂM TRA ---"))
        if total_inconsistent_records == 0:
            self.stdout.write(self.style.SUCCESS(
                "Hoàn hảo! Tất cả dữ liệu đều nhất quán với cấu hình Single-organization của SCMD Pro."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"CẢNH BÁO: Tìm thấy {total_inconsistent_records} bản ghi không hợp lệ trên {inconsistent_models} models."
            ))
            self.stdout.write(self.style.WARNING(
                "Hành động: Vui lòng sử dụng script update hoặc kiểm tra lại logic TenantScopedModel.save()."
            ))
            self.stdout.write(self.style.NOTICE(
                "Lưu ý: Mọi thao tác sửa đổi trực tiếp phải được ghi lại trong Audit Log."
            ))

        if schema_drift_models:
            self.stdout.write(self.style.WARNING(
                f"Phát hiện {len(schema_drift_models)} model có schema drift giữa code và DB. "
                "Integrity check đã bỏ qua các model này để tránh chặn bootstrap."
            ))
            self.stdout.write(self.style.WARNING(
                f"Model bị ảnh hưởng: {schema_drift_models[:10]}"
            ))
            self.stdout.write(self.style.WARNING(
                "Hành động: chạy makemigrations/migrate hoặc bổ sung migration forward-fix trước khi coi môi trường là sạch."
            ))
            
