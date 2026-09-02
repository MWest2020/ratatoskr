## ADDED Requirements

### Requirement: Sessie-identiteiten voor toerekenbare afzender

Elke vaste Claude-sessie die in de relay post SHALL een eigen sleutelpaar hebben
(rol `sessie` in de registry), zodat elk bericht toerekenbaar is aan de echte
afzender en het audit-spoor de juiste identiteit toont — niet een gedeelde
identiteit met een naam-prefix. Een sessie-identiteit krijgt GEEN handbook-def en
staat NIET in de listener-run-lijst (een sessie is geen gespawnde chat-agent).

#### Scenario: Sessie post onder eigen sleutel

- **WHEN** een sessie een bericht in #general plaatst via de ping-helper met haar
  eigen `IDENT`
- **THEN** is het bericht in de relay ondertekend met het sleutelpaar van die
  sessie, en toont het audit-spoor die identiteit
