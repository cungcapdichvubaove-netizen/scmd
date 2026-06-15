#!/bin/bash
set -e

<<<<<<< HEAD
if [ "${SCMD_COLLECTSTATIC_ON_START:-0}" = "1" ]; then
=======
if [ "${SCMD_COLLECTSTATIC_ON_START:-1}" = "1" ]; then
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
  echo ">>> Dang thu gom Static Files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
