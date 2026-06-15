# ==============================================================================
# SCMD Pro - Daily Backup Script for Windows (PowerShell)
# ------------------------------------------------------------------------------
# Mô tả: Tự động dump database và nén media volume từ Docker Desktop.
# Tần suất: Chạy hằng ngày qua Windows Task Scheduler.
# ==============================================================================

# 1. Cấu hình đường dẫn
$ProjectDir = "D:\SCMD_Tech\1.SCMDPRO\scmd_pro"
$BackupDir = "D:\SCMD_Backups"
$RetentionDays = 30
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DateStamp = Get-Date -Format "yyyyMMdd"
$CurrentBackupPath = Join-Path $BackupDir $DateStamp
$LogFile = Join-Path $BackupDir "backup_history.log"

# Tạo thư mục backup nếu chưa có
if (!(Test-Path $CurrentBackupPath)) {
    New-Item -ItemType Directory -Path $CurrentBackupPath -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $LogEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $LogFile -Value $LogEntry
    Write-Host $LogEntry
}

Write-Log "--- BẮT ĐẦU SAO LƯU SCMD PRO v3.5.0 ---"

# 2. Load biến môi trường từ .env
$DotEnvPath = Join-Path $ProjectDir ".env"
if (Test-Path $DotEnvPath) {
    Get-Content $DotEnvPath | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
        $name, $value = $_.Split('=', 2).Trim()
        # Loại bỏ dấu nháy nếu có
        $value = $value -replace "^['""]|['""]$" , ""
        Set-Content -Path "env:$name" -Value $value
    }
} else {
    Write-Log "ERR: Không tìm thấy file .env tại $ProjectDir"
    exit 1
}

# 3. Sao lưu PostgreSQL (PostGIS)
$DbContainer = "scmd_db_prod"
$DbFileName = "scmd_db_$Timestamp.sql"
$DbFilePath = Join-Path $CurrentBackupPath $DbFileName
$ZipDbPath = "$DbFilePath.zip"

Write-Log "  -> Đang dump database: $($env:SQL_DATABASE)..."

# Sử dụng --no-container-name-labels để tránh nhiễu log trong một số phiên bản docker
& docker exec $DbContainer pg_dump -U $env:SQL_USER $env:SQL_DATABASE > $DbFilePath

if ($LASTEXITCODE -eq 0) {
    # Nén file SQL bằng công cụ native của PowerShell
    Compress-Archive -Path $DbFilePath -DestinationPath $ZipDbPath -Force
    Remove-Item $DbFilePath
    Write-Log "  OK: Database đã được sao lưu tại $ZipDbPath"
} else {
    Write-Log "  ERR: Lỗi khi sao lưu Database (ExitCode: $LASTEXITCODE)"
}

# 4. Sao lưu Media Volume (Ảnh chấm công & Sự cố)
# Tên volume: Thường là [project_folder]_media_volume. Hãy kiểm tra bằng 'docker volume ls'
$MediaVolumeName = "scmd_media_volume" 
$MediaFileName = "scmd_media_$Timestamp.tar"
$MediaFilePath = Join-Path $CurrentBackupPath $MediaFileName
$ZipMediaPath = "$MediaFilePath.zip"

Write-Log "  -> Đang nén Media Assets từ volume: $MediaVolumeName..."

# Chạy container Alpine tạm thời để đóng gói dữ liệu volume thành tar
& docker run --rm `
    -v "${MediaVolumeName}:/volume_data" `
    -v "${CurrentBackupPath}:/backup_dest" `
    alpine tar cf "/backup_dest/$MediaFileName" -C /volume_data .

if ($LASTEXITCODE -eq 0) {
    # Nén file TAR thành ZIP để tiết kiệm không gian trên Windows
    Compress-Archive -Path $MediaFilePath -DestinationPath $ZipMediaPath -Force
    Remove-Item $MediaFilePath
    Write-Log "  OK: Media đã được sao lưu tại $ZipMediaPath"
} else {
    Write-Log "  ERR: Lỗi khi sao lưu Media Assets (ExitCode: $LASTEXITCODE)"
}

# 5. Dọn dẹp bản sao lưu cũ (Retention Policy)
Write-Log "  -> Đang dọn dẹp bản sao lưu cũ hơn $RetentionDays ngày..."
$LimitDate = (Get-Date).AddDays(-$RetentionDays)

Get-ChildItem -Path $BackupDir -Directory | Where-Object { 
    try {
        # Parse tên thư mục dạng yyyyMMdd
        [datetime]::ParseExact($_.Name, "yyyyMMdd", $null) -lt $LimitDate
    } catch { $false }
} | ForEach-Object {
    Write-Log "     - Xóa thư mục cũ: $($_.FullName)"
    Remove-Item -Path $_.FullName -Recurse -Force
}

Write-Log "--- HOÀN TẤT SAO LƯU ---"
Write-Log "-------------------------------------------"

# Gợi ý lệnh cài đặt vào Task Scheduler qua PowerShell:
# $action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument "-ExecutionPolicy Bypass -File $PSCommandPath"
# $trigger = New-ScheduledTaskTrigger -Daily -At 1am
# Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "SCMD_Pro_Daily_Backup" -Description "Backup DB and Media for SCMD Pro" -User "SYSTEM" -RunLevel Highest