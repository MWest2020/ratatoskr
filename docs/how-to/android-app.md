---
status: verslag
last_reviewed: 2026-09-13
---

# De Android-app (verslag, niet meer in gebruik)

Van 2026-09-12 tot 2026-09-13 heeft Ratatoskr een echte Android-app gehad: een
**Trusted Web Activity**, gebouwd met Bubblewrap. Die is weer weg. De PWA is de
weg. Dit bestand blijft staan zodat we het niet nog een keer proberen zonder de
uitkomst te kennen.

## Wat een TWA is

Geen tweede codebase: een Android-schil die Chrome fullscreen op één origin
opent. Dezelfde service worker, opslag, sessie en pushmeldingen. Aantrekkelijk,
want een nieuwe versie van de chat zit er meteen in.

## Waarom hij weg is

Chrome controleert bij **elke start** of `<origin>/.well-known/assetlinks.json`
bereikbaar is en of de vingerafdruk daarin bij de ondertekensleutel van de
geïnstalleerde APK hoort. Lukt dat niet, dan valt hij terug op een Custom Tab —
mét adresbalk. Dat is precies wat een app *geen* app maakt.

Onze origin zit op het tailnet. Bij een koude start is de Tailscale-verbinding
er vaak nét niet, en dan mislukt die controle. De serverkant was aantoonbaar in
orde (de route gaf 200, de vingerafdruk klopte); het probleem is structureel, en
niet op te lossen aan de kant die van ons is. Marks oordeel, 2026-09-12: *"als
ik app open echt even lelijk een google bar. dit is tacky."*

De geïnstalleerde PWA heeft dit probleem niet: Android controleert daar niets bij
het starten, want er is geen tweede partij die iets moet bewijzen.

## Wat er is weggehaald

- de route `/ratatoskr.apk` en de static `/.well-known/assetlinks.json`
- het bouwspul onder `android/` (`build.sh`, `extract-key.py`,
  `twa-manifest.json`)
- de APK in het datavolume van de draaiende installatie

`secrets/android-signing.yaml` is blijven staan. Android ontleent de identiteit
van een app aan zijn ondertekensleutel: wie 'm weggooit en later toch een APK
uitbrengt, brengt voor Android een *andere* app uit. Het bestand is klein en
versleuteld; weggooien levert niets op en is onomkeerbaar.

## Als het ooit tóch weer moet

Dan eerst dit oplossen, niet opnieuw ontdekken: de app moet starten zonder dat
er op dat moment een verbinding met de origin nodig is. Dat betekent een origin
die altijd bereikbaar is (dus een publieke voordeur, en die is er bewust niet),
of geen TWA maar een schil die zijn eigen UI meebrengt. Zie
[pwa-installeren.md](pwa-installeren.md) voor wat er nu geldt.
