# Change: uitweg-uit-een-bevroren-pwa

## Why

`herstel-na-koude-start` repareerde de app: valt de eerste fetch om, dan
blijft de poll draaien en herstelt hij zodra het netwerk er is. Nagemeten
in een echte browser tegen de VM, en groen.

Marks geïnstalleerde PWA blijft hangen.

Dat is geen tegenspraak, het is een tweede storing die de eerste
verborg. Een PWA die niet draait, kan zichzelf niet repareren: de nieuwe
`app.js` komt pas binnen als de app een fetch dóét, en precies dat deed
hij niet. De cache-versiebump (v9) helpt alleen ná één geslaagde start.
Zit het apparaat vast op de oude shell — oude service worker, oude JS,
of een PWA die ooit tegen een adres is geïnstalleerd dat niet meer
antwoordt — dan is er vanuit de app geen weg terug.

Wat ontbreekt is niet nog een automatisch herstel, maar twee dingen die
de gebruiker zélf kan doen én zien:

1. **Zien wát er misgaat.** "geen verbinding" zegt niet welk adres is
   geprobeerd of welke fout terugkwam. Met dat ene zinnetje is het
   verschil tussen "de tunnel is nog niet op" en "deze app wijst naar een
   adres dat niet meer bestaat" meteen duidelijk — voor Mark én voor wie
   het later moet uitzoeken.
2. **Eruit kunnen.** Een knop die de service worker afmeldt, alle caches
   wist en opnieuw laadt. Dat is de enige handeling die een vastgelopen
   PWA gegarandeerd loskrijgt zonder hem te verwijderen en opnieuw te
   installeren.

## What changes

- Een nieuw bestandje `chat/app-verbinding.js`: het verbindingsbericht,
  de laatst geziene fout, en de twee knoppen (*opnieuw proberen* en
  *app verversen*). Los, omdat `app.js` en `app-ui.js` allebei tegen de
  200-regelgrens uit `CLAUDE.md` aan zitten.
- Het verbindingsbericht noemt het adres dat geprobeerd is en de fout die
  terugkwam.
- *App verversen* meldt elke service worker af, wist elke cache en
  herlaadt. Daarna is de app per definitie de versie die de server nu
  serveert.
- De service worker wordt geregistreerd met `updateViaCache: "none"`,
  zodat het script zelf nooit uit de HTTP-cache komt.

## Wat hier NIET in zit

- Geen automatische unregister. Een app die zichzelf ongevraagd wist bij
  elke storing, wist ook je ongelezen-status bij een tunnel die twee
  seconden hikt. Dit is een knop, geen reflex.
- Geen wijziging aan het cache-beleid zelf; dat is `herstel-na-koude-start`
  en de service worker doet daar wat de spec vraagt.

## Impact

- `chat/app-verbinding.js` (nieuw), `chat/index.html`, `chat/sw.js`
  (shell-lijst + verse assets), en de aanroepen in `chat/app.js` /
  `chat/app-ui.js`.
- e2e: `offline-boot.js` krijgt er een controle bij dat het bericht het
  adres en de fout noemt, en dat de knoppen er zijn.
