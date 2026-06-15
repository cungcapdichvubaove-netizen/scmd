# Production Surface Hardening Contract

This contract captures Phase 0 production-safety decisions for the runtime surface.

## Private media

`/media/` is private. Nginx must use `auth_request /_internal/media-auth/?uri=$request_uri` before serving any media file.

Mandatory headers on `/media/`:

- `Cache-Control: private, no-store`
- `X-Content-Type-Options: nosniff`

`main.views.MEDIA_AUTH_POLICY_MATRIX` must list every owned `upload_to` prefix. New upload fields must update this matrix and add tests.

## HTTPS production contract

`docker-compose.prod.yml` is an internal origin stack. Public production traffic must terminate TLS at an edge load balancer/reverse proxy or a hardened TLS gateway before this stack. The edge must forward `X-Forwarded-Proto=https`; Django keeps `SECURE_SSL_REDIRECT=True` in production.

## Backup/restore

The web backup/restore app is disabled by default and exposes no URL. Database backup/restore must use a controlled operational runbook with approval, encrypted storage and audit. Re-enabling the web UI requires a separate security design and tests in the same patch.

## Release ZIP hygiene

Release/source ZIPs must not contain:

- `__pycache__/`
- `*.pyc`
- runtime `media/`
- collected `staticfiles/`
- `.env` or runtime secrets
- local logs, browser profiles, Redis dumps or celery beat state

Use `scripts/release_contract_check.py --audit-zip` before release packaging.

Recommended cleanup command before packaging:

```bash
scripts/clean_release_artifacts.sh
python scripts/release_contract_check.py --audit-zip
```
