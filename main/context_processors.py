# main/context_processors.py
from .models import CompanyProfile

def company_info(request):
    """
    Tự động đưa thông tin công ty vào tất cả các template của hệ thống SCMD.
    """
    try:
        # Lấy bản ghi đầu tiên (thường profile công ty chỉ có 1)
        profile = CompanyProfile.objects.first()
        return {
            'COMPANY': profile
        }
    except Exception:
        return {
            'COMPANY': None
        }