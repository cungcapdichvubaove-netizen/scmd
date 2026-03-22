# Dockerfile
# Base image: Python 3.11 Slim Bookworm (Stable & Light)
FROM python:3.11-slim-bookworm

# 1. Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Quan trọng: Chế độ Production
ENV DJANGO_SETTINGS_MODULE config.settings

# 2. Cài đặt thư viện hệ thống
# - GeoDjango: binutils, libproj-dev, gdal-bin
# - Database: libpq-dev, gcc
# - WeasyPrint: libpango...
# - Utils: gettext (i18n), netcat-openbsd (để check DB port)
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    gettext \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 3. Tạo thư mục làm việc
WORKDIR /app

# 4. Copy và cài đặt requirements
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ mã nguồn
COPY . /app/

# 6. Tạo thư mục cho Static/Media
# Nginx sẽ mount vào đây để phục vụ file
RUN mkdir -p /app/staticfiles
RUN mkdir -p /app/media

# 7. Copy và cấp quyền cho Entrypoint Script
COPY ./scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

# 8. Mở cổng 8000 (Daphne sẽ chạy ở đây)
EXPOSE 8000

# 9. Chạy Entrypoint
ENTRYPOINT ["/bin/bash", "/app/scripts/entrypoint.sh"]