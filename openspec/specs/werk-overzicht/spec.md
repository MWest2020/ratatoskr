# werk-overzicht Specification

## Purpose

Eén bord dat de vraag "wat beweegt er, en wat zit vast?" beantwoordt, met
ouderdom als signaal. Het is een spiegel van git en de relay, geen bron: werk
verplaatst doordat een PR gemerged of een change gearchiveerd wordt. De
gegevens komen van één producent buiten de chat, zodat de chat-container
dependency-loos blijft.

## Requirements

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

### Requirement: Het bord is een spiegel, geen bron

Het bord SHALL geen werk kunnen verplaatsen: er is geen slepen, geen statusknop,
geen bewerken. Git en de relay blijven de waarheid; een kaart verandert doordat
een PR gemerged wordt of een change gearchiveerd, nooit doordat iemand het bord
aanraakt.

#### Scenario: Poging tot verplaatsen

- **WHEN** een gebruiker een kaart probeert te verslepen
- **THEN** gebeurt er niets, en de app legt uit waar de status vandaan komt

### Requirement: Eén producent buiten de chat, één momentopname

De gegevens SHALL door één terugkerende taak verzameld worden op de host waar de
clones en de sessies zijn, en als één bestand in de datalaag van de chat landen.
De chat SHALL dat bestand alleen serveren, achter de sessie, en zelf geen clones,
`gh` of GitHub-toegang nodig hebben.

Ontbreekt het bestand of is het oud, dan SHALL de app dat zeggen — met het
tijdstip van de laatste momentopname. Een leeg bord is niet te onderscheiden van
een kapotte producent, en dat onderscheid is precies wat je nodig hebt.

#### Scenario: Producent draait niet

- **WHEN** de laatste momentopname ouder is dan de verversingsperiode
- **THEN** toont de app hoe oud hij is en dat er iets misgaat, niet "geen werk"

#### Scenario: Nog nooit gedraaid

- **WHEN** er geen momentopname bestaat
- **THEN** antwoordt de route met een nette 404 en zegt de app wat er moet
  gebeuren

### Requirement: De graaf is een tweede weergave van dezelfde kaarten

Een latere grafische weergave SHALL dezelfde kaarten en dezelfde momentopname
gebruiken. Er SHALL geen tweede verzameling of tweede producent voor komen.

#### Scenario: Graaf erbij

- **WHEN** de graafweergave gebouwd wordt
- **THEN** leest die `board.json` en verandert er niets aan de producent
