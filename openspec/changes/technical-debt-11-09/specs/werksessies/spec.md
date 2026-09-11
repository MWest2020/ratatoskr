# werksessies

## MODIFIED Requirements

### Requirement: Alleen een gemachtigde starter zet een sessie in gang

Een sessie SHALL alleen starten wanneer zowel de **starter** als de
**aanleiding** bij het type in `starters` staan. De starter is de afzender van
het bericht met de marker: de agent die het antwoord schreef, of de mens die het
bericht postte. De aanleiding is de afzender van het bericht dat de beurt in gang
zette; typt een mens de marker zelf, dan zijn starter en aanleiding dezelfde.
Beide identiteiten SHALL van de Nostr-afzender komen (registry), nooit uit de
tekst van een bericht. `starters` is de volledige lijst: er SHALL geen extra eis
aan de rol van de aanleiding gesteld worden.

#### Scenario: Niet-gemachtigde agent noemt de marker

- **WHEN** een agent die niet in `starters` staat `!sessie zettelkast …` schrijft
- **THEN** start er niets en verschijnt er een korte weigering in de thread

#### Scenario: Gemachtigde agent, namens iemand die niet mag

- **GIVEN** odin staat bij het type in `starters` en de schrijver van het
  aansturende bericht niet
- **WHEN** odin in het antwoord op dat bericht `!sessie zettelkast …` schrijft
- **THEN** start er niets en noemt de weigering dat de aanleiding niet op
  `starters` staat

#### Scenario: Automatisering als aanleiding

- **WHEN** een identiteit die geen mens is maar wél op `starters` staat, zoals
  `orchestrator`, de marker postt of een agent ertoe aanzet
- **THEN** start de sessie, en de startpost noemt die identiteit als aanleiding —
  de herleiding stopt daar, en niet bij een persoon

### Requirement: Begrensd bestaan, en een stille sessie bestaat niet

Elk type SHALL een tijdbudget hebben; bij overschrijding SHALL de sessie
(inclusief kindprocessen) gestopt worden. Er SHALL een bovengrens staan op het
aantal gelijktijdige sessies, en per aanleiding SHALL er hoogstens één tegelijk
lopen — ongeacht via welke starter. Een sessie die faalt, leeg terugkomt of
afgekapt wordt SHALL dat MET reden melden in de thread; stilzwijgend niets posten
is verboden, omdat een storing dan als "niets te melden" gelezen wordt.

#### Scenario: Budget op

- **WHEN** een sessie zijn `max_seconden` overschrijdt
- **THEN** wordt de procesgroep gestopt en verschijnt er een melding dat de
  sessie is afgekapt, met wat er tot dan toe gedaan was

#### Scenario: Tweede sessie van dezelfde starter

- **WHEN** een sessie gestart wordt, door een mens zelf of door een agent,
  terwijl een eerdere sessie met diezelfde aanleiding nog loopt
- **THEN** start de tweede niet en zegt de listener dat de eerste nog bezig is

#### Scenario: Twee mensen via dezelfde agent

- **WHEN** twee verschillende gemachtigde mensen odin elk om een sessie vragen en
  `max_gelijktijdig` laat ruimte
- **THEN** starten beide sessies

## ADDED Requirements

### Requirement: Een sessie legt vast namens wie hij draait

Elke sessie SHALL starter én aanleiding vastleggen: in de naam van het
runbestand (`{type}-{aanleiding}-{tijd}.jsonl`), in een eerste regel van dat
runbestand met starter, aanleiding, het id van het aansturende bericht en het
kanaal, en in de startpost in het kanaal. Een runbestand of startpost die alleen
de agent noemt en niet de aanleiding, SHALL niet voorkomen.

#### Scenario: Odin start op verzoek van Mark

- **WHEN** Mark odin om een sessie vraagt en odin die start
- **THEN** heet het runbestand `zettelkast-mark-<tijd>.jsonl`
- **AND** noemt de eerste regel starter `odin`, aanleiding `mark` en het id van
  Marks bericht
- **AND** zegt de startpost dat odin de sessie startte namens `mark`

#### Scenario: De meta-regel verstoort de oogst niet

- **WHEN** de listener het runbestand per tick leest
- **THEN** wordt de eerste regel overgeslagen en verschijnen voortgang en
  resultaat zoals voorheen
