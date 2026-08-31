// Boomhuis PWA service worker.
// - De PAGINA (navigatie/index.html): netwerk-eerst MET timeout → een herlaad
//   toont online de laatste versie, maar een koude launch vóór de tailnet-tunnel
//   op is valt binnen ~3s terug op de cache i.p.v. te hangen. De netwerk-fetch
//   loopt na een timeout dóór en ververst de cache alsnog (waitUntil).
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
  // Veerkrachtig: één falende shell-URL laat de hele install (en dus v2) niet
  // sneuvelen — cache elk item los, negeer individuele fouten.
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.all(SHELL.map((u) => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function putCache(req, res) {
  // fire-and-forget mét .catch: een volle-opslag-QuotaExceededError mag geen
  // unhandled rejection in de worker worden.
  caches.open(CACHE).then((c) => c.put(req, res)).catch(() => {});
}

function fromCache(req, isPage) {
  // Altijd een Response teruggeven, nooit undefined. Alleen een PAGINA valt terug
  // op "/" (de shell); een asset mag dat niet — dan krijg je HTML met de verkeerde
  // content-type. Een asset zonder cache-hit → 503.
  return caches.match(req)
    .then((hit) => hit || (isPage ? caches.match("/") : null))
    .then((hit) => hit || new Response("offline", {
      status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } }));
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    if (hit) {
      // achtergrond-update, maar serveer meteen de cache
      fetch(req).then((res) => { if (res && res.status === 200) putCache(req, res.clone()); }).catch(() => {});
      return hit;
    }
    return fetch(req).then((res) => {
      if (res && res.status === 200) putCache(req, res.clone());
      return res || fromCache(req, false);
    }).catch(() => fromCache(req, false));
  });
}

function networkFirst(e) {
  const req = e.request;
  // De fetch loopt volledig af en ververst de cache bij succes — óók als de race
  // hieronder al door de timeout is beslist. waitUntil houdt de worker levend.
  const fresh = fetch(req.url, { cache: "no-store" }).then((res) => {
    if (res && res.ok) putCache(req, res.clone());
    return res;
  }).catch(() => null);
  e.waitUntil(fresh);
  const timeout = new Promise((resolve) => setTimeout(() => resolve(null), NET_TIMEOUT));
  return Promise.race([fresh, timeout]).then((res) => (res && res.ok) ? res : fromCache(req, true));
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") {
    return; // API/niet-GET: altijd live, nooit via de cache
  }
  const isPage = e.request.mode === "navigate" ||
    url.pathname === "/" || url.pathname === "/index.html";
  e.respondWith(isPage ? networkFirst(e) : cacheFirst(e.request));
});
