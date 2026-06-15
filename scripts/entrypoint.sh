#!/bin/bash
# file: scripts/entrypoint.sh

set -euo pipefail

echo "Checking Database connection at $DB_HOST:$DB_PORT..."

# Sử dụng Python để kiểm tra kết nối thay vì nc
python << END
import socket
import time
import os

db_host = os.getenv('DB_HOST', 'db')
db_port = int(os.getenv('DB_PORT', 5432))
timeout = 30
start_time = time.time()

while True:
    try:
        with socket.create_connection((db_host, db_port), timeout=1):
            print("Database started!")
            break
    except (socket.error, socket.timeout):
        if time.time() - start_time > timeout:
            print(f"Error: Database connection timed out after {timeout} seconds.")
            exit(1)
        print(f"PostgreSQL at {db_host}:{db_port} is unavailable - sleeping")
        time.sleep(1)
END
if [ $? -ne 0 ]; then exit 1; fi

if [ "$#" -eq 0 ]; then
    echo "Error: no startup command was provided to scripts/entrypoint.sh"
    exit 1
fi

echo "Starting process: $*"
exec "$@"
