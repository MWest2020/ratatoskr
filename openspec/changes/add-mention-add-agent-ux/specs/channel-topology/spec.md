## ADDED Requirements

### Requirement: Coordinator standaard lid bij nieuw kanaal

Een kanaal dat via de webchat wordt aangemaakt SHALL de coordinator (meta-agent) standaard als lid toegevoegd krijgen bij het aanmaken (best-effort — het kanaal bestaat ook als de add faalt; de respons meldt dit via `coordinator_added`). Bestaande kanalen vallen buiten deze change: die worden eenmalig via de operator-backfill (`orchestrator/add-member.py --all-channels`) op het beleid gebracht, want de webchat maakt of muteert lidmaatschap van bestaande kanalen niet vanzelf.

Dit is een lidmaatschaps-beleid (coordinator ís lid, zodat een @coordinator-mention niet op "geen lid" faalt). Of coordinator er ook ANTWOORDT hangt van de listener af (aparte change: listener op lidmaatschap i.p.v. alleen def-kanalen).

#### Scenario: Nieuw kanaal krijgt coordinator als lid

- **WHEN** een kanaal via de app wordt aangemaakt
- **THEN** wordt coordinator standaard als lid toegevoegd

#### Scenario: Add faalt maar kanaal blijft bestaan

- **WHEN** het aanmaken lukt maar het toevoegen van coordinator faalt (relay-fout)
- **THEN** bestaat het kanaal nog steeds en meldt de respons `coordinator_added: false`
