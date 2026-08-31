# Design: add-pwa-fresh-reload

Niet-voor-de-hand-liggende keuzes met verworpen alternatieven (CLAUDE.md-eis).

## 1. Netwerk-eerst voor de pagina (i.p.v. stale-while-revalidate + update-prompt)

**Keuze:** de service worker haalt de pagina netwerk-eerst op; een herlaad toont
online meteen de laatste versie.

**Verworpen:** cache-eerst / stale-while-revalidate met een "nieuwe versie
beschikbaar — herladen?"-prompt. Dat is de mainstream-aanpak, maar het vergt UI
en een tweede handeling van de gebruiker, en toont per definitie één keer de oude
versie. Voor een intern tailnet-tooltje dat vaak verandert weegt "altijd vers bij
herlaad" zwaarder dan een offline-first-optimalisatie. De app is toch bijna altijd
online wanneer je 'm gebruikt (tailnet).

## 2. Netwerk-timeout van 3s met cache-fallback

**Keuze:** de netwerk-fetch racet tegen een timeout van 3s; daarna valt 'ie terug
op de cache.

**Verworpen:** netwerk-eerst zónder timeout. De PWA is alleen over Tailscale
bereikbaar en het home-screen-icoon wordt vaak aangetikt vóór de tunnel op is —
een fetch naar een onbereikbare host hangt dan op de OS-timeout (tientallen
seconden). De timeout maakt de koude launch snel: binnen 3s de gecachete shell,
en de volgende herlaad (tunnel op) haalt vers.

## 3. `fetch(url, {cache: "no-store"})` — defensief

**Keuze:** de pagina-fetch zet expliciet `no-store`.

**Context:** het backend stuurt al `Cache-Control: no-store` op elke respons
(`chat/server.py` `_send`), dus de browser-HTTP-cache hoort de pagina sowieso niet
te bewaren. `no-store` op de fetch is daarmee **belt-and-suspenders**: het maakt de
service worker onafhankelijk van de server-headers, zodat een gewone home-screen-
launch (cache-mode `default`) ook zonder die header niet stil een oude respons uit
de HTTP-cache kan krijgen. **Verworpen:** `fetch(req)` ongewijzigd doorgeven en
enkel op de server-header vertrouwen — dat koppelt de fresh-garantie aan een
config die elders staat en stil kan wijzigen.
