## ADDED Requirements

### Requirement: Mention naar niet-lid geeft een keuze, geen kale error

Wanneer een bericht een `@naam` bevat die geen lid van het kanaal is, SHALL de app geen kale relay-error tonen maar een keuze bieden: is het een bekende AGENT (chat-agent/meta-agent), dan "toevoegen?" (de agent wordt kanaal-LID en het bericht wordt opnieuw verstuurd); is het geen agent (bv. `@here`, een geplakte handle), dan "toch versturen?" (het bericht gaat met een lid-mention zodat de @-tekst presentation-only blijft). Sessies en mark (rol: mens) worden NIET als toe-te-voegen agent aangeboden. Deze change regelt uitsluitend het VERSTUREN en het LIDMAATSCHAP; of een toegevoegde agent ook daadwerkelijk ANTWOORDT hangt van de listener af (aparte change: listener-membership).

#### Scenario: Agent niet in kanaal

- **WHEN** Mark `@ontwerper` typt in een kanaal waar ontwerper geen lid is
- **THEN** verschijnt "@ontwerper zit niet in #kanaal — toevoegen?"; bij toevoegen wordt ontwerper kanaal-lid en het bericht alsnog geplaatst (of ontwerper vervolgens antwoordt is de listener z'n taak, buiten deze change)

#### Scenario: Geen agent — toch versturen

- **WHEN** het @woord geen bekende agent is (bv. `@here` of een sessie/mark)
- **THEN** krijgt Mark "toch versturen?"; bij bevestigen gaat het bericht met een lid-mention zodat de @-tekst presentation-only blijft, zonder toevoeg-optie
