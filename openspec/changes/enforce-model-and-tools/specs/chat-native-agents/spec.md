## ADDED Requirements

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
