FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    binutils \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libharfbuzz-subset0 \
    libharfbuzz0b \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Desktop/runtime images consume the committed Tailwind output instead of
# rebuilding CSS inside Docker. This avoids depending on a Node base-image pull
# during local deploy when Docker Hub or DNS is unstable.
RUN test -f /app/theme/static/css/dist/styles.css

# Keep these explicit until the dependency layer history is fully normalized.
RUN pip install --no-cache-dir phonenumbers qrcode==8.2 reportlab==4.4.2

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
