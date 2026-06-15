# SCMD Pro — PWA Readiness Report

## Executive summary

Base audited: `9.zip`.

SCMD Pro is currently a Django server-rendered monolith with Tailwind/PostCSS static asset builds, HTMX/Alpine-style progressive enhancement, and a mobile-first Django template surface under `operations/mobile/`. It is **not** a React, Vite, Next.js, or React Router SPA.

Current PWA readiness before this patch: **46/100 — NOT READY**.

After this Phase 1–2 v3 foundation patch: expected readiness **76/100 — PARTIALLY READY**, pending real Lighthouse/browser verification.

The system already had a manifest and root service worker, but the service worker was too narrow, the manifest icon set was incomplete, iOS standalone metadata was incomplete, and there was no offline fallback page. This patch adds a safer production-grade PWA foundation without changing Django architecture or auth flows.

## Current-state audit

### Frontend framework

- Framework: Django templates, Tailwind/PostCSS, HTMX, Dexie vendor library, NProgress, Font Awesome.
- Not detected: React, Vite app, Next.js, React Router.
- Rendering mode: server-rendered HTML, not SSR React and not SPA.
- Routing: Django URL routing; mobile pages live mainly under `/operations/mobile/` and API endpoints under `/operations/api/`.
- Bundling: PostCSS/Tailwind build into `static/css/dist/styles.css`; no JS bundle splitting currently detected.
- Dynamic imports: not used as a first-class app architecture.

### Authentication and offline impact

- Django session/cookie auth is used for server-rendered pages.
- DRF SimpleJWT is configured for API authentication, but the mobile templates mainly operate through session/CSRF and server-rendered flows.
- PWA must not cache auth endpoints, token responses, CSRF/session endpoints, or profile-sensitive admin pages.
- Offline while authenticated is limited: the app can open its shell/offline page; safe offline write sync is not production-ready until IndexedDB queue + server idempotency are implemented.

### API layer classification

Critical online-first:

- `/operations/api/v1/mobile/checkin/`
- `/operations/api/v1/mobile/checkout/`
- `/operations/api/v1/mobile/alive-check/respond/`
- `/inspection/mobile/ghi-nhan/`
- camera/media upload endpoints and SOS flows

Critical read-mostly cache candidates:

- `/operations/api/dashboard/data/`
- `/operations/api/dashboard/alive-check-violations/`
- `/operations/api/mobile/ca-truc/`
- `/operations/api/mobile/su-co/`

Network-only sensitive areas:

- `/admin/`
- `/login/`, `/logout/`, `/admin/logout/`
- `/api/schema/`, `/api/docs/`, `/api/redoc/`
- any auth/token/session/password path

## Install prompt UX

Before v3:

- The app could be installable if the browser detected the manifest and service worker, but there was no user-visible install prompt or iOS guidance in the UI.
- Users would rely on the browser address-bar install icon or manual Add to Home Screen discovery.

After v3:

- `static/pwa/pwa-register.js` captures `beforeinstallprompt` and shows a non-blocking SCMD Pro install banner on eligible Desktop/Android Chromium browsers.
- The banner is suppressed on auth/admin/password pages and when already running standalone.
- iOS Safari receives a separate Add to Home Screen hint because iOS does not support the `beforeinstallprompt` event.
- Dismissal is session-scoped and does not store tokens or sensitive data.

## Gap analysis

### Manifest

Before patch:

- Present: `static/manifest.json`.
- Present: `name`, `short_name`, `start_url`, `display`, `theme_color`, `background_color`, `orientation`.
- Missing/weak: icon sizes 72/96/128/144/152/384, `id`, `scope`, `description`, `display_override`, `lang`, richer install metadata.

After patch:

- Added full icon set: 72, 96, 128, 144, 152, 192, 384, 512, and maskable 512.
- Added `id`, `scope`, `description`, `display_override`, `categories`, `lang`.

### Service Worker

Before patch:

- Present: `templates/sw.js`, root route `/sw.js`.
- Weakness: only cached a few static assets, included a broken-looking `default_avatar` path, no offline page, no API strategy, no explicit network-only guard for auth/mutations.

After v3 patch:

- Adds versioned caches.
- Cache First for static assets.
- Stale While Revalidate for selected read-only JSON APIs.
- Network First + offline fallback for mobile navigation.
- Network Only for auth, admin, mutations, check-in/out, SOS/patrol writes.
- Login/logout/password auth-boundary cache purge via service worker message and Cache Storage API.
- `/sw.js` is served with no-store, `Service-Worker-Allowed: /`, and `nosniff` headers.
- Precache is resilient: one missing optional static asset does not break service-worker installation.

### Offline experience

Implemented now:

- App can install more reliably.
- Static shell assets cached.
- Offline fallback page available.
- Selected read-only JSON endpoints can serve stale data.
- Mobile navigation may fall back to cached page/offline page.

Not implemented yet:

- Full offline write mode.
- IndexedDB sync queue.
- Background Sync retry processor.
- Conflict/idempotency handling for incident/patrol writes.
- Server-side sync endpoint contracts.

## Proposed PWA architecture

```text
Browser
│
├── Service Worker
│   ├── Static cache: CSS, fonts, icons, app shell
│   ├── API cache: selected read-only JSON only
│   └── Navigation fallback: offline page
│
├── Cache Storage
│   ├── scmd-pro-<version>-static
│   ├── scmd-pro-<version>-api
│   └── scmd-pro-<version>-page
│
├── IndexedDB
│   └── Future: offline incident/patrol write queue
│
└── API Layer
    ├── Online: normal Django/DRF endpoints
    └── Future offline queue: idempotent sync endpoint
```

## Cache strategy

| Resource class | Strategy | Notes |
|---|---:|---|
| Static CSS/JS/fonts/icons/images | Cache First | Versioned and purged on SW activate. |
| Dashboard read API | Stale While Revalidate | Users see last known snapshot. |
| Shift/incident read APIs | Stale While Revalidate | Only selected GET JSON endpoints. |
| Mobile HTML navigation | Network First | Falls back to cached page/offline page. |
| Check-in/check-out/SOS/patrol writes | Network Only | No mutation replay until sync queue is designed. |
| Camera/media stream/upload | Network Only | Do not cache. |
| Auth/session/token/admin | Network Only | Explicitly excluded. |

## Security review

This patch intentionally avoids storing JWT, refresh token, session token, or localStorage credentials. Cache Storage is still user-sensitive if it stores role-scoped JSON, so this patch adds cache purge on logout and limits API caching to selected GET endpoints. For absolute protection across shared devices, Phase 3 should add per-user cache partitioning or full cache clear on every auth boundary.

Remaining security work:

- Add server headers to mark sensitive pages `Cache-Control: no-store`.
- Add CSP review for service worker and static asset origins.
- Add DB/server idempotency keys before offline write replay.
- Decide whether incident history offline is acceptable by role and device ownership policy.

## iOS compatibility

Added:

- `apple-mobile-web-app-capable=yes`
- `apple-mobile-web-app-title=SCMD Pro`
- `apple-mobile-web-app-status-bar-style=black-translucent`
- Apple touch icon references
- `viewport-fit=cover` on mobile base
- safe-area padding via `env(safe-area-inset-*)`

Still to verify on physical iOS:

- Add to Home Screen behavior.
- standalone display mode.
- bottom navigation safe-area on devices with home indicator.
- storage eviction behavior under low storage.

## Performance review

Current strengths:

- Tailwind output is minified.
- Static assets are served through hashed/static pipeline.
- Vendor assets are local, reducing third-party network dependency.

Current gaps:

- No measured bundle analysis output.
- No route-level JS splitting because this is not SPA architecture.
- `staticfiles/` appears in source ZIP; release contract should ensure it is not packaged as source input.
- Large background images exist and should be responsive/lazy-loaded where used.

## Implementation plan

### Phase 1 — Installable foundation

Files modified/created in this patch:

- `static/manifest.json`
- `static/img/brand/pwa-icon-72x72.png`
- `static/img/brand/pwa-icon-96x96.png`
- `static/img/brand/pwa-icon-128x128.png`
- `static/img/brand/pwa-icon-144x144.png`
- `static/img/brand/pwa-icon-152x152.png`
- `static/img/brand/pwa-icon-384x384.png`
- `templates/base.html`
- `operations/templates/operations/mobile/base_mobile.html`
- `operations/templates/operations/mobile/base_mobile_revamped.html`

### Phase 2 — Service worker and offline shell

Files modified/created in this patch:

- `templates/sw.js`
- `static/pwa/offline.html`
- `static/pwa/pwa-register.js`
- `main/tests/test_pwa_contract.py`

### Phase 3 — Offline mode with IndexedDB queue

Recommended new files:

- `static/pwa/offline-db.js`
- `static/pwa/offline-queue.js`
- `operations/api_offline_sync.py`
- `operations/application/offline_sync_use_cases.py`
- `operations/tests_offline_sync.py`

Required server contracts:

- idempotency key per offline mutation.
- conflict policy.
- audit trail for replayed mutations.
- role/scope policy re-check at sync time.

### Phase 4 — Push notification

Recommended files:

- `notifications/push_service.py`
- `notifications/api_views.py`
- `static/pwa/push-client.js`
- `notifications/tests_push_subscription.py`

Preferred provider: FCM if Firebase is already operational; otherwise standards-based Web Push with VAPID.

## Final verdict

Current codebase before patch: **NOT READY — 46/100**.

After this v3 patch: **PARTIALLY READY — estimated 76/100**, pending Docker/browser verification.

Not yet READY because production-grade offline writes, IndexedDB sync queue, push notification, and real Lighthouse/browser validation are not complete.


## v2 backtest addendum

Independent backtest of the first PWA foundation patch found three issues that prevented calling it optimal:

1. `/sw.js` was served by a generic template view without explicit no-store and root-scope headers.
2. Cache purge was link-click oriented and did not cover the existing logout form POST pattern.
3. `cache.addAll()` could fail the whole install flow if any optional asset was temporarily missing.

The v2 patch fixes these without changing authentication, database schema, or mobile business flows. It still intentionally avoids offline write replay until idempotency keys, conflict policy, and audit replay semantics are designed.

## v3 install prompt addendum

Independent review after v2 found that the foundation was installable in principle but did not actively propose installation when users visited the system. That meant users had to discover the browser install affordance manually.

The v3 patch adds a safe install prompt UX:

1. Chromium/Desktop/Android: captures `beforeinstallprompt`, stores the deferred event in memory, and shows a controlled SCMD Pro install banner.
2. iOS Safari: shows Add to Home Screen instructions because Safari does not expose `beforeinstallprompt`.
3. Auth/admin/password pages: prompt is suppressed to avoid distracting from sensitive flows.
4. Standalone mode: prompt is suppressed once installed.
5. Storage: dismissal is session-scoped only; no token or credential is stored.

This improves discoverability and install conversion while preserving security boundaries.

## Addendum — v4 install prompt entrypoint fix

Backtest after v3 showed that users opening `http://localhost:8000/` were redirected to `/login/`, but the standalone login template did not include the PWA manifest or registration script. The install prompt was also suppressed on `/login/`.

Patch v4 fixes this by adding the PWA entrypoint to `main/templates/main/login.html`, `main/templates/main/homepage.html`, and `templates/base_public.html`, and by allowing a safe install suggestion on `/login/` while keeping `/admin/`, `/logout/`, and password reset/change flows suppressed. A manual install hint is shown when the browser does not fire `beforeinstallprompt` immediately.
