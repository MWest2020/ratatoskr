## Why

De service worker cachet de app-shell cache-first, dus een herlaad toont de
gecachete (soms oude) versie en haalt de update pas op de achtergrond op — de
nieuwe UI verschijnt pas bij de volgende keer openen. Verwarrend bij een app die
vaak verandert; de gebruiker denkt dat een update niet is doorgekomen.

## What Changes

- **Service worker netwerk-eerst voor de pagina** (navigatie/index.html): elke
  herlaad toont de laatste versie; offline valt 'ie terug op de cache. Statics
  (iconen, manifest) blijven cache-eerst; `/api/*` blijft altijd live.
- **Cache-versie gebumpt** (v2) zodat de oude gecachete shell wordt opgeruimd.
