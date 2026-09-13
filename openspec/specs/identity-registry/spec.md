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
handle, en SHALL de enige bron zijn waartegen een afzender gecontroleerd wordt.

Het bestand hoort bij de **installatie**, niet bij de repo: een verse installatie
SHALL zijn eigen `identities.yml` schrijven met de publieke helft van de
sleutels die daar gegenereerd zijn. Wat in git staat is de registry van Marks
installatie en SHALL geen sleutels bevatten die een andere installatie overneemt
— twee installaties met dezelfde npub zijn voor de relay één identiteit.

#### Scenario: Verse installatie krijgt eigen identiteiten

- **WHEN** `scripts/init_identities.py` draait op een installatie zonder sleutels
- **THEN** ontstaat per identiteit een nieuw sleutelpaar, staat de publieke helft
  in de lokale `identities.yml`, en staat de privéhelft alleen in de
  sleutelopslag

#### Scenario: Nog een keer draaien verandert niets

- **GIVEN** een installatie waar de sleutels al bestaan
- **WHEN** het script opnieuw draait
- **THEN** worden bestaande sleutelparen niet vervangen en verandert
  `identities.yml` niet

#### Scenario: Nieuwe agent-identiteit

- **WHEN** een nieuwe agentrol een identiteit nodig heeft
- **THEN** ontstaat die via een gecommitte registry-wijziging, niet via een
  handmatige actie buiten git om

### Requirement: Privésleutels nooit leesbaar in git

Privésleutels SHALL nooit leesbaar in git staan. Waar ze wél staan SHALL een
keuze van de installatie zijn, niet van de repo: een sleutelopslag met minstens
twee backends, `sops` (SOPS+age-versleuteld in `secrets/`) en `bestand` (een map
op de installatie).

Een bestand-backend SHALL een sleutel weigeren die ruimer dan 0600 leesbaar is,
en SHALL die weigering benoemen in plaats van de sleutel over te slaan. Ontbreekt
een privésleutel, dan SHALL de bijbehorende agent niet starten en SHALL de reden
op stdout staan.

#### Scenario: Marks installatie blijft draaien

- **GIVEN** een installatie met `secrets/identities.yaml` en een age-sleutel
- **WHEN** de listener start met de `sops`-backend
- **THEN** laadt hij dezelfde sleutels als voorheen

#### Scenario: Een sleutel die iedereen kan lezen telt niet

- **GIVEN** de `bestand`-backend en een sleutelbestand met mode 0644
- **WHEN** de listener die sleutel opvraagt
- **THEN** start de agent niet en zegt de melding dat de rechten te ruim zijn

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
