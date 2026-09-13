// Boomhuis PWA service worker.
// - The PAGE (navigation/index.html): network first WITH a timeout → online a
//   reload shows the latest version, but a cold launch before the tailnet tunnel
//   is up falls back on the cache within ~3s instead of hanging. The network fetch
//   keeps running after a timeout and refreshes the cache anyway (waitUntil).
// - Statics (icons, manifest): cache first with a background update.
// - /api/*: NEVER cached (chat is realtime, git is the truth).
const CACHE = "boomhuis-shell-v28";  // v28: says so when you are in a tab, not the app
// A version bump wipes every older cache on `activate`. That is the only thing
// that reliably unsticks an installed PWA stuck on the old JS: network first only
// helps once the app runs, and that was exactly the bug where it did not.
const NET_TIMEOUT = 3000;
const SHELL = [
  "/",
  "/index.html",
  "/app.css",
  "/repos.css",
  "/header.css",
  "/board.css",
  "/login.css",
  "/app.js",
  "/app-cache.js",
  "/app-connection.js",
  "/app-auth.js",
  "/login.js",
  "/app-modal.js",
  "/app-ui.js",
  "/app-repos.js",
  "/app-board.js",
  "/app-push.js",
  "/app-update.js",
  "/manifest.webmanifest",
  "/icon.svg",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  // Resilient: one failing shell URL must not sink the whole install (and so v2)
  // — cache each item separately, ignore individual errors.
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
  // fire-and-forget WITH a .catch: a storage-full QuotaExceededError must not
  // become an unhandled rejection in the worker.
  caches.open(CACHE).then((c) => c.put(req, res)).catch(() => {});
}

function fromCache(req, isPage) {
  // Always return a Response, never undefined. Only a PAGE falls back on "/" (the
  // shell); an asset must not — you would get HTML with the wrong content type. An
  // asset without a cache hit → 503.
  return caches.match(req)
    .then((hit) => hit || (isPage ? caches.match("/") : null))
    .then((hit) => hit || new Response("offline", {
      status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } }));
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    if (hit) {
      // background update, but serve the cache straight away
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
  // The fetch runs to completion and refreshes the cache on success — even when
  // the race below has already been decided by the timeout. waitUntil keeps the
  // worker alive.
  const fresh = fetch(req.url, { cache: "no-store" }).then((res) => {
    if (res && res.ok) putCache(req, res.clone());
    return res;
  }).catch(() => null);
  e.waitUntil(fresh);
  const timeout = new Promise((resolve) => setTimeout(() => resolve(null), NET_TIMEOUT));
  // isNav decides the fallback: a navigation may fall back on "/" (the shell), an
  // asset (app.js/app.css) may not — that gets its own cache or a 503.
  return Promise.race([fresh, timeout]).then((res) => (res && res.ok) ? res : fromCache(req, isNav));
}

// The app shell (HTML + app.css + app.js + app-ui.js) is network first so a
// reload shows the latest version; now that the JS/CSS are separate assets they
// need the same freshness as the page. Icons and manifest stay cache first.
const FRESH_ASSETS = new Set(["/app.css", "/header.css", "/repos.css", "/board.css", "/login.css", "/app.js", "/app-cache.js", "/app-connection.js", "/app-auth.js", "/login.js", "/app-modal.js", "/app-ui.js", "/app-repos.js", "/app-board.js", "/app-push.js", "/app-update.js"]);

// Web Push: show a notification on an incoming push.
self.addEventListener("push", (e) => {
  let d = { title: "Ratatoskr", body: "" };
  try { if (e.data) d = e.data.json(); } catch (_) { if (e.data) d.body = e.data.text(); }
  // NO fixed tag: with a constant tag every new notification wiped the previous
  // one (verdict B overwrites verdict A). Only group when the payload explicitly
  // supplies a tag (then WITH renotify so it still notifies again).
  const opts = { body: d.body || "", icon: "/icon-192.png", badge: "/icon-192.png",
                 data: { url: d.url || "/" } };
  if (d.tag) { opts.tag = d.tag; opts.renotify = true; }
  e.waitUntil(self.registration.showNotification(d.title || "Ratatoskr", opts));
});
// Click on the notification: focus an open window or open the app.
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) {
      if ("focus" in w) {
        // Existing window: navigate it to the url from the notification too —
        // focus() alone let d.url evaporate silently.
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
    return; // API or non-GET: always live, never through the cache
  }
  const isNav = e.request.mode === "navigate" ||
    url.pathname === "/" || url.pathname === "/index.html" ||
    url.pathname === "/login";   // a page too: network first
  const fresh = isNav || FRESH_ASSETS.has(url.pathname);
  e.respondWith(fresh ? networkFirst(e, isNav) : cacheFirst(e.request));
});
