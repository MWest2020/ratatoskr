# repo-conventies Specification

## Purpose

De regels over hoe deze repo eruitziet, en het bewijs dat ze ook echt gelden.

Eén regel met tanden is meer waard dan tien in een CONTRIBUTING.md, dus staat
hier alleen wat een script kan controleren: bestanden blijven binnen 200 regels,
en een baseline voor wat al te lang was mag alleen korter worden. Dat tweede is
de belangrijkste helft — een baseline zonder vervaldatum is een uitzondering die
zichzelf vermenigvuldigt.

## Requirements

### Requirement: Bronbestanden blijven binnen 200 regels, gecontroleerd in CI

Elk bronbestand dat we zelf schrijven — `*.py`, `*.js`, `*.sh`, `*.css`,
`*.html` en `Dockerfile`, tests inbegrepen — SHALL hoogstens 200 regels hebben.
Markdown, `LICENSE`, binaire bestanden, YAML/JSON-data en vendored configuratie
SHALL buiten die grens vallen, met de reden per categorie in de check zelf. De
check SHALL op elke PR en elke push naar `main` in CI draaien, samen met de
unittests uit `verify.sh`, en SHALL lokaal met dezelfde opdracht te draaien zijn.

#### Scenario: Een bestand groeit over de grens

- **WHEN** een PR een bronbestand boven de 200 regels brengt
- **THEN** is de check rood en noemt hij het bestand en het aantal regels

#### Scenario: Buiten de scope telt niet

- **WHEN** een spec, een design of het vendored compose-bestand boven de 200
  regels komt
- **THEN** blijft de check groen

#### Scenario: Lokaal hetzelfde oordeel

- **WHEN** iemand `bash verify.sh` draait op dezelfde commit als CI
- **THEN** geeft de check hetzelfde oordeel

### Requirement: Een baseline is tijdelijk

Een bestand dat bij het aanzetten van de check al boven de grens zat, MAG op een
baseline staan met zijn aantal regels van dat moment. Zo'n bestand SHALL niet
groeien, en SHALL van de baseline af zodra het binnen de grens valt. Een
baseline SHALL alleen bestaan zolang de change die hem invoerde niet
gearchiveerd is.

#### Scenario: Baseline-bestand groeit

- **WHEN** een PR een regel toevoegt aan een bestand op de baseline
- **THEN** is de check rood

#### Scenario: Gesplitst maar niet afgevoerd

- **WHEN** een bestand op de baseline onder de 201 regels komt en nog op de
  baseline staat
- **THEN** is de check rood tot het van de baseline af is, zodat de baseline
  niet stil blijft staan

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
