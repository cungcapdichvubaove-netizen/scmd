// file: templates/sw.js
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