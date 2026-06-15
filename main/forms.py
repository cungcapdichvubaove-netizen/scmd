from django.contrib.auth.forms import AuthenticationForm


class LoginAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": (
            "Tên đăng nhập hoặc mật khẩu không chính xác. "
            "Lưu ý các trường này có phân biệt chữ hoa và chữ thường."
        ),
        "inactive": "Tài khoản này hiện không hoạt động.",
    }

