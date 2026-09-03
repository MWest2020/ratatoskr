## ADDED Requirements

### Requirement: Coordinator is lid van elk kanaal

De coordinator (meta-agent) SHALL kanaal-LID zijn van elk kanaal; een nieuw kanaal SHALL coordinator standaard als lid toegevoegd krijgen bij aanmaken (best-effort — het kanaal bestaat ook als de add faalt). Dit is een lidmaatschaps-beleid: het maakt coordinator overal een lid (zodat een @coordinator-mention niet op "geen lid" faalt). Of coordinator er ook ANTWOORDT hangt van de listener af (aparte change: listener op lidmaatschap i.p.v. alleen def-kanalen).

#### Scenario: Nieuw kanaal krijgt coordinator als lid

- **WHEN** een kanaal via de app wordt aangemaakt
- **THEN** is coordinator er standaard LID van; faalt de add, dan bestaat het kanaal nog steeds en kan coordinator later worden toegevoegd
