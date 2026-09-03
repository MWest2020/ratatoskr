## MODIFIED Requirements

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
