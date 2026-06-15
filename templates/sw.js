// file: templates/sw.js
<<<<<<< HEAD
// SCMD Pro PWA Service Worker - root scope.
// Security rule: never cache authentication endpoints, token responses, camera streams, or non-GET mutations.

const SCMD_SW_VERSION = "{{ scmd_sw_version|escapejs }}";
const STATIC_CACHE = `scmd-pro-${SCMD_SW_VERSION}-static`;
const API_CACHE = `scmd-pro-${SCMD_SW_VERSION}-api`;
const PAGE_CACHE = `scmd-pro-${SCMD_SW_VERSION}-page`;
const OFFLINE_URL = "/static/pwa/offline.html";

const CORE_ASSETS = [
  OFFLINE_URL,
  "/static/manifest.json",
  "/static/css/dist/styles.css",
  "/static/common/css/brand_system.css",
  "/static/vendor/fonts/be-vietnam-pro.css",
  "/static/vendor/fontawesome/css/all.min.css",
  "/static/vendor/dexie/dexie.min.js",
  "/static/vendor/htmx/htmx.min.js",
  "/static/vendor/nprogress/nprogress.min.js",
  "/static/vendor/nprogress/nprogress.css",
  "/static/pwa/pwa-register.js",
  "/static/img/brand/logo-symbol.svg",
  "/static/img/brand/logo-symbol-white.svg",
  "/static/img/brand/android-chrome-192x192.png",
  "/static/img/brand/android-chrome-512x512.png",
  "/static/img/brand/maskable-icon-512x512.png"
];

const NETWORK_ONLY_PREFIXES = [
  "{% url 'admin:index' %}",
  "/api/schema/",
  "/api/docs/",
  "/api/redoc/",
  "/accounts/",
  "/login/",
  "/logout/",
  "/password-change/",
  "/password-reset/",
  "/operations/api/v1/mobile/checkin/",
  "/operations/api/v1/mobile/checkout/",
  "/operations/api/v1/mobile/alive-check/respond/",
  "/operations/api/dashboard/data/",
  "/operations/mobile/sos/",
  "/inspection/mobile/ghi-nhan/",
  "/media/"
];

// Only selected same-origin GET JSON endpoints are eligible. These responses are
// user-scoped, so they are purged on login/logout/password auth boundaries.
const CACHEABLE_API_PREFIXES = [
  "/operations/api/dashboard/alive-check-violations/",
  "/operations/api/mobile/ca-truc/",
  "/operations/api/mobile/su-co/"
];

const PUBLIC_NAVIGATION_CACHE_PATHS = [
  "/",
  "/login/",
  "/password-reset/"
];

function isSameOrigin(requestUrl) {
  return requestUrl.origin === self.location.origin;
}

function hasNetworkOnlyPrefix(pathname) {
  return NETWORK_ONLY_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function isAuthenticationLikeRequest(requestUrl) {
  return /(auth|token|jwt|login|logout|password|csrf|session)/i.test(requestUrl.pathname + requestUrl.search);
}

function isStaticAsset(pathname) {
  return pathname.startsWith("/static/");
}

function isCacheableApi(pathname) {
  return CACHEABLE_API_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function isPublicEntryNavigation(request, requestUrl) {
  return request.mode === "navigate" && PUBLIC_NAVIGATION_CACHE_PATHS.includes(requestUrl.pathname);
}

function isValidCacheResponse(response) {
  return response && response.ok && response.type === "basic";
}

async function safePrecache(cacheName, urls) {
  const cache = await caches.open(cacheName);
  await Promise.allSettled(urls.map(async (assetUrl) => {
    const response = await fetch(assetUrl, { credentials: "same-origin", cache: "reload" });
    if (isValidCacheResponse(response)) {
      await cache.put(assetUrl, response);
    }
  }));
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (isValidCacheResponse(response)) {
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(API_CACHE);
  const cached = await cache.match(request);
  const networkPromise = fetch(request).then((response) => {
    const contentType = response.headers.get("content-type") || "";
    const cacheControl = response.headers.get("cache-control") || "";
    const hasSetCookie = response.headers.has("set-cookie");
    const isJson = /json/i.test(contentType);
    const isNoStore = /no-store/i.test(cacheControl);
    if (isValidCacheResponse(response) && isJson && !hasSetCookie && !isNoStore) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);
  return cached || networkPromise;
}

async function networkFirstPage(request, options = {}) {
  const { allowCache = false, preloadResponsePromise = null } = options;
  try {
    const preloadedResponse = preloadResponsePromise ? await preloadResponsePromise : null;
    const response = preloadedResponse || await fetch(request);
    if (isValidCacheResponse(response)) {
      const cacheControl = response.headers.get("cache-control") || "";
      const url = new URL(request.url);
      const isMobilePage = url.pathname.startsWith("/operations/mobile/") || url.pathname.startsWith("/inspection/mobile/");
      if ((allowCache || isMobilePage) && !/no-store/i.test(cacheControl)) {
        const cache = await caches.open(PAGE_CACHE);
        await cache.put(request, response.clone());
      }
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    return cached || caches.match(OFFLINE_URL);
  }
}

async function clearScmdCaches() {
  const keys = await caches.keys();
  await Promise.all(keys.filter((key) => key.startsWith("scmd-pro-")).map((key) => caches.delete(key)));
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(safePrecache(STATIC_CACHE, CORE_ASSETS));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const expected = new Set([STATIC_CACHE, API_CACHE, PAGE_CACHE]);
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith("scmd-pro-") && !expected.has(key)).map((key) => caches.delete(key)));
    if (self.registration.navigationPreload) {
      await self.registration.navigationPreload.enable();
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (!event.data) return;
  if (event.data.type === "SCMD_PWA_CLEAR_CACHES") {
    event.waitUntil(clearScmdCaches());
  }
  if (event.data.type === "SCMD_PWA_SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!isSameOrigin(url)) return;

  if (isPublicEntryNavigation(request, url)) {
    event.respondWith(networkFirstPage(request, {
      allowCache: true,
      preloadResponsePromise: event.preloadResponse,
    }));
    return;
  }

  if (hasNetworkOnlyPrefix(url.pathname) || isAuthenticationLikeRequest(url)) return;

  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (isCacheableApi(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstPage(request, { preloadResponsePromise: event.preloadResponse }));
  }
});
=======
// Service Worker - Root Scope

const CACHE_NAME = 'scmd-v3-root'; // Đổi tên cache mới
const ASSETS_TO_CACHE = [
    '/static/css/scmd_theme.css',
    '/static/img/logo_moi.png',
    '/static/img/default_avatar.png',
    'https://cdn.jsdelivr.net/npm/daisyui@3.9.0/dist/full.css',
    // 'https://cdn.tailwindcss.com/', // <--- Xóa hoặc Comment dòng này lại
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css',
    'https://unpkg.com/dexie/dist/dexie.js'
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) return caches.delete(key);
            }));
        })
    );
    return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    event.respondWith(
        fetch(event.request)
            .then((res) => {
                const resClone = res.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
                return res;
            })
            .catch(() => caches.match(event.request))
    );
});
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
