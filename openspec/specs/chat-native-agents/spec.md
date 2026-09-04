# chat-native-agents Specification

## Purpose
TBD - created by archiving change add-chat-native-agents. Update Purpose after archive.
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
scope niet. Zo wordt een agent die lid wordt (via de webchat-pop-up, de coordinator-
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

