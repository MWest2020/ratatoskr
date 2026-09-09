# Tasks — uitweg-uit-een-bevroren-pwa

## 1. Het verbindingsbericht

- [x] 1.1 `chat/app-verbinding.js`: bericht met adres en laatst geziene fout.
- [x] 1.2 `app.js` en `app-ui.js` geven hun fout door in plaats van 'm te laten
      vallen.

## 2. De uitweg

- [x] 2.1 Knop *opnieuw proberen*: probeert direct opnieuw, zonder op de poll
      te wachten.
- [x] 2.2 Knop *app verversen*: meldt service workers af, wist caches, herlaadt.
- [x] 2.3 Service worker registreren met `updateViaCache: "none"`.

## 3. Inbedden

- [x] 3.1 Scripttag in `index.html`, en het bestand in de shell-lijst én de
      verse assets van `sw.js`. Plus in de statics-tabel van `server.py`: die
      is een allowlist, dus zonder regel daar gaf het nieuwe bestand een 404 —
      precies wat de e2e-test als eerste liet zien.
- [x] 3.2 Cache-versie ophogen zodat de nieuwe shell binnenkomt.

## 4. Nameten

- [x] 4.1 `offline-boot.js` controleert dat de melding het adres en de fout
      noemt, en dat beide knoppen er zijn.
- [x] 4.2 De rest van de e2e-suite blijft groen: api.sh 36/36, ui.js 20/20,
      deeplink.js 5/5, xss.js alles, verify.sh groen. offline-boot.js 12/12.
- [x] 4.3 Uitgerold en in een echte browser nagemeten: met een oude cache
      erbij gezet, na *app verversen* is die weg, staat er `?vers=` in de URL
      en werkt de app weer. Tellen van workers/caches ná het herladen zegt
      niets — de app registreert zijn worker dan terecht opnieuw.
