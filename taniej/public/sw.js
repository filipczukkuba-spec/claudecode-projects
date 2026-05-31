// Minimal service worker — its main job is to make the app installable
// (Chrome requires a registered SW with a fetch handler to fire
// beforeinstallprompt). Strategy is deliberately conservative so users never
// see stale prices: navigations are network-first (fresh data, cached page
// only as offline fallback); hashed static assets are cache-first.

const CACHE = "tk-v1";
const OFFLINE_URLS = ["/"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(OFFLINE_URLS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Never cache dynamic/server endpoints — always hit the network.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/go/") || url.pathname.startsWith("/admin")) {
    return;
  }

  // Navigations: network-first so prices/promos stay fresh; fall back to the
  // cached shell when offline.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then((m) => m || caches.match("/")))
    );
    return;
  }

  // Hashed static assets + icons: cache-first.
  if (url.pathname.startsWith("/_next/static") || /\.(png|svg|ico|webp|woff2?)$/.test(url.pathname)) {
    event.respondWith(
      caches.match(req).then((m) =>
        m ||
        fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
      )
    );
  }
});
