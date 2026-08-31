// Boomhuis PWA service worker.
// - De PAGINA (navigatie/index.html): netwerk-eerst MET timeout → een herlaad
//   toont online de laatste versie, maar een koude launch vóór de tailnet-tunnel
//   op is valt binnen ~3s terug op de cache i.p.v. te hangen.
// - Statics (iconen, manifest): cache-eerst met achtergrond-update.
// - /api/*: NOOIT cachen (chat is realtime, git is waarheid).
const CACHE = "boomhuis-shell-v2";
const NET_TIMEOUT = 3000;
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

function putCache(req, res) {
  // fire-and-forget, maar mét .catch: een volle-opslag-QuotaExceededError mag
  // geen unhandled rejection in de worker worden.
  caches.open(CACHE).then((c) => c.put(req, res)).catch(() => {});
}

function fromCache(req) {
  // Altijd een Response teruggeven, nooit undefined.
  return caches.match(req)
    .then((hit) => hit || caches.match("/"))
    .then((hit) => hit || new Response("offline", {
      status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } }));
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res && res.status === 200) putCache(req, res.clone());
      return res;
    }).catch(() => hit);
    return hit || net;
  });
}

function networkFirst(req) {
  // no-store: omzeil de HTTP-cache zodat ook een koude launch (cache-mode
  // 'default') vers haalt, niet alleen een expliciete reload (no-cache).
  const fresh = fetch(req.url, { cache: "no-store" });
  const timeout = new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), NET_TIMEOUT));
  return Promise.race([fresh, timeout])
    .then((res) => {
      if (!res || !res.ok) throw new Error("bad status");  // 4xx/5xx → val terug op cache
      putCache(req, res.clone());
      return res;
    })
    .catch(() => fromCache(req));
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
