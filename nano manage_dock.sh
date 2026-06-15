#!/bin/bash

# SCMD Docker Management Script
# Chuyển đổi nhanh giữa chế độ Debug và Production

# 1. Định nghĩa các biến
COMPOSE_PROD="docker-compose.yml"
COMPOSE_DEBUG="docker-compose.debug.yml"
CONTAINER_NAME="scmd_web" # Thay đổi theo tên container của bạn

# 2. Xử lý các tham số đầu vào
case "$1" in
    debug)
        echo "--- 🛠️  ĐANG CHUYỂN SANG CHẾ ĐỘ DEBUG (HOT-RELOAD) ---"
        docker-compose -f $COMPOSE_PROD -f $COMPOSE_DEBUG up -d
        echo "✅ Đã bật chế độ Debug tại cổng 8000."
        echo "💡 Gợi ý: Dùng 'tail -f logs' để xem lỗi trực tiếp."
        ;;
        
    prod)
        echo "--- 🚀 ĐANG CHUYỂN SANG CHẾ ĐỘ PRODUCTION ---"
        docker-compose -f $COMPOSE_PROD up -d
        echo "✅ Hệ thống đã quay lại chế độ Production ổn định."
        ;;

    restart)
        echo "--- ♻️  ĐANG KHỞI ĐỘNG LẠI HỆ THỐNG ---"
        docker-compose restart
        ;;

    log)
        echo "--- 📋 ĐANG THEO DÕI LOGS (Nhấn Ctrl+C để thoát) ---"
        docker logs -f $CONTAINER_NAME
        ;;

    migrate)
        echo "--- 🗄️  ĐANG CẬP NHẬT DATABASE ---"
        docker-compose exec web python manage.py makemigrations
        docker-compose exec web python manage.py migrate
        echo "✅ Đã cập nhật cấu trúc bảng dữ liệu."
        ;;

<<<<<<< HEAD
    profile)
        echo "--- 📊 ĐANG CHẠY QUERY PROFILING TRÊN DASHBOARD ---"
        docker-compose exec web python manage.py profile_ops_dashboard
        ;;

    *)
        echo "Sử dụng: ./manage_dock.sh {debug|prod|restart|log|migrate|profile}"
=======
    *)
        echo "Sử dụng: ./manage_dock.sh {debug|prod|restart|log|migrate}"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        echo "  debug   : Bật hot-reload để sửa lỗi nhanh"
        echo "  prod    : Tắt debug, chạy Gunicorn ổn định"
        echo "  log     : Xem log thời gian thực"
        echo "  migrate : Chạy lệnh migrate nhanh vào container"
<<<<<<< HEAD
        echo "  profile : Kiểm tra hiệu năng truy vấn SQL trên Dashboard"
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        exit 1
        ;;
esac