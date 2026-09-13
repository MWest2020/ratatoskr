# identity-registry

## MODIFIED Requirements

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
