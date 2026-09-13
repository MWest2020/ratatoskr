# Change: terug naar de PWA, de APK gaat weg

## Why

De Android-app (TWA, gisteren gebouwd) doet precies wat een TWA doet als hij zijn
herkomst niet kan verifiëren: hij valt terug op een browservenster **met
adresbalk**. Mark: *"als ik app open echt even lelijk een google bar... dit is
tacky."*

Serverzijde is er niets mis: `/.well-known/assetlinks.json` geeft 200, de
vingerafdruk komt overeen met de APK, het package klopt. Het probleem is
structureel: Chrome haalt die verificatie op **bij het starten**, en deze origin
zit alleen op het tailnet. Start je de app terwijl Tailscale nog verbindt, dan
faalt de controle en krijg je de balk. Dat gaat niet over.

En het bittere deel: de gewone geïnstalleerde PWA had dit nooit. `display:
standalone` geeft al geen browser-interface, en doet geen assetlinks-controle.
De APK bracht één ding — een echt app-icoon met de juiste naam — en kostte
daarvoor een verificatie die op een tailnet niet betrouwbaar is.

## What Changes

- **De APK verdwijnt van de installatie**: de route `/ratatoskr.apk`, het
  bestand in het datavolume, en `/.well-known/assetlinks.json` (dood gewicht
  zonder app).
- **`docs/how-to/android-app.md` wordt een verslag**, geen handleiding: wat we
  gebouwd hebben, waarom het niet past, en wat je in plaats daarvan doet.
  Weggooien zou de volgende persoon dezelfde middag laten herhalen.
- **De PWA is weer de weg**: `docs/how-to/pwa-installeren.md` is weer de enige
  instructie.
- **Het bouwspul onder `android/` gaat weg, de ondertekensleutel blijft.** Een
  bouwpijplijn voor iets dat we niet meer serveren is precies het soort dood
  gewicht dat later voor werkend wordt aangezien. De sleutel is het enige
  onvervangbare deel — Android ontleent de identiteit van een app daaraan — en
  kost versleuteld niets om te bewaren.
- **Het icoon wordt een eekhoorn.** Het huisje was van "boomhuis"; de naam is
  Ratatoskr, de eekhoorn die langs Yggdrasil de boodschappen doet. `icon.svg` is
  voortaan de enige tekening en `chat/gen_icons.py` rastert die alleen nog — de
  vorige opzet tekende het glyph twee keer, in Python én in SVG, en die liepen
  uiteen.

## Impact

- Gewijzigd: `chat/server.py`, `chat/statics.py`, `chat/sw.js` (cache-bump),
  `chat/test_server.py`, `chat/gen_icons.py`, `chat/icon.svg` + de drie PNG's,
  de twee how-to's.
- Verwijderd: `chat/well-known/assetlinks.json`, `android/`, de APK op de VM.
- Spec: de requirement over de Android-app wordt ingetrokken.
