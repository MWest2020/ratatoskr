---
status: current
last_reviewed: 2026-09-11
---

# De Android-app

Ratatoskr draait als echte Android-app: een **Trusted Web Activity**. Dat is geen
tweede codebase — het is dezelfde PWA, fullscreen, zonder browserbalk, met
dezelfde service worker, opslag, sessie en pushmeldingen. Een nieuwe versie van
de chat zit er meteen in; de app verander je alleen als de naam, het icoon of de
host verandert.

## Installeren op een toestel

1. Open de chat in de browser en log in.
2. Ga naar `<jouw-url>/ratatoskr.apk`. Die link werkt zónder in te loggen — een
   APK-download start vaak buiten de sessie (de downloadmanager of een
   doorgestuurde link draagt het cookie niet mee), en het bestand bevat niets
   geheims: het is een browser-schil met de hostnaam erin. De netwerklaag
   (tailnet of je proxy) is hier de deur.
3. Android vraagt om installatie uit een onbekende bron toe te staan. Dat hoort:
   deze app komt niet uit de Play Store en dat is de bedoeling.
4. Had je de PWA als snelkoppeling staan? Haal die weg. Android hernoemt een
   bestaande snelkoppeling nooit, dus die blijft "boomhuis" heten.

**Start de app met een adresbalk?** Dan is de verificatie mislukt. Het toestel
moet `<jouw-url>/.well-known/assetlinks.json` kunnen ophalen (dus: op het tailnet
zitten), en de vingerafdruk daarin moet horen bij de sleutel waarmee deze APK
ondertekend is.

## Bouwen

Eenmalig op de bouwmachine: JDK 17, de Android-SDK (build-tools 36.1.0 +
platform 36) en `npm i -g @bubblewrap/cli`. Bubblewrap wil de SDK in de oude
indeling zien, dus:

    ln -s $ANDROID_HOME/cmdline-tools/latest/bin $ANDROID_HOME/bin
    ln -s $ANDROID_HOME/cmdline-tools/latest/lib $ANDROID_HOME/lib

Daarna:

    bash android/build.sh      # -> android/ratatoskr-<versie>.apk

Het script haalt de ondertekensleutel uit SOPS in een tijdelijke map, gooit het
gegenereerde Android-project weg (zodat de build volledig uit
`twa-manifest.json` volgt), bouwt, en tekent met `apksigner`.

## Een nieuwe versie uitbrengen

1. In `android/twa-manifest.json`: `appVersion` **en** `appVersionName` naar de
   nieuwe versie, `appVersionCode` één omhoog. Die twee versievelden moeten
   gelijk zijn — lopen ze uiteen, dan zegt de APK iets anders dan het bestand,
   en het bouwscript weigert.
2. `bash android/build.sh`
3. De APK naar de installatie kopiëren (zie hieronder).

De **vingerafdruk verandert niet** zolang je dezelfde sleutel gebruikt, dus
`assetlinks.json` blijft kloppen.

## De APK op een installatie zetten

De APK zit niet in het image: hij is ondertekend voor één origin, dus hij hoort
bij de installatie, niet bij de code. Hij komt in het datavolume:

    vol=$(docker volume inspect -f '{{.Mountpoint}}' <project>_ratatoskr-chat-data)
    sudo mkdir -p "$vol/apk"
    sudo cp android/ratatoskr-<versie>.apk "$vol/apk/ratatoskr.apk"
    sudo chown -R 10001:10001 "$vol/apk"

Daarna is hij te downloaden op `/ratatoskr.apk`, zonder sessie. Staat er niets,
dan geeft die route een nette 404 — geen app geïnstalleerd op deze server.

## Wat je nooit weggooit

`secrets/android-signing.yaml`. Android ontleent de **identiteit** van een app
aan de ondertekensleutel: raak je die kwijt, dan is een volgende build voor
Android een andere app. Iedereen moet de oude verwijderen en de nieuwe
installeren, en `assetlinks.json` krijgt een nieuwe vingerafdruk. Het is het
enige onvervangbare bestand in deze hele keten — de rest is opnieuw te maken.

Uitpakken wanneer je 'm nodig hebt:

    python3 android/extract-key.py /tmp/ks    # en ruim die map daarna op

## Voor een andere installatie

Een APK is gebonden aan één host: die staat in `twa-manifest.json` en in de
asset-links van die origin. Een derde die Ratatoskr zelf draait, bouwt dus een
eigen APK met zijn eigen host, zijn eigen sleutel en zijn eigen
`assetlinks.json`. Het bouwscript is hetzelfde; alleen `host`, `startUrl`,
`webManifestUrl` en `fullScopeUrl` verschillen.
