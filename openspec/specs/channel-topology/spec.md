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

### Requirement: Kanaalbeheer tekent als agent, nooit als de mens

Kanalen maken, verwijderen en leden toevoegen SHALL ondertekend worden met de
orchestrator-identiteit. De mens-sleutel SHALL nergens in de lopende dienst voor
kanaalbeheer gebruikt worden; is er geen orchestrator-sleutel geconfigureerd, dan
SHALL de actie geweigerd worden met een leesbare melding in plaats van terug te
vallen op een andere identiteit.

#### Scenario: Nieuw kanaal is agent-owned

- **WHEN** een gebruiker in de web-chat een kanaal aanmaakt
- **THEN** is de orchestrator de eigenaar van dat kanaal, en kan geautomatiseerd
  kanaalbeheer het daarna zonder mens-sleutel bijwerken

#### Scenario: Geen orchestrator-sleutel geconfigureerd

- **WHEN** kanaalbeheer wordt aangeroepen terwijl er geen orchestrator-sleutel in
  de serveromgeving staat
- **THEN** faalt de actie zichtbaar met de melding dat kanaalbeheer uit staat, en
  wordt er niets met een andere identiteit ondertekend

### Requirement: Bestaande mens-owned kanalen zijn overdraagbaar

Er SHALL een herhaalbaar, idempotent script bestaan dat het eigenaarschap van
mens-owned kanalen overdraagt aan de orchestrator zonder het kanaal opnieuw aan
te maken, met behoud van id, leden en geschiedenis.

#### Scenario: Overdracht van een mens-owned kanaal

- **WHEN** het overdrachtsscript draait op een kanaal waarvan de mens eigenaar is
- **THEN** is de orchestrator daarna eigenaar, geverifieerd tegen de relay, en
  laat een tweede run het kanaal ongemoeid

### Requirement: Hub standaard lid bij nieuw kanaal

Een kanaal dat via de webchat wordt aangemaakt SHALL de **hub-agent** standaard
als lid toegevoegd krijgen (best-effort — het kanaal bestaat ook als de add
faalt; de respons meldt dit via `hub_added`). De hub SHALL op **rol** worden
bepaald (de actieve identiteit met rol `meta-agent`), niet op naam: de hub is
hernoembaar, en een naam-koppeling faalt dan stil. Bestaande kanalen vallen
hierbuiten; die worden operationeel op het beleid gebracht.

Dit is een lidmaatschaps-beleid: de hub ís lid, zodat een mention niet op "geen
lid" faalt. Of de hub ook ANTWOORDT hangt van de listener af.

#### Scenario: Nieuw kanaal krijgt de hub als lid

- **WHEN** een kanaal via de app wordt aangemaakt
- **THEN** wordt de hub-agent standaard als lid toegevoegd en meldt de respons
  `hub_added: true`

#### Scenario: Add faalt maar kanaal blijft bestaan

- **WHEN** het aanmaken lukt maar het toevoegen van de hub faalt (relay-fout, of
  er is geen actieve meta-agent)
- **THEN** bestaat het kanaal nog steeds en meldt de respons `hub_added: false`

#### Scenario: De hub is hernoemd

- **WHEN** de hub-identiteit een andere naam krijgt in de registry
- **THEN** blijft het toevoegen werken zonder codewijziging, omdat de hub op rol
  wordt gevonden

