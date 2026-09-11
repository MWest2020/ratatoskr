# Change: Ratatoskr als Android-app

## Why

De PWA werkt, maar hij is een snelkoppeling in een browser en gedraagt zich ook
zo. Drie dingen die dat vandaag kostte, allemaal waargenomen:

- **De naam blijft hangen.** Android leest de manifest-naam bij installatie en
  hernoemt een bestaande snelkoppeling nooit. Na de hernoeming naar Ratatoskr
  (PR #80) staat er op Marks telefoon nog steeds "boomhuis", en daar is
  server-zijdig niets aan te doen.
- **De cache zit in de kritieke lus.** Twee storingen op één dag eindigden in
  "scherm blijft op laden" waar de service worker een oude shell serveerde;
  het herstel is elke keer "unregister, cache wissen, herladen" — precies wat je
  niet kunt als het scherm bevroren is.
- **Er is geen versie.** Welke Ratatoskr draait er op die telefoon? Onbekend.

## What Changes

- Een **Trusted Web Activity** (TWA), gebouwd met Bubblewrap: een echte
  Android-app die dezelfde PWA fullscreen draait, met dezelfde service worker,
  opslag en pushmeldingen. Geen tweede codebase, geen tweede API.
- **`/.well-known/assetlinks.json`** vanaf de eigen origin, met de vingerafdruk
  van de ondertekensleutel. Zonder dat bestand toont Chrome alsnog een
  adresbalk — dan is het een browser in een app-jasje en heb je niets gewonnen.
- **De ondertekensleutel** wordt een secret zoals elk ander in deze repo:
  SOPS+age. Verlies = een app die Android niet meer als dezelfde app herkent en
  die je gebruikers opnieuw moeten installeren.
- **De APK is te downloaden vanaf de eigen installatie**, achter dezelfde deur
  als de rest. Geen Play Store; een derde die dit zelf host, hoort niet langs
  Google te hoeven.
- Een **how-to** voor de volgende versie: wat je bumpt, wat je opnieuw bouwt, en
  wat je nooit weggooit.

## Impact

- Nieuw: `android/` (bubblewrap-project + bouwscript), `chat/statics.py` krijgt
  twee paden erbij (`/.well-known/assetlinks.json`, de APK).
- Gewijzigd: `docs/how-to/pwa-installeren.md` verwijst naar de app.
- Spec: `webchat-pwa` krijgt een requirement over de app en de asset-links.
- Buiten scope: Play Store, iOS, en een app die zonder tailnet werkt. De app is
  de PWA; wat de PWA niet kan, kan de app ook niet.
