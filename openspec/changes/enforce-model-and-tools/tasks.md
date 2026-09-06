## 1. Afdwingen

- [x] 1.1 `providers.run` geeft model + allow/deny mee, JSON-output.
- [x] 1.2 Prompt via stdin (variadische tool-vlaggen slokken een positioneel argument op).
- [x] 1.3 `bootstrap.build_agents` leest model/tools/skills; geen model = niet spawnen.
- [x] 1.4 Live bewezen: Write geweigerd → bestand niet aangemaakt, agent meldt het.

## 2. Melden

- [x] 2.1 `reporting.report_run`: statistiekregel per beurt naar `#statistics`.
- [x] 2.2 Eén geaggregeerde melding naar `#escalatie` bij denial, storing of
      zelfgemelde limitatie.
- [x] 2.3 `LIMITATIE:`-conventie in `prompts.LIMIT_CLAUSE`, live bewezen met haiku.
- [x] 2.4 Melden kan de beurt niet laten falen (try/except om het hele blok).

## 3. Kanaal

- [x] 3.1 `#statistics` aangemaakt op de relay.
- [x] 3.2 `channels.yml` bijgewerkt met id en doel.

## 4. Gate

- [x] 4.1 `python3 -m unittest test_topology` groen (13 tests).
- [x] 4.2 Bestandsgrenzen: listener 190, bootstrap 84, reporting 44, providers 57.
- [ ] 4.3 Na merge van handbook#12: listener herstarten en één echte beurt
      controleren in `#statistics`.
