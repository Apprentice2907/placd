// Placd Service Worker — Sprint 3
const CACHE_VERSION = 'placd-v1';
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const API_CACHE = `${CACHE_VERSION}-api`;
const IMG_CACHE = `${CACHE_VERSION}-img`;

const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// ── Install: pre-cache app shell ──────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith('placd-') && k !== SHELL_CACHE && k !== API_CACHE && k !== IMG_CACHE)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch strategy ────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle GET requests
  if (request.method !== 'GET') return;

  // Images → Cache First, 7-day TTL
  if (request.destination === 'image' || url.pathname.match(/\.(png|jpg|jpeg|svg|webp|ico)$/)) {
    event.respondWith(cacheFirst(IMG_CACHE, request, 7 * 24 * 60 * 60));
    return;
  }

  // API: search → Network First, fallback to cache
  if (url.pathname.includes('/api/jobs') && url.pathname.includes('search')) {
    event.respondWith(networkFirst(API_CACHE, request));
    return;
  }

  // API: job detail → Stale While Revalidate, 24h TTL
  if (url.pathname.match(/\/api\/jobs\/[^/]+$/)) {
    event.respondWith(staleWhileRevalidate(API_CACHE, request, 24 * 60 * 60));
    return;
  }

  // App shell (HTML/CSS/JS) → Cache First
  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirst(SHELL_CACHE, request));
    return;
  }
});

// ── Strategies ────────────────────────────────────────────────────────────

async function cacheFirst(cacheName, request, maxAge) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    if (maxAge) {
      const dateHeader = cached.headers.get('date');
      if (dateHeader) {
        const age = (Date.now() - new Date(dateHeader).getTime()) / 1000;
        if (age > maxAge) {
          return fetchAndCache(cache, request);
        }
      }
    }
    return cached;
  }
  return fetchAndCache(cache, request);
}

async function networkFirst(cacheName, request) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request.clone());
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(cacheName, request, maxAge) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetchAndCache(cache, request);
  if (cached) {
    if (maxAge) {
      const dateHeader = cached.headers.get('date');
      if (dateHeader) {
        const age = (Date.now() - new Date(dateHeader).getTime()) / 1000;
        if (age > maxAge) return fetchPromise;
      }
    }
    return cached;
  }
  return fetchPromise;
}

async function fetchAndCache(cache, request) {
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    return new Response('Network error', { status: 503 });
  }
}

// ── Background Sync: queue failed apply-clicks ────────────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'retry-apply') {
    event.waitUntil(retryPendingApplyClicks());
  }
});

async function retryPendingApplyClicks() {
  // In v1 we just log — full implementation would read from IndexedDB queue
  console.log('[SW] Retrying pending apply clicks');
}
