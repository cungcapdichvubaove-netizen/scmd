#!/usr/bin/env sh
set -eu

# Remove runtime/generated files that must never be shipped in SCMD Pro source ZIPs.
# Safe for source trees; do not run against a live mounted production MEDIA_ROOT.
find . -type d -name __pycache__ -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
rm -rf ./staticfiles ./media ./.pytest_cache ./htmlcov ./tmp-edge-profile ./tmpedge2
rm -f ./.coverage ./dump.rdb ./deploy-scmdpro.log ./celerybeat-schedule ./celerybeat-schedule-shm ./celerybeat-schedule-wal
