# Change: herstel-na-koude-start

## Why

Mark: *"boomhuis hangt op laden"*. Nagemeten op 2026-09-09: de relay, de
comms-server en elk API-pad zijn gezond en snel (kanalen 15 ms, overzicht
200 ms, berichten van #general 30 ms voor 62 KB). Het probleem zit in de
app zelf.

De service worker doet precies wat de spec vraagt: bij een koude launch
vóór de tailnet-tunnel op is, valt hij binnen 3 s terug op de gecachete
shell in plaats van te hangen. Maar dán begint de app te draaien zonder
netwerk, en `init()` opent met `await loadChannels()` — een `fetch`
zónder `try`. Die faalt, `init()` sneuvelt, en daarmee:

- wordt de poll-timer (`setInterval(refresh, 4000)`) **nooit** gezet;
- komt er geen `visibilitychange`-luisteraar;
- blijft `#msgs` staan op `laden…`.

Er is daarna niets meer dat het opnieuw probeert. De tunnel komt op, de
API is bereikbaar, en de app blijft hangen tot een handmatige herlaad —
die op een telefoon vaak weer te vroeg komt. `refresh()` zwijgt bij een
netwerkfout ook volledig (`catch(e){ return; }`), dus de gebruiker ziet
nooit wát er mis is: alleen "laden…", voorgoed.

Dat is één regel spec die ontbreekt: de shell mag terugvallen op de
cache, maar dan moet de app zichzelf herstellen zodra het netwerk er is.

## What changes

- **`init()` zet eerst zijn timers en luisteraars, dan pas data.** Wat er
  ook misgaat bij het laden, de poll blijft draaien.
- **`loadChannels()` faalt zacht** (`false` in plaats van een exception)
  en wordt herhaald tot de kanalen binnen zijn.
- **Een zichtbare toestand in plaats van eeuwig "laden…"**: geen
  verbinding → dat staat er, met de mededeling dat het opnieuw geprobeerd
  wordt. Zodra het lukt verdwijnt die vanzelf.
- **`online` en `visibilitychange` proberen het meteen opnieuw**, zodat
  de app herstelt op het moment dat de tunnel opkomt in plaats van bij de
  volgende poll.

## Wat hier NIET in zit

- Geen wijziging aan de service worker: die doet het goed, en zijn
  cache-fallback is juist wat deze situatie veroorzaakt én wat je wilt
  hebben.
- Geen offline-lezen van berichten. De cache slaat bewust geen `/api/`
  op (chat is realtime); dat blijft zo.

## Impact

- Alleen `chat/app.js` en `chat/app-ui.js`.
- Nieuwe e2e-test `chat/e2e/offline-boot.js` die de storing eerst
  reproduceert: API blokkeren, app laden, deblokkeren, en meten dat de
  app zich herstelt zónder herlaad.
