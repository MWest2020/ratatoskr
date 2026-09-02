# identity-registry Specification

## Purpose
TBD - created by archiving change add-relay. Update Purpose after archive.
## Requirements
### Requirement: Eén keypair per identiteit

Elke deelnemer — mens of agent — SHALL een eigen Nostr-keypair hebben dat nooit
gedeeld of hergebruikt wordt; elk bericht is daarmee herleidbaar tot precies één
identiteit.

#### Scenario: Herleidbaar bericht

- **WHEN** een bericht in een kanaal verschijnt
- **THEN** is via de signatuur eenduidig vast te stellen welke identiteit (rol)
  het schreef

### Requirement: Publieke registry in git als enige bron

`identities.yml` SHALL alle toegelaten publieke sleutels bevatten met rol en
status (`actief`/`ingetrokken`), en toelating tot de relay SHALL herleidbaar
zijn tot een registry-entry; er bestaat geen tweede lijst.

#### Scenario: Nieuwe agent-identiteit

- **WHEN** een nieuwe agentrol een identiteit nodig heeft
- **THEN** ontstaat die via een gecommitte registry-wijziging, niet via een
  handmatige actie buiten git om

### Requirement: Privésleutels nooit leesbaar in git

Privésleutels SHALL uitsluitend SOPS+age-versleuteld in `secrets/` staan;
intrekking betekent status `ingetrokken` in de registry én blokkade aan de
relay-kant.

#### Scenario: Intrekking

- **WHEN** een identiteit wordt ingetrokken
- **THEN** weigert de relay die sleutel en toont de registry wie, wanneer en
  waarom is ingetrokken

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

#### Scenario: Geen impersonatie van de mens of ingetrokken sleutels

- **WHEN** de ping-helper wordt aangeroepen met een `IDENT` die de mens-identiteit
  (rol `mens`) of een niet-actieve identiteit aanwijst
- **THEN** weigert de helper te posten (geen bericht ondertekend met die sleutel),
  zodat niemand zich als de mens of onder een ingetrokken identiteit kan voordoen

