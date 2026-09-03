## ADDED Requirements

### Requirement: Mention naar niet-lid geeft een keuze, geen kale error

Wanneer een bericht een `@naam` bevat die geen lid van het kanaal is, SHALL de app geen kale error tonen maar een keuze bieden op basis van wat de naam is: is het een bekende AGENT (chat-agent/meta-agent), dan "toevoegen?" (na toevoegen wordt het bericht opnieuw verstuurd); is het geen agent (bv. `@here`, een geplakte handle), dan "toch versturen?" (het bericht gaat dan met de @-tekst als presentation-only). Sessies en mark (rol: mens) worden NIET als toe-te-voegen agent aangeboden.

#### Scenario: Agent niet in kanaal

- **WHEN** Mark `@ontwerper` typt in een kanaal waar ontwerper geen lid is
- **THEN** verschijnt "@ontwerper zit niet in #kanaal — toevoegen?"; bij toevoegen wordt ontwerper lid en het bericht alsnog geplaatst met ontwerper getriggerd

#### Scenario: Geen agent — toch versturen

- **WHEN** het @woord geen bekende agent is (bv. `@here` of een sessie/mark)
- **THEN** krijgt Mark "toch versturen?"; bij bevestigen gaat het bericht met een lid-mention zodat de @-tekst presentation-only blijft, zonder toevoeg-optie
