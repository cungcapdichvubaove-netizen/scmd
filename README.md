# Security Command (SCMD) - Hệ thống Quản lý An Ninh Toàn Diện

![Logo](static/img/logo_moi.png)

## 📖 Giới thiệu

**Security Command (SCMD)** là giải pháp ERP chuyên biệt dành cho các công ty Dịch vụ Bảo vệ chuyên nghiệp. Hệ thống được thiết kế để giải quyết các bài toán đặc thù của ngành an ninh như: xếp lịch trực ca đêm, tuần tra QR Code/GPS, quản lý tài sản công cụ hỗ trợ và tính lương nhân viên.

Dự án được xây dựng trên nền tảng **Django (Python)** với kiến trúc Modular, đảm bảo tính bảo mật, hiệu năng cao và khả năng mở rộng.

## 🚀 Tính năng nổi bật

* **Quản lý Nhân sự (HRM):**
    * Hồ sơ nhân viên 360 độ (CCCD, quê quán, lịch sử công tác).
    * Tự động sinh tài khoản đăng nhập (User) khi tạo hồ sơ.
    * Cơ chế sinh mã nhân viên an toàn (Concurrency Safe).
* **Vận hành & Xếp lịch (Operations):**
    * Xử lý logic ca đêm (Night Shift) vắt qua ngày.
    * Chấm công GPS + Hình ảnh thực tế.
    * Báo cáo sự cố tức thời (Incident Reporting) từ Mobile.
* **Thanh tra & Giám sát (Inspection):**
    * Tuần tra bảo vệ bằng QR Code định danh.
    * Giám sát vị trí và tiến độ tuần tra theo thời gian thực.
* **Kho & Tài sản (Inventory):**
    * Quản lý cấp phát đồng phục (tiêu hao) và công cụ hỗ trợ (luân chuyển).
    * Cảnh báo tồn kho tối thiểu.
* **Kinh doanh (CRM):** Quản lý Sales Pipeline từ Leads -> Hợp đồng -> Triển khai Mục tiêu.

## 🛠 Công nghệ sử dụng

* **Backend:** Python 3.9+, Django 4.x
* **Database:** PostgreSQL (Production) / SQLite (Dev)
* **Asynchronous Task:** Redis + Celery (Xử lý tác vụ nền)
* **Real-time:** Django Channels (WebSocket)
* **Frontend:** Tailwind CSS, Jazzmin Admin Theme
* **Infrastructure:** Docker (Optional), WhiteNoise (Static files)

## ⚙️ Cài đặt & Triển khai

### Yêu cầu tiên quyết
* Python >= 3.8
* Node.js & npm (để build Tailwind CSS)
* Redis Server

### Các bước cài đặt

1.  **Clone dự án:**
    ```bash
    git clone [https://github.com/username/lucnao22-art-scmd.git](https://github.com/username/lucnao22-art-scmd.git)
    cd lucnao22-art-scmd
    ```

2.  **Thiết lập môi trường ảo:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình biến môi trường:**
    Tạo file `.env` tại thư mục gốc và cập nhật:
    ```env
    SECRET_KEY=your-secret-key-here
    DEBUG=True
    DATABASE_URL=postgres://user:password@localhost:5432/scmd_db
    REDIS_URL=redis://localhost:6379/0
    ```

5.  **Cài đặt Frontend (Tailwind):**
    ```bash
    cd theme/static_src
    npm install
    npm run build
    cd ../..
    ```

6.  **Khởi tạo Database:**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

7.  **Chạy Server:**
    ```bash
    # Terminal 1: Django Server
    python manage.py runserver

    # Terminal 2: Celery Worker
    celery -A config worker -l info
    ```

## 🤝 Đóng góp

Vui lòng đọc file `CONTRIBUTING.md` để biết quy trình gửi Pull Request. Dự án tuân thủ chuẩn code **PEP 8**. Kiểm tra lỗi cú pháp bằng:
```bash
flake8 .