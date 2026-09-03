## ADDED Requirements

### Requirement: Per kanaal zichtbaar wie erin zit

De app SHALL per kanaal de werkelijke relay-leden kunnen tonen (naam + rol op het kanaal), geladen uit de echte membership (`buzz channels members`) en met namen uit de identiteitsregistry (`identities.yml`), zodat ook sessies (geen vaste agent-def) met hun naam verschijnen i.p.v. een npub-stomp.

#### Scenario: Sessie zichtbaar in een kanaal

- **WHEN** een sessie als lid aan een kanaal is toegevoegd en Mark "per kanaal" opent
- **THEN** verschijnt die sessie onder dat kanaal met zijn registry-naam en kanaalrol
