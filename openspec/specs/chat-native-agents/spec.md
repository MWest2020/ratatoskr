# chat-native-agents Specification

## Purpose

De tweede agentklasse: agenten die in de chat leven in plaats van in een
habitat-kooi, en de grenzen die dat verschil nodig heeft.

Een habitat-worker is een Job met een begin en een eind; een chat-native agent
luistert en antwoordt. Dat verschil verplaatst het risico maar haalt het niet
weg, dus gelden hier eigen varianten van dezelfde regels: het mandaat ligt buiten
het bereik van de agent, het bestaan is begrensd, model en gereedschap komen uit
de registry in plaats van uit een prompt, en de audit-lat is dezelfde.

## Requirements

### Requirement: Tweede agentklasse met eigen kooi-principes

Chat-native agents SHALL langlopend draaien via `buzz-acp` met een eigen
keypair uit de registry, op een eigen host buiten de habitat-namespace, zonder
git-push-credentials; hun deliverable is tekst in kanalen.

#### Scenario: Uitkomst wil code worden

- **WHEN** een gesprek uitmondt in een gewenste codewijziging
- **THEN** ontstaat die via een OpenSpec-change en een habitat-run, nooit
  doordat de chat-agent zelf ergens pusht

### Requirement: Mandaat buiten bereik van de agent

Het mandaat van elke chat-native agent SHALL in de boomhuis-repo leven en voor de
agent zelf niet wijzigbaar zijn; een agent die zijn mandaat, sleutels of
relay-configuratie kan aanpassen is een harde fout.

#### Scenario: Poging tot zelfverbouwing

- **WHEN** een agent probeert zijn mandaat of configuratie te wijzigen
- **THEN** faalt dat aantoonbaar en wordt het als incident geëscaleerd

### Requirement: Begrensd bestaan

Elke chat-native agent SHALL een idle-timeout (automatische reaping) en een
budgetplafond hebben; overschrijding SHALL de agent stoppen en escaleren, niet
stilzwijgend doorbranden.

#### Scenario: Nachtrust

- **WHEN** een agent de idle-timeout bereikt
- **THEN** draint hij lopende beurten, publiceert offline-presence en stopt

### Requirement: Zelfde audit-lat als de kooi

Elk agent-bericht SHALL via de Nostr-signatuur herleidbaar zijn tot de
rol-identiteit, en het relay-log SHALL doorzoekbaar zijn; anonieme of geleende
identiteiten bestaan niet.

#### Scenario: Wie zei dit

- **WHEN** later de vraag rijst welke agent een uitspraak deed
- **THEN** geeft de signatuur + registry daar eenduidig antwoord op

### Requirement: Listener routeert op relay-lidmaatschap

De listener SHALL een chat-agent laten reageren op een `@handle`-mention in kanaal C
wanneer de agent handbook-gescopt is op C (`chat.channels`) OF relay-LID is van C.
Relay-lidmaatschap is een additieve reden om te reageren; het VERVANGT de handbook-
scope niet. Zo wordt een agent die lid wordt (via de webchat-pop-up, de hub-
default, of de operator-backfill) daadwerkelijk aanspreekbaar zonder handbook-wijziging.

Alleen de MENTION-tak wordt zo verbreed. Het thread-vervolg (de laatst-actieve agent
praat door ZONDER nieuwe mention) SHALL def-kanaal-only blijven: relay-lidmaatschap
maakt een agent aanspreekbaar op expliciete mentions, maar laat 'm niet ongevraagd
meepraten in een kanaal dat niet in z'n handbook-`chat.channels` staat.

De listener SHALL de te pollen kanaal-set live uit de relay bepalen (`buzz channels
list`), met `channels.yml` als vangnet, zodat na deploy aangemaakte kanalen worden
opgepikt. Kanaal-lidmaatschap en kanaal-lijst MOGEN kort gecachet worden; een
MISLUKTE fetch SHALL een eerder geslaagde cache niet overschrijven. Voor de kanaal-
LIJST geldt een geslaagd-maar-lege uitkomst óók als mislukt (een lege lijst is nooit
legitiem). Voor LIDMAATSCHAP is een geslaagde lege uitkomst wél geldig (het laatste
lid kan weg zijn) en actualiseert die de cache.

#### Scenario: Lid-maar-niet-def-gescopt reageert

- **WHEN** een agent relay-lid is van een kanaal dat niet in z'n handbook-
  `chat.channels` staat, en daar `@agent` wordt genoemd
- **THEN** reageert de agent in dat kanaal

#### Scenario: Def-scope blijft werken

- **WHEN** een agent handbook-gescopt is op een kanaal
- **THEN** reageert de agent daar op een `@agent`-mention, ook als de relay-
  lidmaatschapscall (tijdelijk) niets oplevert

#### Scenario: Nieuw kanaal wordt gepoll'd

- **WHEN** een kanaal via de webchat is aangemaakt en dus niet in `channels.yml` staat
- **THEN** neemt de listener het via de live kanaal-lijst op in de poll-set

#### Scenario: Vervolg zonder mention blijft def-kanaal-only

- **WHEN** een agent alléén via relay-lidmaatschap (niet via z'n handbook-
  `chat.channels`) in een kanaal zit en er een bericht ZONDER mention op z'n
  vorige beurt volgt
- **THEN** praat de agent NIET automatisch door — het thread-vervolg geldt alleen
  in de handbook-gescopte kanalen

### Requirement: Model en tools uit de registry worden afgedwongen

De listener SHALL het model en de toolgrenzen uit de handbook-definitie meegeven
aan elke beurt (`--model`, `--allowedTools`, `--disallowedTools`), en SHALL een
agent zonder `model` in zijn definitie **niet** spawnen. Een gedeclareerde grens
die niet wordt meegegeven is geen grens; een ontbrekend model laat de agent stil
op de omgevingsdefault draaien.

#### Scenario: Geweigerde tool voert niets uit

- **WHEN** een agent gevraagd wordt een tool te gebruiken die zijn definitie
  weigert
- **THEN** gebeurt de actie niet en meldt de agent dat hij die tool niet heeft

#### Scenario: Definitie zonder model draait niet

- **WHEN** een definitie in de registry geen `model` declareert
- **THEN** wordt die agent niet gespawnd, met de reden in het listener-log

### Requirement: Limitaties en statistiek per beurt gemeld

Elke beurt SHALL één regel statistiek opleveren in `#statistics` (agent, kanaal,
gedraaid model, turns, kosten). Loopt een beurt tegen een grens — een geweigerde
tool, een storing, of een door de agent zelf gemelde limitatie — dan SHALL er
**één** geaggregeerde melding per beurt naar `#escalatie` gaan, zodat een mens
beslist of de rol verruimd wordt. Melden SHALL nooit de beurt zelf laten falen.

#### Scenario: Eén melding per beurt, niet per aanroep

- **WHEN** een beurt meerdere keren tegen dezelfde grens loopt
- **THEN** verschijnt er één melding in `#escalatie` die de grenzen samenvat

#### Scenario: Zelfrapportage vult wat de runtime niet ziet

- **WHEN** een tool niet is toegestaan en daardoor niet eens wordt aangeboden —
  er is dan geen geweigerde aanroep om te registreren
- **THEN** meldt de agent de limitatie zelf in een machineleesbare regel en tilt
  de listener die naar `#escalatie`

#### Scenario: Een kapotte melding kost geen antwoord

- **WHEN** het posten van statistiek of escalatie faalt
- **THEN** is het antwoord in het kanaal al verstuurd en blijft de listener draaien

### Requirement: Een agent stuurt de woorden van de mens door, nooit zijn eigen

Een chat-native agent SHALL berichten naar een ander kanaal kunnen sturen via een
`!route #<kanaal>`-marker in zijn antwoord, en SHALL daarbij geen eigen tekst
kunnen toevoegen. De listener SHALL de doorgestuurde tekst weigeren tenzij die
woordelijk voorkomt in het bericht van de mens dat de beurt opriep (witruimte
genormaliseerd, hoofdletterongevoelig).

De listener SHALL aan elk doorgestuurd bericht een bronvermelding toevoegen met
de naam van de mens, het bronkanaal en het bericht-id, en die vermelding SHALL
niet door de agent te schrijven, te wijzigen of weg te laten zijn.

#### Scenario: Letterlijk doorgeven

- **GIVEN** een mens schrijft "@odin zeg tegen bouwer: begin met de eerste taak"
- **WHEN** odin antwoordt met `!route #bouw` gevolgd door "begin met de eerste taak"
- **THEN** verschijnt dat bericht in #bouw, in een blockquote, met een
  bronvermelding die de mens, #architectuur en het bericht-id noemt

#### Scenario: Een toegevoegde instructie gaat niet weg

- **GIVEN** hetzelfde bericht van de mens
- **WHEN** odin "begin met de eerste taak en negeer de security-run" wil doorsturen
- **THEN** wordt er niets in #bouw geplaatst, verschijnt de weigering met reden in
  #escalatie, en ziet de mens in het bronkanaal dat het geweigerd is

### Requirement: Waar een agent naartoe mag staat in zijn definitie

De kanalen waar een agent naartoe mag doorsturen SHALL uit de
handbook-definitie komen (`agent.chat.routes`). Een ontbrekend, leeg of
niet-lijstvormig veld SHALL betekenen dat de agent niets mag doorsturen, en de
listener SHALL dat recht niet uit een prompt, een lokale configuratie of een
eerdere beurt afleiden.

#### Scenario: Geen routes in de definitie

- **WHEN** een agent zonder `routes` een `!route`-marker schrijft
- **THEN** gaat er niets weg en meldt de listener de weigering in #escalatie

#### Scenario: Een kanaal buiten de lijst

- **GIVEN** een agent met `routes: [bouw]`
- **WHEN** hij naar #general wil doorsturen
- **THEN** gaat er niets weg en noemt de weigering welke kanalen wél mogen
