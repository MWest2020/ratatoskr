# Taken

## 1. De worktree
- [x] 1.1 `agents/work_tree.py`: verse worktree van `origin/main` op een eigen
      branch, buiten elke draaiende checkout
- [x] 1.2 `pre-push`-hook die alleen de eigen branch doorlaat, geschreven vóór
      het proces start
- [x] 1.3 Tests: hook weigert main, laat de eigen branch door, worktree ligt
      buiten de draaiende checkouts

## 2. Het sessietype
- [x] 2.1 `sessies.yml`: type `build` met `writes: true`, eigen starters, ruimer
      tijdbudget
- [x] 2.2 `sessies.py`: bij `writes` een worktree als werkmap en de ruimere
      toolset; zonder `writes` verandert er niets
- [x] 2.3 Tests: een lezend type krijgt nooit schrijftools

## 3. De uitkomst
- [x] 3.1 PR-link uit de uitvoer halen en in het kanaal posten
- [x] 3.2 `docs/how-to/werksessies.md` bijwerken

## 4. Bewijs
- [x] 4.1 Live bewezen, drie keer. Mark startte `!sessie build` in #bouw en dat
      leverde PR #102 op (test_topology.py gesplitst langs module-onder-test, mét
      de vondst dat drie testklassen ná de `__main__`-regel stonden en dus nooit
      liepen). Daarna PR #105 (de laatste Nederlandse teksten) en PR #106 (de
      baseline leeg: vijf bestanden gesplitst, nieuwe CSS netjes in statics.py,
      sw-SHELL, FRESH_ASSETS en een cache-bump — de val die hier twee keer eerder
      is ingelopen).
- [x] 4.2 Change archiveren
