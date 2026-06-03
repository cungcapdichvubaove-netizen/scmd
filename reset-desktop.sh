#!/bin/bash
set -euo pipefail

PROJECT_ROOT="${SCMDERP_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
APP_URL="${SCMDERP_APP_URL:-http://localhost:8000}"
LOG_FILE="$(cd "$(dirname "$0")" && pwd)/reset-scmderp.log"
INFRA_SERVICES=(db redis)
APP_SERVICES=(web celery_worker celery_beat)
ADMIN_USERNAME="${SCMD_ADMIN_USERNAME:-${DJANGO_SUPERUSER_USERNAME:-admin}}"
ADMIN_PASSWORD="${SCMD_ADMIN_PASSWORD:-${DJANGO_SUPERUSER_PASSWORD:-ScmdAdmin2026!}}"
HEALTH_URLS=("$APP_URL/" "$APP_URL/admin/login/" "$APP_URL/api/docs/")

log() {
  printf '%s\n' "$1" | tee -a "$LOG_FILE"
}

run_compose() {
  log "INFO docker compose --project-directory $PROJECT_ROOT -f $COMPOSE_FILE $*"
  docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" "$@" 2>&1 | tee -a "$LOG_FILE"
}

assert_project() {
  command -v docker >/dev/null 2>&1 || { log "ERR Khong tim thay docker trong PATH."; exit 1; }
  docker info >/dev/null 2>&1 || { log "ERR Docker Desktop chua san sang."; exit 1; }
  [ -d "$PROJECT_ROOT" ] || { log "ERR Khong tim thay $PROJECT_ROOT"; exit 1; }
  [ -f "$COMPOSE_FILE" ] || { log "ERR Khong tim thay $COMPOSE_FILE"; exit 1; }
  [ -f "$PROJECT_ROOT/manage.py" ] || { log "ERR Khong tim thay manage.py"; exit 1; }
}

wait_app_health() {
  local timeout="${1:-300}"
  local elapsed=0

  while [ "$elapsed" -lt "$timeout" ]; do
    for url in "${HEALTH_URLS[@]}"; do
      if curl -fsSI --max-time 5 "$url" >/dev/null 2>&1; then
        log "OK HTTP endpoint san sang: $url"
        return 0
      fi
    done

    sleep 5
    elapsed=$((elapsed + 5))
    log "INFO Dang cho SCMDERP san sang $elapsed/$timeout giay"
  done

  log "ERR Health check timeout sau $timeout giay."
  return 1
}

: > "$LOG_FILE"
log "========================================================="
log "  SCMDERP - FACTORY RESET"
log "========================================================="
log "INFO Project root: $PROJECT_ROOT"
log "INFO Compose file: $COMPOSE_FILE"
log "INFO App URL     : $APP_URL"

assert_project

printf 'Nhan Enter de tiep tuc reset, hoac Ctrl+C de huy... '
read -r _
printf 'Backup database truoc khi reset? (y/n): '
read -r backup_choice

if [[ "$backup_choice" =~ ^[Yy]$ ]]; then
  timestamp="$(date +%Y%m%d_%H%M%S)"
  backup_file="$(cd "$(dirname "$0")" && pwd)/scmderp-backup-$timestamp.sql"
  run_compose up -d db
  docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" exec -T db pg_dump -U scmd_user scmd_db >"$backup_file"
  log "OK Backup thanh cong: $backup_file"
fi

run_compose config
run_compose down -v --remove-orphans
run_compose build "${APP_SERVICES[@]}"
run_compose up -d "${INFRA_SERVICES[@]}"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web manage.py migrate --noinput 2>&1 | tee -a "$LOG_FILE"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web create_superuser_auto.py 2>&1 | tee -a "$LOG_FILE"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web manage.py check 2>&1 | tee -a "$LOG_FILE"

run_compose up -d --force-recreate "${APP_SERVICES[@]}"

printf 'Nap du lieu mau bang seed_data sau reset? (y/n): '
read -r seed_choice
if [[ "$seed_choice" =~ ^[Yy]$ ]]; then
  docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web manage.py seed_data 2>&1 | tee -a "$LOG_FILE"
fi

wait_app_health 300

log "OK SCMDERP san sang tai $APP_URL"
log "OK Tai khoan admin: $ADMIN_USERNAME"
log "OK Mat khau admin : $ADMIN_PASSWORD"
