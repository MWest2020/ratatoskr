## ADDED Requirements

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
