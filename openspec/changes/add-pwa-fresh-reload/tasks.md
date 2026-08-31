# Tasks: add-pwa-fresh-reload

- [x] 1.1 sw.js: netwerk-eerst voor navigatie/index.html met 3s-timeout +
      no-store; fetch ververst de cache alsnog na een timeout (waitUntil).
- [x] 1.2 Statics cache-eerst; cache-versie bumpen (v2) zodat de oude shell weg is.
- [x] 1.3 Fallback-hardening: 4xx/5xx→cache, altijd een Response, cache-writes met
      .catch, veerkrachtige install-handler.
- [x] 1.4 chat/README.md naar de HTTPS-tailnet-URL (secure context).
