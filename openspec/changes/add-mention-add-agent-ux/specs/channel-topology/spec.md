## ADDED Requirements

### Requirement: Coordinator is lid van elk kanaal

De coordinator (meta-agent) SHALL lid zijn van elk kanaal; een nieuw kanaal SHALL coordinator standaard toegevoegd krijgen bij aanmaken (best-effort — het kanaal bestaat ook als de add faalt). Zo is coordinator overal aanspreekbaar zonder handmatig toevoegen.

#### Scenario: Nieuw kanaal krijgt coordinator

- **WHEN** een kanaal via de app wordt aangemaakt
- **THEN** is coordinator er standaard lid van; faalt de add, dan bestaat het kanaal nog steeds en kan coordinator later worden toegevoegd
