#!/bin/bash
# ==============================================================================
# SCMD Pro - Daily Backup Script (Operational Truth Enforcer)
# ------------------------------------------------------------------------------
# Mô tả: Tự động dump database và nén media volume.
# Tần suất khuyến nghị: Chạy hằng ngày qua Cron job.
# ==============================================================================

# 1. Cấu hình đường dẫn (Điều chỉnh theo môi trường thực tế)
PROJECT_DIR="/d/SCMD_Tech/1.SCMDPRO/scmd_pro" # Đường dẫn dự án
BACKUP_DIR="/d/SCMD_Backups"                  # Nơi lưu trữ bản sao lưu
RETENTION_DAYS=30                             # Số ngày giữ bản sao lưu
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_STAMP=$(date +"%Y%m%d")
CURRENT_BACKUP_PATH="$BACKUP_DIR/$DATE_STAMP"

# Tạo thư mục backup nếu chưa có
mkdir -p "$CURRENT_BACKUP_PATH"

# 2. Load biến môi trường từ .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
else
    echo "ERR: Không tìm thấy file .env tại $PROJECT_DIR"
    exit 1
fi

LOG_FILE="$BACKUP_DIR/backup_history.log"
echo "[$(date)] --- BẮT ĐẦU SAO LƯU SCMD PRO v3.5.0 ---" >> "$LOG_FILE"

# 3. Sao lưu PostgreSQL (PostGIS)
# Tên container lấy từ docker-compose.prod.yml: scmd_db_prod
DB_CONTAINER="scmd_db_prod"
DB_FILE="$CURRENT_BACKUP_PATH/scmd_db_$TIMESTAMP.sql.gz"

echo "  -> Đang dump database: $SQL_DATABASE..."
docker exec "$DB_CONTAINER" pg_dump -U "$SQL_USER" "$SQL_DATABASE" | gzip > "$DB_FILE"

if [ $? -eq 0 ]; then
    echo "  OK: Database đã được sao lưu tại $DB_FILE" >> "$LOG_FILE"
else
    echo "  ERR: Lỗi khi sao lưu Database" >> "$LOG_FILE"
    # Có thể thêm gửi mail cảnh báo tại đây
fi

# 4. Sao lưu Media Volume (Ảnh chấm công & Sự cố)
# Tên volume lấy từ docker-compose.prod.yml: media_volume
# Chúng ta dùng một container tạm thời để nén dữ liệu từ volume
MEDIA_VOLUME_NAME="scmd_media_volume" # Docker thường thêm prefix project name
MEDIA_FILE="$CURRENT_BACKUP_PATH/scmd_media_$TIMESTAMP.tar.gz"

echo "  -> Đang nén Media Assets..."
docker run --rm \
    -v "$MEDIA_VOLUME_NAME:/volume_data" \
    -v "$CURRENT_BACKUP_PATH:/backup_dest" \
    alpine tar czf "/backup_dest/scmd_media_$TIMESTAMP.tar.gz" -C /volume_data .

if [ $? -eq 0 ]; then
    echo "  OK: Media đã được sao lưu tại $MEDIA_FILE" >> "$LOG_FILE"
else
    echo "  ERR: Lỗi khi sao lưu Media Assets" >> "$LOG_FILE"
fi

# 5. Ghi nhận Audit Log (Theo BACKUP_RESTORE_DRILL.md)
# Thực hiện một lệnh insert đơn giản vào bảng AuditLog nếu cần thiết
# docker exec "$DB_CONTAINER" psql -U "$SQL_USER" -d "$SQL_DATABASE" -c \
# "INSERT INTO main_auditlog (action, object_type, timestamp, note) VALUES ('EXECUTE', 'System', NOW(), 'Daily Auto Backup Completed');"

# 6. Dọn dẹp bản sao lưu cũ (Retention Policy)
echo "  -> Đang dọn dẹp bản sao lưu cũ hơn $RETENTION_DAYS ngày..."
find "$BACKUP_DIR" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "[$(date)] --- HOÀN TẤT SAO LƯU ---" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

echo "Sao lưu hoàn tất. Kiểm tra log tại $LOG_FILE"