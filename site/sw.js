// Service worker for GTHA by Transit.
//
// The network data file (site/data/<city>.bin, ~10-22 MB) is the slow part of
// every first visit. Cache it aggressively: the URL carries ?v=<dataVersion>,
// so a data rebuild is a brand-new cache key and stale data can never be served.
// The app shell (HTML/JS/CSS) uses network-first so code updates propagate.

const CACHE = "gtha-transit-v1";
const DATA_PATH = /\/data\/[a-z]+\.bin$/;

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Only handle our own origin; leave Photon/CDN requests alone.
  if (url.origin !== self.location.origin || event.request.method !== "GET") return;

  if (DATA_PATH.test(url.pathname)) {
    // Network data: cache-first. The ?v= query makes every rebuild a new key.
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(event.request).then(
          (hit) =>
            hit ||
            fetch(event.request).then((res) => {
              if (res.ok) cache.put(event.request, res.clone());
              return res;
            })
        )
      )
    );
  } else {
    // App shell: network-first, fall back to cache when offline.
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return res;
        })
        .catch(() => caches.match(event.request))
    );
  }
});
