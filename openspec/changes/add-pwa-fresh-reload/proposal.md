## Why

De service worker cachet de app-shell cache-first, dus een herlaad toont de
gecachete (soms oude) versie en haalt de update pas op de achtergrond op — de
nieuwe UI verschijnt pas bij de volgende keer openen. Verwarrend bij een app die
vaak verandert; de gebruiker denkt dat een update niet is doorgekomen.

## What Changes

- **Service worker netwerk-eerst voor de pagina** (navigatie/index.html) met een
  **3s-timeout**: online toont een herlaad de laatste versie, maar een koude
  launch vóór de tailnet-tunnel op is valt binnen 3s terug op de cache i.p.v. te
  hangen. De netwerk-fetch loopt na een timeout dóór en ververst de cache alsnog.
- **`no-store`** op de pagina-fetch (defensief; het backend stuurt al no-store).
- **Fallback-hardening**: 4xx/5xx en fouten vallen terug op de cache; er wordt
  altijd een `Response` teruggegeven (nooit `undefined`); cache-writes met
  `.catch`; de install-handler cachet elk shell-item los (één fout sloopt v2 niet).
- Statics blijven cache-eerst; `/api/*` blijft altijd live. **Cache-versie v2**
  ruimt de oude shell op.
- `chat/README.md` verwijst nu naar de HTTPS-tailnet-URL (secure context, nodig
  voor de service worker) i.p.v. de oude http-LAN-URL.
