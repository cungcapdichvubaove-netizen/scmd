# file: main/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

def homepage(request):
    """
    Trang chủ:
    - Nếu đã đăng nhập -> Chuyển vào Hub điều phối (để phân quyền).
    - Nếu chưa đăng nhập -> Chuyển sang trang Login.
    """
    if request.user.is_authenticated:
        return redirect('main:central_hub')
    return redirect('main:login')

@login_required
def central_hub(request):
    """
    TRUNG TÂM ĐIỀU PHỐI (ROUTER)
    Quyết định người dùng sẽ đi đâu dựa trên Nhóm Quyền (Group) hoặc Superuser.
    Giữ nguyên logic phân quyền quan trọng của bạn.
    """
    user = request.user
    groups = list(user.groups.values_list('name', flat=True))
    
    # --- DEBUG LOG (Giúp bạn kiểm tra quyền trong Terminal) ---
    print(f"\n[DEBUG HUB] User: {user.username}")
    print(f"[DEBUG HUB] Superuser: {user.is_superuser} | Staff: {user.is_staff}")
    print(f"[DEBUG HUB] Groups: {groups}")
    # -------------------------------------------------------------

    # 1. ƯU TIÊN CAO NHẤT: Superuser hoặc Staff (Admin) -> Luôn vào Dashboard CEO
    if user.is_superuser or user.is_staff:
        print("[DEBUG HUB] => Redirecting to Dashboard Main (Admin)")
        return redirect('dashboard:main')

    # 2. Phân quyền theo Nhóm (Thứ tự ưu tiên)
    if 'BanGiamDoc' in groups:
        return redirect('dashboard:main')
    
    elif 'NghiepVu' in groups:
        return redirect('operations:dashboard_vanhanh') 
    
    elif 'KeToan' in groups:
        return redirect('accounting:dashboard')
    
    elif 'Kho' in groups:
        return redirect('inventory:dashboard')
    
    elif 'ThanhTra' in groups:
        return redirect('inspection:dashboard')
    
    elif 'BaoVe' in groups:
        # Bảo vệ đi thẳng vào giao diện Mobile
        return redirect('operations:mobile_dashboard')

    # 3. Mặc định (Nếu tài khoản thường và không thuộc nhóm nào)
    print("[DEBUG HUB] => No group matched. Fallback to Mobile Dashboard.")
    messages.warning(request, f"Xin chào {user.username}, tài khoản của bạn chưa được phân nhóm quyền.")
    return redirect('operations:mobile_dashboard')

def login_view(request):
    """
    Xử lý đăng nhập (Bổ sung để sửa lỗi AttributeError)
    """
    # Nếu đã đăng nhập thì đá về Hub ngay
    if request.user.is_authenticated:
        return redirect('main:central_hub')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Sau khi login thành công -> Chuyển về Hub để phân luồng
                next_url = request.GET.get('next', 'main:central_hub')
                return redirect(next_url)
            else:
                messages.error(request, "Tài khoản hoặc mật khẩu không chính xác.")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin đăng nhập.")
    else:
        form = AuthenticationForm()

    return render(request, 'main/login.html', {'form': form})

def logout_view(request):
    """
    Xử lý đăng xuất
    """
    logout(request)
    return redirect('main:login')