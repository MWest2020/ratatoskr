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

## 3. `fetch(url, {cache: "no-store"})` i.p.v. de request ongewijzigd doorgeven

**Keuze:** de pagina-fetch forceert `no-store`.

**Verworpen:** `fetch(req)` ongewijzigd. Die erft de cache-mode van het request:
een expliciete reload is `no-cache` (haalt vers), maar een gewone home-screen-
launch is `default` — dan mag de HTTP-cache van de browser de fetch stil met een
oude respons bedienen, buiten de service worker om. `no-store` omzeilt dat, zodat
de fresh-garantie ook bij een launch geldt.
