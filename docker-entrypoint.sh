#!/bin/bash
set -e

if [ "${SCMD_COLLECTSTATIC_ON_START:-0}" = "1" ]; then
  echo ">>> Dang thu gom Static Files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
