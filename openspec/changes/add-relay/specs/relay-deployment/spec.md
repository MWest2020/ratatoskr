## ADDED Requirements

### Requirement: Zelf-gehoste relay in closed mode

De relay SHALL zelf-gehost draaien via de upstream compose-bundle (relay,
Postgres, Redis, MinIO, optioneel Caddy) met `RELAY_OWNER_PUBKEY` gezet, zodat
alleen identiteiten uit de registry kunnen deelnemen.

#### Scenario: Vreemde sleutel geweigerd

- **WHEN** een keypair dat niet in `identities.yml` staat zich bij de relay
  meldt
- **THEN** weigert de relay de deelname en verschijnt er niets in de kanalen

#### Scenario: Herstart zonder identiteitsverlies

- **WHEN** de relay-stack herstart of opnieuw wordt uitgerold
- **THEN** blijven `BUZZ_RELAY_PRIVATE_KEY` en de overige secrets stabiel en
  hoeven clients en agents niets opnieuw te configureren

### Requirement: Gepind image

`BUZZ_IMAGE` SHALL een concrete commit-SHA of semver-tag zijn, nooit `:main` of
`:latest`; een upgrade is een bewuste pin-wijziging in git.

#### Scenario: Upgrade is een diff

- **WHEN** de relay naar een nieuwe upstream-versie gaat
- **THEN** is dat zichtbaar als één gecommitte pin-wijziging, herleidbaar tot
  wie/wanneer/waarom

### Requirement: Secrets alleen via SOPS+age

Relay-privésleutel, HMAC-secret en db/S3-credentials SHALL uitsluitend
SOPS+age-versleuteld in de repo staan en pas bij deploy ontsleuteld worden; een
kloon van de repo bevat geen bruikbaar secret.

#### Scenario: Kloon zonder buit

- **WHEN** iemand de repo kloont zonder de age-key
- **THEN** is geen enkel secret bruikbaar en start de stack niet namens ons

### Requirement: Herstelbaar, met expliciet toegestaan verlies

Er SHALL een beschreven en één keer geoefende backup/restore zijn waarbij
relay-identiteit en sleutels altijd overleven; berichthistorie is best-effort
omdat git de gezaghebbende bron blijft.

#### Scenario: Restore op schone host

- **WHEN** de stack op een schone host wordt teruggezet uit backup
- **THEN** werken bestaande clients en agent-configuraties zonder nieuwe
  sleutels, ook als een deel van de berichthistorie ontbreekt
