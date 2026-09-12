# werksessies

## ADDED Requirements

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
