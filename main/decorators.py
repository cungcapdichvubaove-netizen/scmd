# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Infrastructure Utility: Audit Log Decorator.
Description: Tự động hóa việc ghi nhật ký hậu kiểm cho Application Layer.
"""

import functools
import logging
from django.conf import settings
from main.models import AuditLog

logger = logging.getLogger(__name__)

def application_audit_log(module: str, model_name: str, action: str = AuditLog.Action.EXECUTE):
    """
    Decorator dành cho các phương thức execute() của Use Cases.
    Yêu cầu: Phương thức được decorate nên nhận 'user' và 'tenant_id' trong kwargs.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Thu thập ngữ cảnh từ arguments (Rule 12.3)
            user = kwargs.get('user')
            tenant_id = kwargs.get('tenant_id', getattr(settings, 'SCMD_ORGANIZATION_ID', None))
            ip_address = kwargs.get('ip_address')
            user_agent = kwargs.get('user_agent')
            
            try:
                # 2. Thực thi nghiệp vụ chính
                result = func(*args, **kwargs)
                
                # 3. Trích xuất object_id từ kết quả trả về
                object_id = None
                # Giả định kết quả trả về là Object, hoặc tuple (Object, success, ...)
                if hasattr(result, 'pk'):
                    object_id = str(result.pk)
                elif isinstance(result, (list, tuple)) and len(result) > 0:
                    if hasattr(result[0], 'pk'):
                        object_id = str(result[0].pk)
                    elif hasattr(result[0], 'id'):
                        object_id = str(result[0].id)

                # 4. Ghi log thành công
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    module=module,
                    model_name=model_name,
                    object_id=object_id,
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='SUCCESS'
                )
                return result

            except Exception as e:
                # 5. Ghi log thất bại nếu nghiệp vụ phát sinh lỗi
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    module=module,
                    model_name=model_name,
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='FAILED',
                    note=f"Exception: {str(e)}"
                )
                logger.error(f"[Audit] Logic failure in {func.__name__}: {str(e)}")
                raise e
                
        return wrapper
    return decorator