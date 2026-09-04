## ADDED Requirements

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

## MODIFIED Requirements

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
