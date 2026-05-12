/*
 * Service Worker for OM SOTA — Activation Precheck
 * 3-tier caching: app-shell (precache), google-fonts, map-tiles
 */

const APP_VERSION = '1.9.0';
const CACHE_SHELL   = 'app-shell-v' + APP_VERSION;
const CACHE_FONTS   = 'google-fonts-v1';
const CACHE_TILES   = 'map-tiles-v1';
const MAX_TILES     = 2000;

/* ── Pre-cache list (app shell) ──────────────────────────── */
const SHELL_URLS = [
  './',
  'summits.json',
  'vchu.json',
  'osm_pa.json',
  'icon.svg',
  'icon-192.png',
  'favicon.ico',
  'manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/vue@3.5.13/dist/vue.global.prod.js',
  'https://unpkg.com/socket.io-client@4.7.5/dist/socket.io.min.js',
];

/* ── Install: pre-cache app shell ────────────────────────── */
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_SHELL)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

/* ── Activate: purge old caches ──────────────────────────── */
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith('app-shell-') && k !== CACHE_SHELL)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

/* ── Fetch: route by URL pattern ─────────────────────────── */
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // 1) ŠOPSR WMS — network only (fail silently offline)
  if (url.hostname === 'maps.sopsr.sk') {
    e.respondWith(
      fetch(e.request).catch(() => new Response('', { status: 503 }))
    );
    return;
  }

  // 1b) point2point API / Socket.IO — network only
  if (url.hostname === 'point2point.trgo.sk') {
    e.respondWith(
      fetch(e.request).catch(() => new Response('', { status: 503 }))
    );
    return;
  }

  // 2) version.json — always network (for update detection)
  if (url.pathname.endsWith('version.json')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }

  // 3) Google Fonts CSS — network-first (may contain updated font URLs)
  if (url.hostname === 'fonts.googleapis.com') {
    e.respondWith(networkFirst(e.request, CACHE_FONTS));
    return;
  }

  // 4) Google Fonts woff2 files — cache-first (immutable)
  if (url.hostname === 'fonts.gstatic.com') {
    e.respondWith(cacheFirst(e.request, CACHE_FONTS));
    return;
  }

  // 5) Map tiles (CARTO basemap, Mapy.cz) — cache-first + FIFO eviction
  if (url.hostname.endsWith('.basemaps.cartocdn.com') || url.hostname === 'api.mapy.cz') {
    e.respondWith(cacheTile(e.request));
    return;
  }

  // 6) App shell & data — network-first during dev, ensures latest code on refresh
  e.respondWith(networkFirst(e.request, CACHE_SHELL));
});

/* ── Strategies ──────────────────────────────────────────── */

/** Cache-first: serve from cache, fall back to network (and cache the response) */
function cacheFirst(request, cacheName) {
  return caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (response.ok) {
        const clone = response.clone();
        caches.open(cacheName).then((c) => c.put(request, clone));
      }
      return response;
    });
  }).catch(() => caches.match(request));
}

/** Network-first: try network, fall back to cache */
function networkFirst(request, cacheName) {
  return fetch(request).then((response) => {
    if (response.ok) {
      const clone = response.clone();
      caches.open(cacheName).then((c) => c.put(request, clone));
    }
    return response;
  }).catch(() => caches.match(request));
}

/** Map tile caching with FIFO eviction at MAX_TILES */
function cacheTile(request) {
  return caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (response.ok) {
        const clone = response.clone();
        caches.open(CACHE_TILES).then((cache) => {
          cache.put(request, clone);
          // FIFO eviction: if over limit, delete oldest entries
          cache.keys().then((keys) => {
            if (keys.length > MAX_TILES) {
              const toDelete = keys.length - MAX_TILES;
              for (let i = 0; i < toDelete; i++) {
                cache.delete(keys[i]);
              }
            }
          });
        });
      }
      return response;
    }).catch(() => caches.match(request));
  });
}
