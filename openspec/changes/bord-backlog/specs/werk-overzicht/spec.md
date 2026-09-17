## MODIFIED Requirements

### Requirement: Het bord toont wat beweegt en wat vastzit

De app SHALL een bord tonen met de kolommen *backlog*, *voorstel*, *bouwen*,
*review* en *gemerged*. Elke kaart SHALL ten minste de repo, een titel, de kolom,
hoe lang hij in die kolom staat en een verwijzing naar de bron (PR-URL, issue-URL
of het pad van de OpenSpec-change) dragen.

*Backlog* is werk dat nog niet begonnen is: een open issue. Zonder die kolom
toont het bord alleen wat al loopt, en zegt het dus niets op het moment dat je
wilt weten wat er nog moet.

Het bord SHALL markeren welke kaarten langer in hun kolom staan dan de drempel
voor die kolom, en die drempels SHALL configuratie zijn, geen code. Ouderdom is
het signaal: dat kaart X al drie dagen op review wacht is de informatie, niet dat
er twaalf kaarten open staan.

#### Scenario: Iets staat te lang stil

- **WHEN** een kaart langer dan de drempel van zijn kolom op dezelfde plek staat
- **THEN** toont het bord dat zichtbaar, apart van de kaarten die doorstromen

#### Scenario: Niets loopt vast

- **WHEN** geen enkele kaart over zijn drempel is
- **THEN** toont het bord dat als zodanig, en niet als een lege pagina

#### Scenario: Een issue draagt zijn indeling

- **WHEN** een open issue het label `spec-nodig` of `direct` heeft
- **THEN** staat dat merk in de titel op de kaart, en een issue zonder zo'n label
  houdt zijn kale titel
