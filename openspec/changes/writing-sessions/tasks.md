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
- [ ] 4.1 Live: odin start op Marks verzoek een build-sessie die een PR oplevert
- [ ] 4.2 Change archiveren
