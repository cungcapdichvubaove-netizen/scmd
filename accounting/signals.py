# -*- coding: utf-8 -*-
import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BangLuongThang, ChiTietLuong
from .models_soquy import SoQuy
from .cache_utils import invalidate_accounting_cache

logger = logging.getLogger(__name__)

def _schedule_invalidation():
    """Đảm bảo chỉ invalidate cache sau khi DB transaction đã commit thành công."""
    transaction.on_commit(invalidate_accounting_cache)

@receiver([post_save, post_delete], sender=BangLuongThang)
@receiver([post_save, post_delete], sender=ChiTietLuong)
@receiver([post_save, post_delete], sender=SoQuy)
def handle_accounting_data_change(sender, instance, **kwargs):
    """Lắng nghe thay đổi từ các nguồn dữ liệu KPI chính."""
    try:
        _schedule_invalidation()
    except Exception:
        logger.exception("[Accounting-Cache] Failed to schedule invalidation.")