## ADDED Requirements

### Requirement: Kanalen per functie, niet per agent

Er SHALL een vaste, kleine set kanalen per functie bestaan — `#runs`,
`#escalatie`, `#bouw`, `#review`, `#architectuur`, `#marketing` — en geen
kanalen per individuele agent; samenhangende berichten over één change of run
SHALL als thread onder één wortelbericht hangen.

#### Scenario: Run-verloop als thread

- **WHEN** een habitat-run start en later eindigt
- **THEN** staan start en verdict als replies in dezelfde thread in `#runs`,
  terugvindbaar op change en run-id

#### Scenario: Geen kanaalwildgroei

- **WHEN** een nieuwe agentrol bijkomt
- **THEN** krijgt die een identiteit (registry) en spreekt hij in de bestaande
  functiekanalen; een nieuw kanaal vergt een spec-wijziging

### Requirement: #escalatie is het enige besluitkanaal

Alles wat volgens de habitat-escalatiematrix een menselijk besluit vergt SHALL
(ook) in `#escalatie` landen met een link naar het HTML-run-rapport; `#runs` is
een feed en SHALL nooit de enige plek zijn waar een besluitvraag staat.

#### Scenario: Security-finding

- **WHEN** een security-run een finding meldt
- **THEN** staat er één bericht in `#escalatie` met rapportlink, en neemt
  niemand een besluit tot Mark reageert
