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
en de installatiestappen per platform (Android/iOS). De how-to SHALL de
toegangswerking beschrijven zoals die is: tailnet-only, server-side identiteit
`mark`, en — wanneer de deployment een schrijf-token zet — een token dat de
gebruiker één keer per apparaat invoert om te mogen schrijven.

#### Scenario: Gebruiker zet de app op zijn telefoon

- **WHEN** een gebruiker met een tailnet-node de how-to volgt
- **THEN** kan hij de webchat-URL openen en via "toevoegen aan beginscherm" als
  losse app installeren, zonder app store

#### Scenario: How-to beschrijft de echte toegangswerking

- **WHEN** de how-to de toegang tot de app beschrijft
- **THEN** vermeldt die dat toegang uitsluitend via het tailnet loopt, dat de app
  namens de server-side identiteit `mark` post, en of er een schrijf-token nodig
  is — zodat de documentatie geen toegangspoort suggereert die er niet is, en
  geen openheid suggereert die er niet meer is

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

### Requirement: Mention naar niet-lid geeft een keuze, geen kale error

Wanneer een bericht een `@naam` bevat die geen lid van het kanaal is, SHALL de app geen kale relay-error tonen maar een keuze bieden: is het een bekende AGENT (chat-agent/meta-agent), dan "toevoegen?" (de agent wordt kanaal-LID en het bericht wordt opnieuw verstuurd); is het geen agent (bv. `@here`, een geplakte handle), dan "toch versturen?" (het bericht gaat met een lid-mention zodat de @-tekst presentation-only blijft). Sessies en mark (rol: mens) worden NIET als toe-te-voegen agent aangeboden. Deze change regelt uitsluitend het VERSTUREN en het LIDMAATSCHAP; of een toegevoegde agent ook daadwerkelijk ANTWOORDT hangt van de listener af (aparte change: listener-membership).

#### Scenario: Agent niet in kanaal

- **WHEN** Mark `@ontwerper` typt in een kanaal waar ontwerper geen lid is
- **THEN** verschijnt "@ontwerper zit niet in #kanaal — toevoegen?"; bij toevoegen wordt ontwerper kanaal-lid en het bericht **normaal** opnieuw verstuurd — `@ontwerper` blijft dus een échte mention (niet geforceerd tot platte tekst), zodat de relay 'm naar het verse lid resolvet. Of ontwerper vervolgens antwoordt is de listener z'n taak (aparte change: listener-membership). Ziet de relay het verse lidmaatschap heel even nog niet (race), dan biedt de app "nu toch als tekst versturen?" i.p.v. te blijven proberen.

#### Scenario: Geen agent — toch versturen

- **WHEN** het @woord geen bekende agent is (bv. `@here` of een sessie/mark)
- **THEN** krijgt Mark "toch versturen?"; bij bevestigen gaat het bericht met een lid-mention zodat de @-tekst presentation-only blijft, zonder toevoeg-optie

### Requirement: De hele kanaalrij is het klikdoel

Een rij in de kanaallade SHALL over haar volledige oppervlak het kanaal openen
en de lade sluiten — niet alleen op de tekst. Alleen de verwijderknop in die rij
SHALL een eigen actie houden.

#### Scenario: Tik naast de kanaalnaam

- **WHEN** de gebruiker in de kanaallade tikt op de lege ruimte rechts van een
  kanaalnaam
- **THEN** wisselt de app naar dat kanaal en sluit de lade, zodat de invoerbalk
  weer bereikbaar is

### Requirement: De invoerbalk blijft zichtbaar met het toetsenbord open

De app-shell SHALL de hoogte van de visuele viewport volgen, zodat de invoerbalk
zichtbaar blijft wanneer het schermtoetsenbord open staat. Op een browser zonder
`visualViewport` SHALL het bestaande gedrag ongewijzigd blijven.

#### Scenario: Toetsenbord opent

- **WHEN** de gebruiker de invoerbalk aantikt en het schermtoetsenbord opent
- **THEN** krimpt de app-shell mee en blijft de invoerbalk binnen het zichtbare
  gebied, in plaats van eronder te zakken

### Requirement: De app herstelt zelf zodra het netwerk terug is

De webchat SHALL blijven proberen zijn gegevens te laden wanneer de eerste
poging faalt, en SHALL zich herstellen zonder handmatige herlaad zodra het
netwerk antwoordt. Een mislukte eerste laadpoging SHALL de poll-timer en de
luisteraars van de app niet verhinderen; die worden gezet vóór de eerste
netwerkaanroep.

Zolang er geen verbinding is SHALL de app dat tonen in plaats van een
laad-indicator te laten staan — een scherm dat "laden…" blijft zeggen is niet
te onderscheiden van een kapotte app.

#### Scenario: Koude start vóór de tunnel op is

- **WHEN** de app start terwijl de API onbereikbaar is (de service worker
  serveert de gecachete shell) en het netwerk daarna alsnog beschikbaar komt
- **THEN** laadt de app zijn kanalen en berichten alsnog, zonder herlaad

#### Scenario: Geen verbinding is zichtbaar

- **WHEN** de app zijn gegevens niet kan laden
- **THEN** meldt hij dat er geen verbinding is en dat het opnieuw geprobeerd
  wordt, in plaats van een laad-indicator te laten staan

### Requirement: De app is uit een vastgelopen staat te krijgen zonder herinstallatie

De webchat SHALL de gebruiker een handeling bieden die elke service
worker afmeldt, elke cache wist en de app opnieuw laadt. Die handeling
SHALL bereikbaar zijn juist wanneer de app zijn gegevens niet kan laden —
dat is het moment waarop hij nodig is.

De app SHALL zichzelf niet ongevraagd wissen: een storing van enkele
seconden mag geen lokale staat kosten. Het is een knop, geen automatisme.

De service worker SHALL geregistreerd worden zodat zijn script niet uit
de HTTP-cache komt, zodat een nieuwe versie bij de eerstvolgende start
wordt opgemerkt.

#### Scenario: Vastgelopen app komt los

- **GIVEN** een geïnstalleerde app die op een oude, gecachete versie
  hangt
- **WHEN** de gebruiker *app verversen* kiest
- **THEN** worden service workers afgemeld en caches gewist, en laadt de
  app opnieuw als de versie die de server nu serveert

### Requirement: Een verbindingsfout noemt het adres en de oorzaak

Wanneer de app zijn gegevens niet kan laden SHALL hij tonen welk adres
hij probeerde en welke fout terugkwam. Een melding die alleen "geen
verbinding" zegt, maakt geen verschil zichtbaar tussen een tunnel die nog
niet op is en een app die naar een adres wijst dat niet meer bestaat.

#### Scenario: De melding is bruikbaar

- **WHEN** de app zijn gegevens niet kan laden
- **THEN** noemt de melding het adres waar hij het probeerde
- **AND** de fout die daarbij terugkwam

### Requirement: Zonder verbinding toont de app wat hij het laatst wist

Kan de app zijn berichten niet ophalen, dan SHALL hij de laatst opgehaalde
berichten van dat kanaal tonen in plaats van een leeg scherm, mét het
tijdstip waarop die zijn opgehaald. De weergave SHALL onmiskenbaar als
gedateerd te herkennen zijn: zonder dat tijdstip is oude tekst niet van
verse te onderscheiden, en dat is erger dan niets tonen.

Zodra er verse berichten binnenkomen SHALL de datering verdwijnen en de
momentopname vervangen worden. Verzenden SHALL zonder verbinding blijven
falen met een leesbare melding; de app SHALL geen berichten in de wacht
zetten om later te versturen.

De service worker SHALL `/api/`-antwoorden ongemoeid laten: de
momentopname is van de app, die weet wanneer hij hem ophaalde.

#### Scenario: Melding leidt naar een app zonder tailnet

- **GIVEN** een toestel dat een push-melding krijgt (die loopt over het
  publieke internet) maar de comms-API niet kan bereiken
- **WHEN** de gebruiker de app opent
- **THEN** toont de app de laatst bekende berichten van dat kanaal, met
  het tijdstip waarop ze zijn opgehaald

#### Scenario: Verse berichten verdringen de momentopname

- **WHEN** de verbinding terugkomt en er berichten worden opgehaald
- **THEN** verdwijnt de datering en toont de app de verse berichten

#### Scenario: Verzenden wordt niet uitgesteld

- **WHEN** de gebruiker zonder verbinding een bericht probeert te sturen
- **THEN** meldt de app dat het niet gelukt is
- **AND** zet het bericht niet in een wachtrij voor later

### Requirement: De app stuurt je naar inloggen wanneer de sessie ontbreekt

Krijgt de app een 401, dan SHALL hij naar de inlogpagina gaan en na een
geslaagde login terugkeren naar waar de gebruiker was — hetzelfde kanaal, niet
de voorpagina.

Een 401 SHALL onderscheiden worden van een netwerkfout: het eerste betekent
"jij mag hier niet (meer)", het tweede "ik kan er niet bij". Ze verdienen een
ander antwoord op het scherm.

#### Scenario: Verlopen sessie tijdens gebruik

- **GIVEN** een geopende app waarvan de sessie is verlopen
- **WHEN** de app zijn berichten ophaalt
- **THEN** gaat hij naar de inlogpagina
- **AND** staat de gebruiker na het inloggen weer in hetzelfde kanaal

#### Scenario: Netwerkfout is geen uitlog

- **WHEN** de app zijn berichten niet kan ophalen omdat er geen verbinding is
- **THEN** blijft hij ingelogd en toont hij de verbindingsmelding, niet de
  inlogpagina

### Requirement: Een 401 wist de lokaal bewaarde berichten

Blijkt de sessie ongeldig, dan SHALL de app zijn lokale momentopnamen wissen.
Zonder dat leest de volgende persoon op hetzelfde apparaat de berichten van de
vorige — de momentopname is er voor "geen verbinding", niet voor "geen
toegang".

Een netwerkfout SHALL de momentopnamen juist laten staan.

#### Scenario: Uitgelogd op een gedeeld apparaat

- **GIVEN** een apparaat met bewaarde berichten van een vorige gebruiker
- **WHEN** de app een 401 krijgt
- **THEN** zijn die berichten weg voordat de inlogpagina verschijnt

### Requirement: Instellingen heten RATATOSKR_, en de oude naam blijft werken

Elke instelling die de chat uit de omgeving leest SHALL primair onder
`RATATOSKR_<naam>` gelezen worden, en SHALL terugvallen op `BOOMHUIS_<naam>`
wanneer de eerste ontbreekt. Het lezen SHALL via één gedeelde functie lopen, zodat
er geen leesplek kan achterblijven bij een volgende hernoeming.

De terugval SHALL niet stilzwijgend verdwijnen zolang er installaties bestaan die
de oude naam gebruiken: hij is de enige weg terug na een mislukte uitrol.

#### Scenario: Nieuwe installatie

- **WHEN** alleen `RATATOSKR_URL` gezet is
- **THEN** gebruikt de app die waarde

#### Scenario: Draaiende installatie tijdens de hernoeming

- **WHEN** een nieuw image start tegen een `.env` die nog `BOOMHUIS_URL` heeft
- **THEN** werkt de installatie ongewijzigd door

#### Scenario: Beide gezet

- **WHEN** zowel `RATATOSKR_URL` als `BOOMHUIS_URL` gezet zijn
- **THEN** wint `RATATOSKR_URL`

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
