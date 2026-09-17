# Change: bord-backlog

## Why

Het bord toont alleen werk dat al in beweging is: een voorstel, een PR, een
sessie. Wat nog niet begonnen is staat nergens.

Dat was tot nu toe geen gemis, omdat er ook nergens iets stond. Sinds wordsworth
van PoC naar MVP gaat is er wél een backlog: de afspraak is dat een kleine
verandering een issue wordt en iets dat een epic kan worden eerst een spec krijgt.
Van die afspraak is de ene helft zichtbaar (voorstellen staan op het bord) en de
andere helft niet. Een bord dat alleen laat zien wat al loopt, zegt precies dan
niets als je wilt weten wat er nog moet.

## Wat deze change WEL doet

- **Een kolom `backlog`**, vóór *voorstel*: open GitHub-issues van de owner.
- **Het merk in de titel.** `[spec-nodig]` of `[direct]` staat op de kaart, want
  dat verschil bepaalt wat je ermee moet en dat wil je zien zonder door te
  klikken. Een issue zonder zo'n label houdt zijn kale titel — een verzonnen
  indeling is erger dan geen.
- **Gecacht, net als de gemergede PR's.** Issues veranderen langzaam; het bord
  draait elke twee minuten en mag daar geen GitHub-aanroep per keer aan kwijt
  zijn. De cache-helper wordt daarvoor gedeeld: twee concrete gebruikers, en pas
  daarom één functie.

## Wat deze change NIET doet

- **Geen tweede achterstand.** OpenSpec blijft de plek waar een belofte wordt
  vastgelegd; een issue is geen spec en wordt er ook geen. Het bord toont beide
  naast elkaar zodat er één beeld is, niet twee lijsten.
- **Geen gesloten issues.** Die zijn klaar; *gemerged* is al de uitgang.
- **Geen eigen drempellogica.** `stale_days` voor de nieuwe kolom is configuratie
  zoals de andere vier.

## Impact

- `jobs/board.yml` (de kolom), `jobs/board_sources.py` (de bron),
  `jobs/board.py` (de gedeelde cache-helper), `openspec/specs/werk-overzicht`.
