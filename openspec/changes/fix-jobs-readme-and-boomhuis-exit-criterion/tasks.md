## 1. Documentatie kloppend

- [ ] 1.1 `jobs/README.md`, sectie "Nieuwe job toevoegen": `boomhuis-job@` →
      `ratatoskr-job@`, `boomhuis-<x>.timer` → `ratatoskr-<x>.timer`.
- [ ] 1.2 De rest van het bestand nalopen op dezelfde restjes, niet alleen de
      regels die in het gesprek genoemd zijn.

## 2. Exit-criterium

- [ ] 2.1 Bij de `BOOMHUIS_`-terugval in `chat/settings.py` vastleggen wanneer
      hij weg mag: geen enkele live `.env` gebruikt de prefix nog.
- [ ] 2.2 Erbij: wie dat vaststelt en hoe (grep over de `.env` van de VM en van
      agent-lxc), zodat het criterium toetsbaar is en geen wens.

## 3. Groen

- [ ] 3.1 `bash verify.sh` groen.
- [ ] 3.2 Docs-gate groen.
