# relay-deployment Specification

## Purpose

Hoe een boomhuis uitgerold en blootgesteld wordt: één compose-bestand met
gepinde images, staat in named volumes, en poorten die standaard alleen op
loopback luisteren. De beheerder kiest bewust wat verder open gaat (reverse
proxy met TLS, VPN/tailnet, of het LAN); de netwerklaag is sinds
`inloggen-per-persoon` de buitenste van twee controls, niet de enige.

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

### Requirement: De standaard is niet bereikbaar, blootstelling is een keuze

Een verse installatie SHALL niets buiten de machine publiceren: elke
gepubliceerde poort SHALL een expliciet bind-adres hebben, met loopback als
standaard. Een beheerder die het verder open wil zetten SHALL dat expliciet
doen, en de documentatie SHALL de vormen benoemen die wij ondersteunen —
reverse proxy met TLS, een VPN of tailnet, of bewust het lokale netwerk — met
wat je bij de laatste opgeeft.

De installatie SHALL geen TLS termineren; dat is werk voor de proxy die de
beheerder al heeft. De app SHALL wel correct werken achter zo'n proxy: de rem
op inlogpogingen leest `X-Forwarded-For`, en het sessiecookie krijgt `Secure`
zodra de verbinding niet lokaal is.

#### Scenario: Verse installatie is van buiten niets

- **WHEN** een installatie is opgezet zonder dat de beheerder iets aan
  blootstelling wijzigt
- **THEN** is er vanaf een andere machine geen enkele poort te bereiken

#### Scenario: Blootstellen is één regel, geen verbouwing

- **WHEN** de beheerder de installatie achter zijn reverse proxy wil hangen
- **THEN** volstaat het aanpassen van de bind-adressen in zijn env-bestand
- **AND** hoeft hij niets in de stack zelf te wijzigen

### Requirement: De app wordt uitgerold als gepind image, niet als kopie

De chat SHALL draaien uit een image dat uit deze repo gebouwd is, met een
concrete versietag — nooit `latest`, net als de relay. De installatie SHALL
bestaan uit een compose-bestand en een env-bestand, en SHALL geen bestanden
kennen die met de hand op de machine gezet moeten worden.

Een installatie SHALL kunnen zeggen welke versie er draait.

#### Scenario: Installeren zonder voorkennis

- **GIVEN** een schone machine met docker
- **WHEN** iemand het compose-bestand en een ingevuld env-bestand neerzet en de
  stack start
- **THEN** draait er een boomhuis, en is de enige resterende stap het aanmaken
  van de eigenaar

#### Scenario: Een upgrade is een diff

- **WHEN** een installatie naar een nieuwe versie gaat
- **THEN** is dat één gewijzigde tag in het env- of compose-bestand

### Requirement: Staat overleeft een herinstallatie

Accounts, sessies en push-registraties SHALL in een volume staan dat losstaat
van de container, zodat opnieuw uitrollen of upgraden geen accounts kost.

#### Scenario: Container weg, accounts blijven

- **WHEN** de chat-container verwijderd en opnieuw gestart wordt
- **THEN** bestaan de accounts nog en blijven bestaande sessies geldig
