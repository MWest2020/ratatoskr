# identity-registry Specification

## Purpose

Wie er namens wie tekent op de relay, en hoe dat controleerbaar blijft.

Een bericht op een Nostr-relay is precies zo veel waard als de sleutel die het
tekende. Deze capability legt vast dat een identiteit exact één sleutelpaar
heeft, dat de publieke helft in git staat als enige bron, en dat de privéhelft
daar nooit leesbaar komt. Daar hangt de toerekenbaarheid van elke sessie aan:
zonder dit weet je dat er iets gezegd is, maar niet door wie.
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

### Requirement: Eén hub-agent in het mens-kanaal

Het hub-kanaal `#general` SHALL precies één agent-identiteit als deelnemer
hebben: de hub. Andere agents SHALL hun eigen kanalen hebben, en
sessie-identiteiten SHALL niet in het hub-kanaal posten; het post-pad SHALL dat
weigeren in plaats van erop te vertrouwen.

#### Scenario: Sessie probeert in het hub-kanaal te posten

- **WHEN** een identiteit met rol `sessie` een bericht naar `#general` stuurt
- **THEN** wordt het geweigerd met een melding die het projectkanaal of
  `#escalatie` als plaats aanwijst, en wordt er niets gepost

#### Scenario: De hub post wel

- **WHEN** de hub-agent in `#general` antwoordt
- **THEN** gaat dat ongehinderd door

### Requirement: Een hernoemde identiteit houdt haar sleutelpaar

Het hernoemen van een identiteit SHALL de handle wijzigen in de registry én in de
sleutelbundel, met behoud van hetzelfde sleutelpaar, zodat eerdere berichten
toewijsbaar blijven. Een identiteit die haar rol verliest SHALL op `ingetrokken`
blijven staan in plaats van verwijderd te worden.

#### Scenario: Ingetrokken identiteit

- **WHEN** een sleutel is ingetrokken
- **THEN** weigert het post-pad die identiteit, terwijl haar eerdere berichten
  nog steeds onder haar naam leesbaar zijn

