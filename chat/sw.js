// Boomhuis PWA service worker.
// - De PAGINA (navigatie/index.html): netwerk-eerst → elke herlaad toont de
//   laatste versie; offline valt 'ie terug op de cache.
// - Statics (iconen, manifest): cache-eerst met achtergrond-update.
// - /api/*: NOOIT cachen (chat is realtime, git is waarheid).
const CACHE = "boomhuis-shell-v2";
const SHELL = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icon.svg",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res && res.status === 200) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => hit);
    return hit || net;
  });
}

function networkFirst(req) {
  return fetch(req).then((res) => {
    if (res && res.status === 200) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
    }
    return res;
  }).catch(() => caches.match(req).then((hit) => hit || caches.match("/")));
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") {
    return; // API/niet-GET: altijd live, nooit via de cache
  }
  const isPage = e.request.mode === "navigate" ||
    url.pathname === "/" || url.pathname === "/index.html";
  e.respondWith(isPage ? networkFirst(e.request) : cacheFirst(e.request));
});
