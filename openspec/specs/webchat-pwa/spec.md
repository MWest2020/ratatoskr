# webchat-pwa Specification

## Purpose
De webchat als installeerbare PWA op het tailnet: een Slack/Telegram-achtige app
die je op je telefoon zet, met een how-to die de echte toegangswerking beschrijft
(tailnet-only, server-side identiteit `mark`, geen login of sleutel in de browser).
## Requirements
### Requirement: Installeerbare PWA met how-to

De webchat SHALL als installeerbare PWA aangeboden worden (manifest, service
worker en iconen, geserveerd over HTTPS), en er SHALL een how-to zijn die uitlegt
hoe je 'm op een telefoon zet — inclusief de vereiste (telefoon als tailnet-node)
en de installatiestappen per platform (Android/iOS).

#### Scenario: Gebruiker zet de app op zijn telefoon

- **WHEN** een gebruiker met een tailnet-node de how-to volgt
- **THEN** kan hij de webchat-URL openen en via "toevoegen aan beginscherm" als
  losse app installeren, zonder app store

#### Scenario: How-to beschrijft de echte toegangswerking

- **WHEN** de how-to de toegang tot de app beschrijft
- **THEN** vermeldt die dat toegang uitsluitend via het tailnet loopt en dat de
  app namens de server-side identiteit `mark` post (geen login en geen sleutel in
  de browser), zodat de documentatie geen toegangspoort suggereert die er niet is

### Requirement: Ongelezen-teller per kanaal

De PWA SHALL per kanaal tonen hoeveel berichten er nieuw zijn sinds de gebruiker
dat kanaal op dít apparaat het laatst bekeek, en het openen van een kanaal SHALL
het als gelezen markeren. De telling per apparaat SHALL geen serverstate vereisen
(client-side onthouden), zodat er geen gedeelde "gelezen"-status tussen apparaten
ontstaat.

#### Scenario: Nieuw bericht geeft een badge

- **WHEN** er een bericht in een kanaal verschijnt dat de gebruiker sinds
  aankomst nog niet heeft bekeken
- **THEN** toont de kanaallijst een ongelezen-teller bij dat kanaal

#### Scenario: Openen markeert gelezen

- **WHEN** de gebruiker het kanaal opent
- **THEN** verdwijnt de ongelezen-teller voor dat kanaal op dit apparaat

### Requirement: Verse herlaad toont de laatste versie

De geïnstalleerde PWA SHALL bij een herlaad online de nieuwste gedeployde versie
tonen, niet een oudere gecachete versie; de service worker is netwerk-eerst voor
de pagina, met de cache als fallback wanneer het netwerk niet of niet op tijd
(binnen een korte timeout) reageert.

#### Scenario: Herlaad toont de laatste versie

- **WHEN** de gebruiker de geïnstalleerde app herlaadt terwijl hij online is en
  het netwerk op tijd antwoordt
- **THEN** toont de app de nieuwste gedeployde versie, niet een oudere cache

#### Scenario: Traag of geen netwerk valt terug op de cache

- **WHEN** de gebruiker de app opent terwijl het netwerk onbereikbaar is of niet
  binnen de timeout antwoordt (bv. een koude launch vóór de tailnet-tunnel op is)
- **THEN** toont de app snel de laatst gecachete versie in plaats van te hangen of
  te falen, en ververst de cache alsnog zodra het netwerk antwoordt

### Requirement: Repos-browser is een sluitbare modal

De Repos-weergave in de PWA SHALL een modale lade zijn met een altijd-zichtbare
sluitknop die vanaf elk niveau (repo-lijst, PR-lijst, PR-detail) terugkeert naar
de chat, naast de niveau-terug-links binnen de lade.

#### Scenario: Sluiten vanaf elk niveau

- **WHEN** de gebruiker de Repos-lade opent en naar een repo of PR navigeert
- **THEN** kan hij met de sluitknop in één tik terug naar de chat, ongeacht het
  niveau waarop hij zich bevindt

### Requirement: Kanaal-beschrijving zichtbaar in de app

De PWA SHALL per kanaal een beschrijving tonen (uit het relay-kanaal), zodat de
gebruiker ziet waar een kanaal voor is zonder het te openen.

#### Scenario: Beschrijving in de kanaallijst

- **WHEN** de gebruiker de kanaallade opent
- **THEN** toont elk kanaal met een ingestelde beschrijving die beschrijving als
  subtitel onder de naam

### Requirement: Telefoon-notificaties via Web Push

De geïnstalleerde PWA SHALL de gebruiker kunnen abonneren op Web Push, zodat
meldingen (bv. een review-verdict) ook binnenkomen als de app gesloten is. De
VAPID-private-sleutel SHALL niet op de web-facing backend staan; het versturen
gebeurt buiten de stdlib-backend.

#### Scenario: Aanmelden en een melding ontvangen

- **WHEN** de gebruiker meldingen aanzet (permissie geeft) en er wordt een push
  verstuurd
- **THEN** toont het apparaat een notificatie, ook als de app-tab/app gesloten is,
  en opent een tik erop de app

### Requirement: Per kanaal zichtbaar wie erin zit

De app SHALL per kanaal de werkelijke relay-leden kunnen tonen (naam + rol op het kanaal), geladen uit de echte membership (`buzz channels members`) en met namen uit de identiteitsregistry (`identities.yml`), zodat ook sessies (geen vaste agent-def) met hun naam verschijnen i.p.v. een npub-stomp.

#### Scenario: Sessie zichtbaar in een kanaal

- **WHEN** een sessie als lid aan een kanaal is toegevoegd en Mark "per kanaal" opent
- **THEN** verschijnt die sessie onder dat kanaal met zijn registry-naam en kanaalrol

