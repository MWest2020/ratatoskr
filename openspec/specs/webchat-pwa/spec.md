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

