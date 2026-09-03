## ADDED Requirements

### Requirement: Mention naar niet-lid biedt toevoegen aan

Wanneer een bericht een `@agent` bevat die geen lid van het kanaal is, SHALL de app géén kale error tonen maar een keuze "agent toevoegen?"; na toevoegen SHALL het bericht opnieuw verstuurd worden. Een @naam die geen bekende identiteit is SHALL een nette melding geven (geen toevoeg-optie).

#### Scenario: Agent niet in kanaal

- **WHEN** Mark `@ontwerper` typt in een kanaal waar ontwerper geen lid is
- **THEN** verschijnt "@ontwerper zit niet in #kanaal — toevoegen?"; bij toevoegen wordt ontwerper lid en het bericht alsnog geplaatst met ontwerper getriggerd

#### Scenario: Nieuw kanaal krijgt coordinator

- **WHEN** een nieuw kanaal wordt aangemaakt
- **THEN** is coordinator er standaard lid van (best-effort; het kanaal bestaat ook als de add faalt)

#### Scenario: Onbekende naam

- **WHEN** het @woord geen bekende registry-identiteit is
- **THEN** krijgt Mark een melding "geen bekende agent", zonder toevoeg-optie
