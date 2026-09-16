## ADDED Requirements

### Requirement: Documentatie beweegt mee met code

Een wijziging die code raakt SHALL in dezelfde wijziging iets onder `docs/`
bijwerken, en dat SHALL afgedwongen worden op **elk pad waarlangs code
binnenkomt** — niet alleen op pull requests, maar ook op een push die
rechtstreeks naar `main` gaat.

Wat als code telt SHALL op één plek staan, waar elke handhaver hem uit leest.
Wat als documentatie telt SHALL gelijk zijn aan wat de hub-checker telt; een
lokale handhaver die zijn eigen definitie hanteert is geen tweede handhaving maar
een tweede afspraak.

Op 2026-09-15 heette de README van deze repo nog "Boomhuis", noemde zes
chat-agents terwijl er acht draaiden, en verwees naar systemd-units die al
maanden anders heetten. De gate die dat had moeten vangen bestond al in de hub;
deze repo had hem nooit aangezet.

#### Scenario: Code zonder documentatie wordt geweigerd

- **WHEN** een push naar `main` een pad onder `code_paths` wijzigt zonder dat er
  iets onder `docs/` meebeweegt
- **THEN** de pre-push-guard weigert de push, met de reden en het ontsnappingsluik

#### Scenario: Een pull request wordt op dezelfde regel gemeten

- **WHEN** een pull request diezelfde wijziging bevat
- **THEN** de docs-gate in CI faalt op dezelfde grond

#### Scenario: Beide handhavers tellen hetzelfde als documentatie

- **WHEN** een wijziging alleen `README.md` bijwerkt naast code
- **THEN** beide handhavers weigeren hem, want alleen `docs/` telt

### Requirement: Units bestaan beide kanten op

De unit-controle SHALL twee richtingen dekken: elke unit in de repo staat
geïnstalleerd en is niet afgedreven, **én** elke geïnstalleerde unit die van ons
is heeft een tegenhanger in de repo.

Een unit die alleen op de host bestaat SHALL een melding geven. Een uitzondering
daarop SHALL een reden en een herkomst-repo dragen; een lijst met alleen namen
is geen uitzondering maar een blinde vlek.

De omgekeerde richting ontbrak tot 2026-09-16. Daardoor mat de gate precies de
verzameling waar het gat niet in zat: `claude-secret-refresh.{service,timer}`
draaide maandenlang buiten git en viel niemand op.

#### Scenario: Een unit die nergens in git staat wordt gemeld

- **WHEN** een `ratatoskr-*`-unit geïnstalleerd staat zonder bestand in de repo
- **THEN** de controle meldt hem en eindigt niet-nul

#### Scenario: Een uitzondering zonder reden is zelf een fout

- **WHEN** een unit in de uitzonderingslijst staat zonder reden
- **THEN** de controle beschouwt dat als een fout in de lijst

### Requirement: Een timer die faalt, faalt niet stil

Voor elke timer die wij beheren SHALL gecontroleerd worden of zijn laatste run
slaagde. Een systemd-timer blijft `active (waiting)` en plant de volgende run
ongeacht de afloop van de vorige, dus de toestand van de timer SHALL nooit als
bewijs gelden dat het werk gebeurt.

Een toestand die niet vast te stellen is SHALL als fout tellen, niet als
"waarschijnlijk goed": niet kunnen vaststellen is geen bewijs.

Op 2026-09-16 bleek `claude-secret-refresh.service` 82 keer in veertien dagen te
zijn omgevallen en nul keer geslaagd, terwijl de timer al die tijd groen oogde.

#### Scenario: Een service die niet-nul eindigde wordt gemeld

- **WHEN** de service achter een van onze timers als laatste met een niet-nul
  exitcode eindigde
- **THEN** `verify.sh` is rood en noemt de service

#### Scenario: Timers die niet van ons zijn tellen niet mee

- **WHEN** een systemd-eigen timer op de machine faalt
- **THEN** de controle zwijgt erover, want ruis maakt een gate onbruikbaar
