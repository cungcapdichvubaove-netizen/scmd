#!/bin/bash
set -euo pipefail

PROJECT_ROOT="${SCMDERP_ROOT:-/d/SCMDERP}"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
APP_URL="${SCMDERP_APP_URL:-http://localhost:8000}"
LOG_FILE="$(cd "$(dirname "$0")" && pwd)/deploy-scmderp.log"
MODE="${1:-full}"
INFRA_SERVICES=(db redis)
APP_SERVICES=(web celery_worker celery_beat)
APP_IMAGES=(scmderp-web:latest scmderp-celery_worker:latest scmderp-celery_beat:latest)
ADMIN_USERNAME="${SCMD_ADMIN_USERNAME:-${DJANGO_SUPERUSER_USERNAME:-admin}}"
ADMIN_PASSWORD="${SCMD_ADMIN_PASSWORD:-${DJANGO_SUPERUSER_PASSWORD:-ScmdAdmin2026!}}"
HEALTH_URLS=("$APP_URL/login/" "$APP_URL/admin/login/" "$APP_URL/api/docs/")
TAILWIND_BUILD_ARTIFACT="$PROJECT_ROOT/theme/static/css/dist/styles.css"

log() {
  printf '%s\n' "$1" | tee -a "$LOG_FILE"
}

run_compose() {
  log "INFO docker compose --project-directory $PROJECT_ROOT -f $COMPOSE_FILE $*"
  docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" "$@" 2>&1 | tee -a "$LOG_FILE"
}

has_local_image() {
  docker image inspect "$1" >/dev/null 2>&1
}

is_offline_registry_failure() {
  local message="${1:-}"
  [[ "$message" == *"lookup registry-1.docker.io"* ]] || \
  [[ "$message" == *"no such host"* ]] || \
  [[ "$message" == *"failed to resolve source metadata"* ]]
}

assert_local_fallback_images() {
  local missing=()
  local image
  for image in "${APP_IMAGES[@]}"; do
    if ! has_local_image "$image"; then
      missing+=("$image")
    fi
  done

  if [ "${#missing[@]}" -gt 0 ]; then
    log "ERR Khong the fallback vi thieu image local: ${missing[*]}"
    exit 1
  fi
}

assert_project() {
  command -v docker >/dev/null 2>&1 || { log "ERR Khong tim thay docker trong PATH."; exit 1; }
  docker info >/dev/null 2>&1 || { log "ERR Docker Desktop chua san sang."; exit 1; }
  [ -d "$PROJECT_ROOT" ] || { log "ERR Khong tim thay $PROJECT_ROOT"; exit 1; }
  [ -f "$COMPOSE_FILE" ] || { log "ERR Khong tim thay $COMPOSE_FILE"; exit 1; }
  [ -f "$PROJECT_ROOT/manage.py" ] || { log "ERR Khong tim thay manage.py"; exit 1; }
  [ -f "$TAILWIND_BUILD_ARTIFACT" ] || { log "ERR Khong tim thay Tailwind build artifact: $TAILWIND_BUILD_ARTIFACT. Can build frontend asset truoc khi deploy."; exit 1; }
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
USED_LOCAL_IMAGE_FALLBACK=0
log "========================================================="
log "  SCMDERP - DEPLOY"
log "========================================================="
log "INFO Project root: $PROJECT_ROOT"
log "INFO Compose file: $COMPOSE_FILE"
log "INFO App URL     : $APP_URL"
log "INFO Mode        : $MODE"

assert_project

run_compose config

if [ "$MODE" != "fast" ]; then
  set +e
  BUILD_OUTPUT="$(docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" build "${APP_SERVICES[@]}" 2>&1)"
  BUILD_EXIT=$?
  set -e
  printf '%s\n' "$BUILD_OUTPUT" | tee -a "$LOG_FILE"

  if [ "$BUILD_EXIT" -ne 0 ]; then
    if is_offline_registry_failure "$BUILD_OUTPUT"; then
      log "WARN Build image that bai do khong truy cap duoc Docker Hub."
      assert_local_fallback_images
      log "WARN Tim thay day du image local. Chuyen sang fast restart de tiep tuc deploy."
      MODE="fast"
      USED_LOCAL_IMAGE_FALLBACK=1
    else
      exit "$BUILD_EXIT"
    fi
  fi
else
  log "WARN Fast mode bo qua build image, chi restart stack va van chay migrate/check."
fi

if [ "$USED_LOCAL_IMAGE_FALLBACK" -eq 1 ]; then
  log "WARN Script se dung image local da ton tai, sau do van migrate/check day du."
fi

run_compose up -d "${INFRA_SERVICES[@]}"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web manage.py migrate --noinput 2>&1 | tee -a "$LOG_FILE"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web create_superuser_auto.py 2>&1 | tee -a "$LOG_FILE"
docker compose --project-directory "$PROJECT_ROOT" -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint python web manage.py check 2>&1 | tee -a "$LOG_FILE"

run_compose up -d --force-recreate "${APP_SERVICES[@]}"

wait_app_health 300

log "OK SCMDERP san sang tai $APP_URL"
log "OK Tai khoan admin: $ADMIN_USERNAME"
log "OK Mat khau admin : $ADMIN_PASSWORD"
