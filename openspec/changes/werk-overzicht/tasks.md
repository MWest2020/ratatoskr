# Taken

Nieuwe code is Engels (ADR-0001); commentaar en docs blijven Nederlands.

## 1. De producent
- [x] 1.1 `jobs/board.py`: verzamelt PR's (gh), OpenSpec-changes (clones),
      lopende werksessies en #escalatie-signalen tot één lijst kaarten
- [x] 1.2 Kolom- en ouderdomslogica puur en getest (geen I/O in die functies)
- [x] 1.3 Drempels per kolom in `jobs/board.yml`, niet in de code
- [x] 1.4 Schrijft `board.json` atomisch in het datavolume van de chat
- [x] 1.5 Timer (`jobs/systemd/ratatoskr-board.timer`), elke 10 minuten

## 2. Serveren
- [x] 2.1 `chat/board.py` + route `/api/board`, achter de sessie
- [x] 2.2 Ontbrekend bestand → 404 met uitleg; oude momentopname → meegegeven
      tijdstip, geen stilte
- [x] 2.3 Tests: route achter de sessie, 404-pad, oud-pad

## 3. In de app
- [x] 3.1 `chat/app-board.js` + CSS: vier kolommen, kaarten, ouderdom zichtbaar
- [x] 3.2 Knop in de kop, naast Repos en Agents; sw-cache bumpen
- [x] 3.3 Niets is versleepbaar; de app legt uit waar de status vandaan komt
- [x] 3.4 `rook.js` uitbreiden: bord opent en toont kaarten

## 4. Vastleggen
- [x] 4.1 `docs/how-to/werk-overzicht.md`
- [ ] 4.2 Change archiveren

## Later (niet in deze change)
- Graafweergave over dezelfde `board.json`
- Habitat-jobs als kaarten (vergt `kubectl` in de producent)
