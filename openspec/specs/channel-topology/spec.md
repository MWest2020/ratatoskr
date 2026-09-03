# channel-topology Specification

## Purpose
TBD - created by archiving change add-notifications. Update Purpose after archive.
## Requirements
### Requirement: Kanalen per functie, niet per agent

Er SHALL een vaste, kleine set kanalen per functie bestaan — `#runs`,
`#escalatie`, `#bouw`, `#review`, `#architectuur`, `#marketing`, `#standup` — en
geen kanalen per individuele agent; samenhangende berichten over één change of run
SHALL als thread onder één wortelbericht hangen. `#standup` draagt de recurring
standup/gedaan-digests en SHALL #escalatie/#review-inhoud alleen *spiegelen*
(lezend samenvatten); besluiten vallen nooit in #standup — `#escalatie` blijft het
enige besluitkanaal.

#### Scenario: Geen kanaalwildgroei

- **WHEN** een nieuwe agentrol bijkomt
- **THEN** krijgt die een identiteit (registry) en spreekt hij in de bestaande
  functiekanalen; een nieuw kanaal vergt een spec-wijziging

#### Scenario: Run-verloop als thread

- **WHEN** een habitat-run start en later eindigt
- **THEN** staan start en verdict als replies in dezelfde thread in `#runs`,
  terugvindbaar op change en run-id

#### Scenario: #standup spiegelt, beslist niet

- **WHEN** de standup een openstaand #escalatie-besluit toont
- **THEN** staat dat als samenvatting in #standup, maar wordt het besluit zelf nog
  steeds in #escalatie genomen, niet in #standup

### Requirement: #escalatie is het enige besluitkanaal

Alles wat volgens de habitat-escalatiematrix een menselijk besluit vergt SHALL
(ook) in `#escalatie` landen met een link naar het HTML-run-rapport; `#runs` is
een feed en SHALL nooit de enige plek zijn waar een besluitvraag staat.

#### Scenario: Security-finding

- **WHEN** een security-run een finding meldt
- **THEN** staat er één bericht in `#escalatie` met rapportlink, en neemt
  niemand een besluit tot Mark reageert

### Requirement: Kanalen dragen een reproduceerbare beschrijving

Elk vast kanaal SHALL een native relay-beschrijving hebben die overeenkomt met zijn
`doel` in `channels.yml`, gezet via een reproduceerbaar script
(`orchestrator/set-channel-descriptions.py`) i.p.v. een eenmalige handmatige stap.

#### Scenario: Beschrijving reproduceerbaar (her)zetten

- **WHEN** een `doel` in channels.yml wijzigt of de relay is hersteld
- **THEN** zet het script de beschrijving opnieuw op elk kanaal (als eigenaar),
  zodat de beschrijving die de app toont overeenkomt met channels.yml

