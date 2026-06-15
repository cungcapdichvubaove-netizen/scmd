# file: notifications/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from clients.models import HopDong
from .models import ThongBao


@shared_task
def check_expiring_contracts():
    thirty_days_later = timezone.now().date() + timedelta(days=30)
    expiring_contracts = HopDong.objects.filter(ngay_het_han__lte=thirty_days_later)

    for contract in expiring_contracts:
        # Giả sử cần thông báo cho superuser, sau này sẽ thay bằng người phụ trách
        from django.contrib.auth.models import User

        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            ThongBao.objects.get_or_create(
                nguoi_nhan=admin,
                tieu_de=f"Hợp đồng sắp hết hạn: {contract.so_hop_dong}",
                noi_dung=f"Hợp đồng với khách hàng {contract.khach_hang} sẽ hết hạn vào ngày {contract.ngay_het_han.strftime('%d/%m/%Y')}.",
                link_hanh_dong=f"/admin/clients/hopdong/{contract.id}/change/",
            )
    return f"Đã kiểm tra {expiring_contracts.count()} hợp đồng sắp hết hạn."
