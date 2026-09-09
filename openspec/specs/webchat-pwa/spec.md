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

### Requirement: Schrijven vereist een apparaat-token wanneer de deployment er een zet

De comms-API SHALL een schrijf-token kennen dat per deployment gezet wordt
(`BOOMHUIS_APP_TOKEN`, buiten git). Is er geen token gezet, dan SHALL het gedrag
ongewijzigd zijn en blijft de netwerklaag de enige control. Is er wél een token
gezet, dan SHALL elk statuswijzigend verzoek (bericht sturen, kanaal aanmaken of
verwijderen, een agent aan een kanaal toevoegen, een push-registratie opslaan)
een gelijk token meesturen; ontbreekt het of wijkt
het af, dan SHALL het verzoek geweigerd worden zonder dat de actie plaatsvindt.
De vergelijking SHALL constant-time zijn en het token SHALL nooit in een log,
foutmelding of response verschijnen. Leesverzoeken SHALL ongemoeid blijven.

#### Scenario: Zonder ingesteld token verandert er niets

- **WHEN** de deployment geen schrijf-token zet en een client een bericht stuurt
  zonder token
- **THEN** wordt het bericht verstuurd, precies als voorheen

#### Scenario: Met ingesteld token is een tokenloos schrijfverzoek geweigerd

- **WHEN** de deployment een schrijf-token zet en een client een bericht stuurt
  zonder token of met een afwijkend token
- **THEN** wordt het verzoek geweigerd, verschijnt er geen bericht in het kanaal
  en staat het juiste token nergens in het antwoord

#### Scenario: Lezen blijft open

- **WHEN** de deployment een schrijf-token zet en een client kanalen of berichten
  opvraagt zonder token
- **THEN** krijgt hij die gewoon te zien

### Requirement: De PWA vraagt het token één keer per apparaat

De PWA SHALL het schrijf-token per apparaat lokaal onthouden en het bij elk
schrijfverzoek meesturen. Wordt een schrijfverzoek geweigerd omdat het token
ontbreekt of niet klopt, dan SHALL de PWA de gebruiker om het token vragen en
het verzoek daarna herhalen. De server SHALL het token nooit zelf in de
geserveerde pagina of scripts zetten — een token dat met de pagina meekomt, is
leesbaar voor iedereen die de pagina kan ophalen en beschermt dus niet tegen de
node waartegen het bedoeld is.

#### Scenario: Eerste keer op een nieuw apparaat

- **WHEN** de gebruiker op een apparaat zonder opgeslagen token een bericht
  probeert te sturen terwijl de deployment een token eist
- **THEN** vraagt de app om het token, bewaart het op dit apparaat en verstuurt
  het bericht alsnog, zonder dat de gebruiker het opnieuw hoeft te typen

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

