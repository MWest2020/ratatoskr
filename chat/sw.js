// Boomhuis PWA service worker.
// - De PAGINA (navigatie/index.html): netwerk-eerst MET timeout → een herlaad
//   toont online de laatste versie, maar een koude launch vóór de tailnet-tunnel
//   op is valt binnen ~3s terug op de cache i.p.v. te hangen. De netwerk-fetch
//   loopt na een timeout dóór en ververst de cache alsnog (waitUntil).
// - Statics (iconen, manifest): cache-eerst met achtergrond-update.
// - /api/*: NOOIT cachen (chat is realtime, git is waarheid).
const CACHE = "boomhuis-shell-v14";  // v14: wachtwoord wijzigen in de app
// Een versiebump wist bij `activate` elke oudere cache. Dat is het enige wat
// een geïnstalleerde PWA die op de oude JS vastzit gegarandeerd loskrijgt:
// netwerk-eerst helpt pas als de app draait, en dit was nu juist de bug
// waarbij hij dat niet deed.
const NET_TIMEOUT = 3000;
const SHELL = [
  "/",
  "/index.html",
  "/app.css",
  "/app.js",
  "/app-cache.js",
  "/app-verbinding.js",
  "/app-auth.js",
  "/login.js",
  "/app-modal.js",
  "/app-ui.js",
  "/app-repos.js",
  "/app-push.js",
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

function networkFirst(e, isNav) {
  const req = e.request;
  // De fetch loopt volledig af en ververst de cache bij succes — óók als de race
  // hieronder al door de timeout is beslist. waitUntil houdt de worker levend.
  const fresh = fetch(req.url, { cache: "no-store" }).then((res) => {
    if (res && res.ok) putCache(req, res.clone());
    return res;
  }).catch(() => null);
  e.waitUntil(fresh);
  const timeout = new Promise((resolve) => setTimeout(() => resolve(null), NET_TIMEOUT));
  // isNav bepaalt de fallback: een navigatie mag terugvallen op "/" (de shell),
  // een asset (app.js/app.css) niet — die krijgt z'n eigen cache of 503.
  return Promise.race([fresh, timeout]).then((res) => (res && res.ok) ? res : fromCache(req, isNav));
}

// De app-shell (HTML + app.css + app.js + app-ui.js) is netwerk-eerst zodat een
// herlaad de laatste versie toont; sinds de JS/CSS losse assets zijn moeten die
// dezelfde freshness krijgen als de pagina. Iconen/manifest blijven cache-eerst.
const FRESH_ASSETS = new Set(["/app.css", "/app.js", "/app-cache.js", "/app-verbinding.js", "/app-auth.js", "/login.js", "/app-modal.js", "/app-ui.js", "/app-repos.js", "/app-push.js"]);

// Web Push: toon een notificatie bij een binnenkomende push.
self.addEventListener("push", (e) => {
  let d = { title: "Boomhuis", body: "" };
  try { if (e.data) d = e.data.json(); } catch (_) { if (e.data) d.body = e.data.text(); }
  // GEEN vaste tag: met een constante tag wist elke nieuwe melding de vorige
  // (verdict B overschrijft verdict A). Alleen groeperen als de payload expliciet
  // een tag meegeeft (dan mét renotify zodat 'ie alsnog opnieuw meldt).
  const opts = { body: d.body || "", icon: "/icon-192.png", badge: "/icon-192.png",
                 data: { url: d.url || "/" } };
  if (d.tag) { opts.tag = d.tag; opts.renotify = true; }
  e.waitUntil(self.registration.showNotification(d.title || "Boomhuis", opts));
});
// Klik op de notificatie: focus een open venster of open de app.
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) {
      if ("focus" in w) {
        // Bestaand venster: navigeer het óók naar de url uit de notificatie —
        // enkel focus() liet d.url stil verdampen.
        const go = ("navigate" in w) ? w.navigate(url).catch(() => w) : Promise.resolve(w);
        return go.then((c) => (c || w).focus());
      }
    }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") {
    return; // API/niet-GET: altijd live, nooit via de cache
  }
  const isNav = e.request.mode === "navigate" ||
    url.pathname === "/" || url.pathname === "/index.html" ||
    url.pathname === "/login";   // ook een pagina: netwerk-eerst
  const fresh = isNav || FRESH_ASSETS.has(url.pathname);
  e.respondWith(fresh ? networkFirst(e, isNav) : cacheFirst(e.request));
});
