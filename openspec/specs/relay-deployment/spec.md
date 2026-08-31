# relay-deployment Specification

## Purpose
TBD - created by archiving change add-relay. Update Purpose after archive.
## Requirements
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

### Requirement: Uitsluitend bereikbaar via het tailnet

De relay SHALL uitsluitend via het Tailscale-net bereikbaar zijn: geen
poort-forward, geen publieke DNS, geen binding aan een publiek interface;
verder openzetten vergt een eigen OpenSpec-change.

#### Scenario: Van buiten het tailnet

- **WHEN** een client buiten het tailnet de relay probeert te bereiken
- **THEN** komt er geen verbinding tot stand, nog vóór enige buzz-authenticatie

### Requirement: Gepind image

`BUZZ_IMAGE` SHALL een concrete commit-SHA of semver-tag zijn, nooit `:main` of
`:latest`; een upgrade is een bewuste pin-wijziging in git.

#### Scenario: Upgrade is een diff

- **WHEN** de relay naar een nieuwe upstream-versie gaat
- **THEN** is dat zichtbaar als één gecommitte pin-wijziging, herleidbaar tot
  wie/wanneer/waarom

### Requirement: Geen secret ooit leesbaar in git

Secrets SHALL nooit leesbaar in enige repo staan: infra-secrets
(relay-privésleutel, HMAC-secret, db/S3-credentials) leven als `.env` (0600)
alleen op de host conform het homelab-patroon met een gecommitte
`env.example`; identiteits-privésleutels (Nostr) staan uitsluitend
SOPS+age-versleuteld in de boomhuis-repo.

#### Scenario: Kloon zonder buit

- **WHEN** iemand de boomhuis- of homelab-repo kloont zonder host-toegang en
  zonder de age-key
- **THEN** is geen enkel secret bruikbaar en start de stack niet namens ons

#### Scenario: Herbouw van de host

- **WHEN** de VM opnieuw wordt uitgerold
- **THEN** seedt het playbook `.env` vanaf `env.example` en vult Mark (of een
  gedocumenteerd generatie-stap) de echte waarden; de relay-identiteit komt uit
  backup, nooit vers

### Requirement: Herstelbaar, met expliciet toegestaan verlies

Er SHALL een beschreven en één keer geoefende backup/restore zijn waarbij
relay-identiteit en sleutels altijd overleven; berichthistorie is best-effort
omdat git de gezaghebbende bron blijft.

#### Scenario: Restore op schone host

- **WHEN** de stack op een schone host wordt teruggezet uit backup
- **THEN** werken bestaande clients en agent-configuraties zonder nieuwe
  sleutels, ook als een deel van de berichthistorie ontbreekt

