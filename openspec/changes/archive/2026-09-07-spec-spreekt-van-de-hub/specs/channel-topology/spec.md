## REMOVED Requirements

### Requirement: Coordinator standaard lid bij nieuw kanaal

**Reden:** de requirement koppelde het beleid aan één agent bij NAAM. Die
koppeling brak toen de hub `coordinator` → `odin` werd; vervangen door een
requirement die de hub op rol bepaalt.

## ADDED Requirements

### Requirement: Hub standaard lid bij nieuw kanaal

Een kanaal dat via de webchat wordt aangemaakt SHALL de **hub-agent** standaard
als lid toegevoegd krijgen (best-effort — het kanaal bestaat ook als de add
faalt; de respons meldt dit via `hub_added`). De hub SHALL op **rol** worden
bepaald (de actieve identiteit met rol `meta-agent`), niet op naam: de hub is
hernoembaar, en een naam-koppeling faalt dan stil. Bestaande kanalen vallen
hierbuiten; die worden operationeel op het beleid gebracht.

Dit is een lidmaatschaps-beleid: de hub ís lid, zodat een mention niet op "geen
lid" faalt. Of de hub ook ANTWOORDT hangt van de listener af.

#### Scenario: Nieuw kanaal krijgt de hub als lid

- **WHEN** een kanaal via de app wordt aangemaakt
- **THEN** wordt de hub-agent standaard als lid toegevoegd en meldt de respons
  `hub_added: true`

#### Scenario: Add faalt maar kanaal blijft bestaan

- **WHEN** het aanmaken lukt maar het toevoegen van de hub faalt (relay-fout, of
  er is geen actieve meta-agent)
- **THEN** bestaat het kanaal nog steeds en meldt de respons `hub_added: false`

#### Scenario: De hub is hernoemd

- **WHEN** de hub-identiteit een andere naam krijgt in de registry
- **THEN** blijft het toevoegen werken zonder codewijziging, omdat de hub op rol
  wordt gevonden
