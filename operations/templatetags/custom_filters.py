from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
<<<<<<< HEAD
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
=======
    return dictionary.get(key)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
