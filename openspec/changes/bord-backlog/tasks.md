# Tasks

## 1. De bron
- [x] `issue_rows()` haalt de open issues op; `issues_to_cards()` maakt er
      kaarten van. Apart, zodat de rijen gecacht kunnen worden zoals de
      gemergede PR's.
- [x] Merk `[spec-nodig]` of `[direct]` in de titel; geen label = kale titel.
- [x] Een repo uit `ignore_repos` valt hier net zo goed af.

## 2. De cache
- [x] `_cached()` gedeeld door de gemergede PR's en de issues. Twee concrete
      gebruikers, en pas daarom één functie.
- [x] Een leesfout is een fout, geen lege lijst — en een oude lijst wordt
      getoond mét de mededeling dat hij oud is.
- [x] Test die bewijst dat drie draaien binnen de TTL één GitHub-aanroep doen.
      Zonder die test was de extra aanroep per bordronde stil binnengeslopen;
      een bestaande test viel er dan ook terecht over.

## 3. De kolom
- [x] `backlog` vóór `voorstel`, drempel 30 dagen in `board.yml`.

## 4. Nagemeten
- [x] 42 tests groen (`test_board`, `test_board_model`, `test_board_tmux`).
- [x] Het bord echt gedraaid: 54 kaarten, nul fouten, backlog 8 — waaronder twee
      issues in andere repo's die ik niet kende (Billbird #17,
      workstation-security #11). Dat is meteen het nut van de bron.

## Eigen fout onderweg
Mijn testklasse verving vier functies in `board_sources` en zette ze niet terug.
unittest draait klassen op alfabet, dus `Issues` komt vóór `Snapshot` en liet
daar drie PR-tests vallen op een fout die niet van hen was. Nu bewaart `setUp`
alles wat hij vervangt en zet `tearDown` het terug, en hebben de PR-tests een
eigen issue-cache in hun tempmap in plaats van het gedeelde `/tmp`-pad.
