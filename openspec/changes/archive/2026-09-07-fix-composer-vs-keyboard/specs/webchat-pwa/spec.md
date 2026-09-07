## ADDED Requirements

### Requirement: De invoerbalk blijft zichtbaar met het toetsenbord open

De app-shell SHALL de hoogte van de visuele viewport volgen, zodat de invoerbalk
zichtbaar blijft wanneer het schermtoetsenbord open staat. Op een browser zonder
`visualViewport` SHALL het bestaande gedrag ongewijzigd blijven.

#### Scenario: Toetsenbord opent

- **WHEN** de gebruiker de invoerbalk aantikt en het schermtoetsenbord opent
- **THEN** krimpt de app-shell mee en blijft de invoerbalk binnen het zichtbare
  gebied, in plaats van eronder te zakken
