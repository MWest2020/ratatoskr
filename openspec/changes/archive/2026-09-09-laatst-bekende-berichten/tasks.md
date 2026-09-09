# Tasks — laatst-bekende-berichten

## 1. Opslag

- [x] 1.1 `chat/app-cache.js`: momentopname per kanaal opslaan (tijdstip +
      laatste N berichten), lezen, en oude kanalen snoeien.
- [x] 1.2 `refresh()` bewaart na elke geslaagde ophaal.

## 2. Weergave

- [x] 2.1 Geen verbinding mét momentopname → berichten tonen met een
      gedateerde balk erboven en de bestaande knoppen eronder. Onderweg bleek
      een extra ding nodig: zonder kanaallijst (die komt van de API) weet de
      app niet wélk kanaal open stond, dus die verwijzing wordt apart
      onthouden bij elke kanaalwissel.
- [x] 2.2 Geen verbinding zónder momentopname → de melding zoals nu.
- [x] 2.3 Verse berichten verdringen de balk.

## 3. Inbedden

- [x] 3.1 Scripttag in `index.html`, bestand in de shell-lijst én de verse
      assets van `sw.js`, en in de statics-allowlist van `server.py`.
- [x] 3.2 Cacheversie ophogen.

## 4. Nameten

- [x] 4.1 `offline-boot.js`: online laden, API blokkeren, herladen — de
      berichten staan er nog, gedateerd.
- [x] 4.2 De rest blijft groen: offline-boot.js 16/16, api.sh 36/36,
      ui.js 20/20, deeplink.js 5/5, xss.js groen, verify.sh (66 unittests).
- [x] 4.3 Uitgerold en in een echte browser nagemeten.
