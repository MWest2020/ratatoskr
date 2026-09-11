# webchat-pwa

## ADDED Requirements

### Requirement: De installatie levert een Android-app die de PWA draait

De installatie SHALL een Android-app kunnen aanbieden die de eigen PWA fullscreen
draait (Trusted Web Activity), met dezelfde service worker, opslag en sessie als
de browser. De app SHALL geen eigen API, eigen opslag of eigen schermen hebben:
wat de PWA niet kan, kan de app niet.

De origin SHALL `/.well-known/assetlinks.json` serveren met de SHA-256-vingerafdruk
van de sleutel waarmee de app ondertekend is, en dat bestand SHALL bereikbaar zijn
zonder sessie — Chrome haalt het op vóór er een gebruiker is. Ontbreekt het of
klopt de vingerafdruk niet, dan start de app met een adresbalk; dat is een
zichtbare fout, geen stille.

De installatie SHALL de APK aanbieden op een vaste route (`/ratatoskr.apk`)
ZONDER sessie. Een APK-download start vaak buiten de sessie — de
downloadmanager of een doorgestuurde link draagt het sessiecookie niet mee —
dus achter de gate is de link onbruikbaar precies wanneer je 'm nodig hebt. Het
bestand bevat niets geheims: het is een browser-schil met de hostnaam erin. De
netwerklaag is hier de deur.

De ondertekensleutel SHALL als secret bewaard worden (SOPS+age in deze repo),
omdat Android de identiteit van een app aan die sleutel ontleent.

#### Scenario: App start zonder adresbalk

- **WHEN** de app op een toestel start dat de origin kan bereiken
- **THEN** draait de PWA fullscreen, zonder browser-interface

#### Scenario: Asset-links onbereikbaar

- **WHEN** het toestel de origin niet kan bereiken (geen tailnet)
- **THEN** faalt de verificatie zichtbaar en niet stil — en de chat werkt sowieso
  niet zonder verbinding

#### Scenario: Link doorgestuurd naar een toestel

- **WHEN** iemand de download-link opent zonder ingelogde sessie, op een toestel
  dat de origin kan bereiken
- **THEN** krijgt hij de APK, en niet een 401

#### Scenario: Nieuwe versie van de chat

- **WHEN** de chat een nieuwe image-tag krijgt
- **THEN** hoeft de app niet opnieuw gebouwd te worden
