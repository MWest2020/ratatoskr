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
(`agents/sessies.yml`), met daarin ten minste: de werkmap, de toegestane tools,
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

Een sessie SHALL alleen starten wanneer de afzender van het bericht — de agent
die het antwoord schreef, of de mens die het bericht postte — bij het type in
`starters` staat. De identiteit SHALL van de Nostr-afzender komen (registry),
nooit uit de tekst van het bericht.

#### Scenario: Niet-gemachtigde agent noemt de marker

- **WHEN** een agent die niet in `starters` staat `!sessie zettelkast …` schrijft
- **THEN** start er niets en verschijnt er een korte weigering in de thread

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
aantal gelijktijdige sessies, en per starter SHALL er hoogstens één tegelijk
lopen. Een sessie die faalt, leeg terugkomt of afgekapt wordt SHALL dat MET
reden melden in de thread; stilzwijgend niets posten is verboden, omdat een
storing dan als "niets te melden" gelezen wordt.

#### Scenario: Budget op

- **WHEN** een sessie zijn `max_seconden` overschrijdt
- **THEN** wordt de procesgroep gestopt en verschijnt er een melding dat de
  sessie is afgekapt, met wat er tot dan toe gedaan was

#### Scenario: Tweede sessie van dezelfde starter

- **WHEN** een starter een sessie start terwijl zijn vorige nog loopt
- **THEN** start de tweede niet en zegt de listener dat de eerste nog bezig is

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
