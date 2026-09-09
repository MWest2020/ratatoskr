## Purpose

Wie is dit, en mag die hier zijn. Boomhuis wordt door derden zelf geïnstalleerd
en heeft dan geen tailnet dat de deur voor hem dichthoudt; deze capability geeft
elke aanroep een persoon en houdt de rest buiten.

## ADDED Requirements

### Requirement: Elke aanroep hoort bij een persoon

Elke aanroep van de comms-API SHALL een geldige sessie hebben — lezen zo goed
als schrijven. Zonder sessie SHALL het antwoord 401 zijn en SHALL er geen
gegevens meekomen.

Lezen was open omdat het tailnet het afschermde. In een installatie zonder
tailnet staat in die leesroutes alles: kanaalnamen, berichten, agent-verkeer en
repo-context. "Lezen is open" betekent daar "alles is openbaar".

De sessie SHALL bepalen wíe de aanroeper is. Welk relay-sleutelpaar bij die
persoon hoort valt buiten deze capability.

#### Scenario: Zonder sessie krijg je niets te zien

- **WHEN** een client kanalen of berichten opvraagt zonder geldige sessie
- **THEN** antwoordt de API met 401 en zonder gegevens

#### Scenario: De sessie bepaalt de schrijver

- **WHEN** een ingelogde persoon een bericht stuurt
- **THEN** gebeurt dat onder de identiteit uit de sessie, niet onder een
  identiteit die de client zelf meestuurt

### Requirement: Geen standaardwachtwoord; de eerste persoon komt via een eenmalige link

Een verse installatie SHALL geen account en geen wachtwoord meebrengen. Zolang
er geen personen zijn SHALL de server bij het starten een eenmalige setup-link
afdrukken; wie die opent maakt het eigenaarsaccount. Na gebruik SHALL die link
niet meer werken.

Bestaat er nog geen persoon maar wel een oud gedeeld schrijf-token, dan SHALL
dat token éénmalig gebruikt kunnen worden om de eigenaar aan te maken — het
migratiepad voor de bestaande installatie — en daarna niet meer.

#### Scenario: Verse installatie

- **WHEN** de server voor het eerst start en er is geen persoon
- **THEN** staat er een eenmalige setup-link in de serveruitvoer
- **AND** maakt wie die opent het eigenaarsaccount

#### Scenario: De link werkt één keer

- **WHEN** de setup-link een tweede keer geopend wordt
- **THEN** wordt hij geweigerd en verandert er niets

### Requirement: Mensen komen erbij via een eenmalige, verlopende uitnodiging

De eigenaar SHALL uitnodigingslinks kunnen maken die één keer werken en
verlopen. Een uitnodiging SHALL ingetrokken kunnen worden zolang hij niet is
gebruikt. Zelf-registratie SHALL niet bestaan: één installatie is één team.

#### Scenario: Uitnodiging gebruikt

- **WHEN** iemand een geldige uitnodiging opent en een wachtwoord kiest
- **THEN** krijgt die persoon een account en is de uitnodiging op

#### Scenario: Verlopen of ingetrokken uitnodiging

- **WHEN** iemand een verlopen of ingetrokken uitnodiging opent
- **THEN** wordt hij geweigerd en ontstaat er geen account

### Requirement: Wachtwoorden staan alleen als hash, met opwaardeerbare parameters

Wachtwoorden SHALL uitsluitend als hash worden bewaard, met een geschikte
sleutelafleiding en een unieke salt per persoon. De gebruikte parameters SHALL
bij de hash worden opgeslagen, zodat ze later verzwaard kunnen worden zonder
iedereen buiten te sluiten: bij een geslaagde login met verouderde parameters
SHALL de hash herberekend worden.

Een wachtwoord SHALL nooit in een log, foutmelding of antwoord verschijnen.

#### Scenario: Zwaardere parameters bij een volgende login

- **GIVEN** een hash die met oudere, lichtere parameters is gemaakt
- **WHEN** die persoon met het juiste wachtwoord inlogt
- **THEN** slaagt de login en wordt de hash met de huidige parameters vervangen

### Requirement: Een tweede factor is optioneel per persoon

Iedere persoon SHALL een tijdgebonden tweede factor (TOTP) kunnen aanzetten en
weer uitzetten. Staat die aan, dan SHALL een login zonder geldige code
mislukken. Een code SHALL niet twee keer bruikbaar zijn binnen zijn geldige
venster.

#### Scenario: Hergebruik van een code

- **WHEN** dezelfde TOTP-code binnen hetzelfde venster een tweede keer wordt
  aangeboden
- **THEN** wordt de login geweigerd

### Requirement: Sessies verlopen en zijn in te trekken

Een sessie SHALL een ondoorzichtig token zijn dat aan de serverkant staat, in
een cookie met `HttpOnly` en `SameSite=Lax`, en met `Secure` behalve op
localhost. Sessies SHALL verlopen, bij gebruik verlengd worden, en per stuk of
allemaal tegelijk ingetrokken kunnen worden.

#### Scenario: Overal uitloggen

- **WHEN** een persoon "overal uitloggen" kiest
- **THEN** werken zijn andere sessies niet meer, ook niet op andere apparaten

#### Scenario: Verlopen sessie

- **WHEN** een sessie zijn vervaltijd voorbij is
- **THEN** wordt hij geweigerd alsof hij niet bestaat

### Requirement: Statuswijzigende verzoeken dragen een sessiegebonden token

Elk verzoek dat iets verandert SHALL een token meedragen dat bij de sessie
hoort; ontbreekt het of klopt het niet, dan SHALL het verzoek geweigerd worden
zonder dat de actie plaatsvindt. `SameSite=Lax` alleen SHALL niet als
bescherming gelden.

#### Scenario: Verzoek zonder token

- **WHEN** een statuswijzigend verzoek zonder geldig sessietoken binnenkomt
- **THEN** wordt het geweigerd en verandert er niets

### Requirement: Inlogpogingen zijn begrensd en verraden niets

Een onbekende gebruiker en een verkeerd wachtwoord SHALL hetzelfde antwoord en
dezelfde vertraging opleveren. Mislukte pogingen SHALL begrensd worden per
account én per bron, met oplopende wachttijd.

Een self-hosted installatie heeft geen WAF voor zich staan; de rem hoort in de
app.

#### Scenario: Geen gebruikersopsomming

- **WHEN** er wordt ingelogd met een niet-bestaande gebruikersnaam en met een
  bestaande gebruikersnaam met fout wachtwoord
- **THEN** zijn beide antwoorden niet van elkaar te onderscheiden

#### Scenario: De rem

- **WHEN** er kort achter elkaar herhaald mislukte pogingen op één account of
  vanaf één bron komen
- **THEN** worden volgende pogingen vertraagd of geweigerd
