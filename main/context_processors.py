# main/context_processors.py
from django.apps import apps


def company_info(request):
    """
    Tu dong dua thong tin cong ty vao tat ca cac template cua he thong SCMD.
    """
    try:
        CompanyProfile = apps.get_model('main', 'CompanyProfile')
        profile = CompanyProfile.objects.first() if CompanyProfile else None
        return {
            'COMPANY': profile
        }
    except Exception:
        return {
            'COMPANY': None
        }
