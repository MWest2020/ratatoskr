## ADDED Requirements

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
