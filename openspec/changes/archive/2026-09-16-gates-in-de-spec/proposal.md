# Change: gates-in-de-spec

## Why

Deze week zijn er drie gates bijgekomen, en alle drie bestaan alleen als code:

- documentatie beweegt mee met code (`docs-gates` + `scripts/docs_drift.py`);
- units bestaan beide kanten op (`scripts/check_units.py`);
- timers die stil falen worden gezien (`scripts/check_timers.py`).

Alle drie zijn gebouwd nadat er iets misging, en alle drie hebben een test. Wat
ze niet hebben is een plek waar staat *waarom ze er zijn en wat ze moeten
garanderen*.

Dat is precies de fout die ze moesten afsluiten. Bij wordsworth stond de
postbus-regel in code, in commentaar en in tests, en draaide hij op het echte pad
nergens — dat kostte 214 onleesbaar gemaakte contactadressen. Een regel die
alleen in code staat, is een regel die je bij de eerstvolgende herschrijving
kwijtraakt zonder het te merken.

`track-host-units-in-git` is gearchiveerd met de waarschuwing "no deltas found".
Terecht: er is een gedragsafspraak veranderd zonder dat de spec dat zag.

## What Changes

Drie eisen in `repo-conventies`, elk met het gemeten voorval erbij, zodat
duidelijk is waartegen ze beschermen en niemand ze voor ceremonie aanziet.

## Wat hier NIET in zit

Nieuwe gates. Dit legt vast wat er al draait en getest is.

## Impact

Alleen `openspec/specs/repo-conventies`. Geen code, geen gedragsverandering.
