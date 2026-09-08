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
- [x] 4.3 Listener herstart op de verse registry en één echte beurt nagemeten in
      `#statistics` (2026-09-08 08:55):
      `odin · #general · sonnet→claude-sonnet-5 · 1 turns · $0.10`.
      Het gedeclareerde model wordt dus afgedwongen.

      De beurt daarvóór meldde `claude-haiku-4-5-20251001` en leek een
      handhavingsgat. Dat was de RAPPORTAGE: die nam de eerste sleutel uit
      `modelUsage`, en een run raakt soms meerdere modellen aan. De regel toont nu
      `gevraagd→gedraaid` met een vlag bij een mismatch — anders is dit getal niet
      te vertrouwen als bewijs.
