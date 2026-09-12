# werksessies Specification

## Purpose

Een werksessie is een langere, LEZENDE claude-run die vanuit een kanaal start en
daar terugrapporteert. Hij vult het gat tussen een chat-beurt (150s, Read/Grep/
Glob, te klein voor werk) en een habitat-run (de kooi, een branch, een mens-gate
per dispatch, bedoeld voor code). Wat een sessie kán doen staat in git, per type;
wat hij oplevert is tekst en een voorstel — nooit een wijziging.

## Requirements

### Requirement: Een werksessie is een gedeclareerd type, geen vrije opdracht

Elke werksessie SHALL een type zijn dat in de boomhuis-repo gedeclareerd staat
(`agents/sessions.yml`), met daarin ten minste: de werkmap, de toegestane tools,
het model, het tijdbudget, wie het type mag starten en welke identiteit het
resultaat post. Een starter SHALL alleen het TYPE kiezen en een opdracht in
vrije tekst meegeven; hij SHALL nooit de werkmap, de tools, het model of het
budget van een sessie kunnen bepalen.

#### Scenario: Onbekend type

- **WHEN** een bericht `!sessie <onbekend-type> …` bevat
- **THEN** start er niets en meldt de listener in de thread welke types er wél zijn

#### Scenario: Poging tot eigen gereedschap

- **WHEN** de opdrachttekst vraagt om extra tools, een andere map of meer tijd
- **THEN** blijft de sessie draaien binnen wat het type declareert

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

### Requirement: Een werksessie leest, en verandert niets

Een werksessie SHALL uitsluitend lezende tools krijgen, pad-begrensd tot de
werkmap van het type, in een omgeving zonder sleutels of tokens. `Write`,
`Edit`, `Bash` en push-rechten SHALL nooit aan een sessie worden gegeven. Werk
dat een repo verandert SHALL via een OpenSpec-change en een habitat-run lopen;
de poortwachter van `habitat-bridge` SHALL door werksessies niet omzeilbaar zijn.

#### Scenario: Uitkomst wil code worden

- **WHEN** een sessie concludeert dat er iets gewijzigd moet worden
- **THEN** levert hij dat als voorstel in de thread, en verandert hij zelf niets

### Requirement: Een sessie blokkeert de chat niet en is zichtbaar terwijl hij loopt

Het starten van een sessie SHALL de listener niet blokkeren: gewone beurten in
alle kanalen SHALL doorlopen terwijl een sessie draait. De sessie SHALL
tussentijds tonen wat hij doet en SHALL zijn eindresultaat in het startende
kanaal posten, onder de identiteit die het type declareert.

#### Scenario: Chat tijdens een lange sessie

- **WHEN** een sessie van tien minuten draait
- **THEN** blijven mentions in andere kanalen binnen de gebruikelijke tijd beantwoord

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

### Requirement: Zettelkast-type voor gedeelde clips

Er SHALL een type `zettelkast` bestaan dat de vault leest (`sources/`, `wiki/`,
`journal/`) en beoordeelt wat er met nog niet verwerkte clips moet gebeuren:
welke een wiki-capture verdienen, welke elders horen (bijvoorbeeld skill-forge),
en welke niets opleveren. Het type MAG een gedeelde URL ophalen om die vraag te
kunnen beantwoorden. Het SHALL onderscheiden tussen een clip die nog nergens
verwerkt is en een clip waarvan de fetch-snapshot al gecaptured is — die laatste
is afgehandeld, ook al citeert geen enkele wiki-pagina het clipbestand zelf.

#### Scenario: Reeds verwerkte clip

- **WHEN** `scripts/new_sources.py` een clip noemt waarvan de fetch-snapshot al
  in `wiki/log.md` staat
- **THEN** rapporteert de sessie die clip als afgehandeld, niet als achterstand

### Requirement: Een schrijvende sessie werkt in een eigen worktree op een eigen branch

Een sessietype MAY `writes: true` dragen. Zo'n sessie SHALL een verse
git-worktree krijgen van `origin/main` op een nieuwe branch, in een map buiten
elke draaiende checkout, en SHALL daarbinnen mogen schrijven en `git` en tests
mogen draaien.

De worktree SHALL na afloop blijven staan: hij is het bewijs van wat er gebeurd
is, en opruimen is een aparte handeling.

#### Scenario: Sessie raakt een draaiende checkout

- **WHEN** een schrijvende sessie start
- **THEN** staat zijn werkmap buiten de checkouts waaruit de listener en de chat
  draaien

### Requirement: Pushen naar main is onmogelijk gemaakt, niet afgeraden

De worktree van een schrijvende sessie SHALL een `pre-push`-hook dragen die elke
push weigert behalve naar de eigen branch van die sessie. Die hook SHALL door de
starter geschreven worden vóór het proces begint.

Een instructie in de prompt SHALL niet als afdoende gelden: een sessie met `Bash`
leest teksten die niemand heeft gereviewd, en alles wat in zijn context komt kan
zijn instructies sturen.

#### Scenario: Sessie probeert naar main te pushen

- **WHEN** een schrijvende sessie `git push origin main` uitvoert
- **THEN** weigert de hook dat, en de weigering staat in het runbestand

#### Scenario: Sessie pusht zijn eigen branch

- **WHEN** dezelfde sessie zijn eigen branch pusht
- **THEN** lukt dat, en kan hij een pull request openen

### Requirement: Een schrijvende sessie eindigt in een voorstel, niet in een merge

Een schrijvende sessie SHALL eindigen met een pull request en SHALL niet mergen.
De poortwachter van `habitat-bridge` SHALL hierdoor niet omzeilbaar worden: dit
is een weg naar een VOORSTEL, en gekooide runs blijven lopen zoals ze liepen.

#### Scenario: Werk is af

- **WHEN** de sessie klaar is met bouwen en de tests groen zijn
- **THEN** opent hij een pull request en post de link in het startkanaal

### Requirement: Schrijven is een apart recht

`writes: true` SHALL per type gelden, met een eigen `starters`-lijst. Het recht om
een lezend type te starten SHALL geen recht geven om een schrijvend type te
starten.

#### Scenario: Lezende starter probeert te bouwen

- **WHEN** iemand die alleen `zettelkast` mag starten een `build`-sessie start
- **THEN** weigert de listener met de reden dat hij dat type niet mag starten

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
