from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def vn_weekday(value):
    if not value:
        return ""
    weekday_names = [
        "Thứ hai",
        "Thứ ba",
        "Thứ tư",
        "Thứ năm",
        "Thứ sáu",
        "Thứ bảy",
        "Chủ nhật",
    ]
    try:
        return weekday_names[value.weekday()]
    except Exception:
        return ""
