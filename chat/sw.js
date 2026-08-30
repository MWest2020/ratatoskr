// Boomhuis PWA service worker — shell-cache + netwerk-eerst voor data.
// De app-shell (icoon, manifest, index) mag offline uit cache; alles onder
// /api/* is live en gaat NOOIT via de cache (chat is realtime, git is waarheid).
const CACHE = "boomhuis-shell-v1";
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

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // API en niet-GET nooit cachen — altijd live.
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") {
    return; // laat de browser normaal netwerken
  }
  // Shell: cache-eerst, val terug op netwerk; update cache op de achtergrond.
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
