## ADDED Requirements

### Requirement: Zonder verbinding toont de app wat hij het laatst wist

Kan de app zijn berichten niet ophalen, dan SHALL hij de laatst opgehaalde
berichten van dat kanaal tonen in plaats van een leeg scherm, mét het
tijdstip waarop die zijn opgehaald. De weergave SHALL onmiskenbaar als
gedateerd te herkennen zijn: zonder dat tijdstip is oude tekst niet van
verse te onderscheiden, en dat is erger dan niets tonen.

Zodra er verse berichten binnenkomen SHALL de datering verdwijnen en de
momentopname vervangen worden. Verzenden SHALL zonder verbinding blijven
falen met een leesbare melding; de app SHALL geen berichten in de wacht
zetten om later te versturen.

De service worker SHALL `/api/`-antwoorden ongemoeid laten: de
momentopname is van de app, die weet wanneer hij hem ophaalde.

#### Scenario: Melding leidt naar een app zonder tailnet

- **GIVEN** een toestel dat een push-melding krijgt (die loopt over het
  publieke internet) maar de comms-API niet kan bereiken
- **WHEN** de gebruiker de app opent
- **THEN** toont de app de laatst bekende berichten van dat kanaal, met
  het tijdstip waarop ze zijn opgehaald

#### Scenario: Verse berichten verdringen de momentopname

- **WHEN** de verbinding terugkomt en er berichten worden opgehaald
- **THEN** verdwijnt de datering en toont de app de verse berichten

#### Scenario: Verzenden wordt niet uitgesteld

- **WHEN** de gebruiker zonder verbinding een bericht probeert te sturen
- **THEN** meldt de app dat het niet gelukt is
- **AND** zet het bericht niet in een wachtrij voor later
