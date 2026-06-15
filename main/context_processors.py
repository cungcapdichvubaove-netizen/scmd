# main/context_processors.py
from main.company_info import build_company_report_context, get_company_info


def company_info(request):
    """
    Tu dong dua thong tin cong ty vao tat ca template cua SCMD Pro.

    - COMPANY: object co thuoc tinh ten_cong_ty, dia_chi, hotline...
    - COMPANY_INFO: dict normalized cho cac template/report cu da dung name/address/hotline.
    """
    company = get_company_info()
    return {
        "COMPANY": company,
        "COMPANY_INFO": build_company_report_context(company),
    }


def notification_context(request):
    """Expose unread notification count for shell badge without hardcoding red dot."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {"notification_count": 0}
    try:
        from notifications.models import ThongBao

        count = len(list(ThongBao.objects.filter(nguoi_nhan=user, da_doc=False).values_list("id", flat=True)[:100]))
    except Exception:
        count = 0
    return {"notification_count": count}
