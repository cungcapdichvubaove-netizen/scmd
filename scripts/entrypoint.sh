#!/bin/bash
# file: scripts/entrypoint.sh

echo "Checking Database connection at $DB_HOST:$DB_PORT..."

# Sử dụng Python để kiểm tra kết nối thay vì nc
python << END
import socket
import time
import os

db_host = os.getenv('DB_HOST', 'db')
db_port = int(os.getenv('DB_PORT', 5432))

while True:
    try:
        with socket.create_connection((db_host, db_port), timeout=1):
            print("Database started!")
            break
    except (socket.error, socket.timeout):
        print(f"PostgreSQL at {db_host}:{db_port} is unavailable - sleeping")
        time.sleep(1)
END

echo "Running Migrations..."
python manage.py migrate --noinput

echo "Collecting Static Files..."
python manage.py collectstatic --noinput

echo "Starting Daphne Server..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application