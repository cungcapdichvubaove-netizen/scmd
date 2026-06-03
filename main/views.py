# file: main/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .dashboard_router import DashboardRouter


def homepage(request):
    """
    Trang chủ:
    - Nếu đã đăng nhập -> Chuyển vào Hub điều phối.
    - Nếu chưa đăng nhập -> Chuyển sang trang Login.
    """
    if request.user.is_authenticated:
        return redirect("main:central_hub")
    return redirect("main:login")


@login_required
def central_hub(request):
    """
    Trung tâm điều phối:
    - Dùng DashboardRouter làm SSOT cho điều hướng dashboard.
    - Không còn dùng `is_staff` như tín hiệu thay thế cho vai trò nghiệp vụ.
    """
    decision = DashboardRouter.resolve_decision(request.user)

    if not decision.matched:
        messages.warning(
            request,
            f"Xin chào {request.user.username}, tài khoản của bạn chưa được phân nhóm quyền."
        )

    return redirect(decision.route_name)


def login_view(request):
    """
    Xử lý đăng nhập.
    """
    if request.user.is_authenticated:
        return redirect("main:central_hub")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "main:central_hub")
                return redirect(next_url)

            messages.error(request, "Tài khoản hoặc mật khẩu không chính xác.")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin đăng nhập.")
    else:
        form = AuthenticationForm()

    return render(request, "main/login.html", {"form": form})


def logout_view(request):
    """
    Xử lý đăng xuất.
    """
    logout(request)
    return redirect("main:login")
