# Taken

- [x] 1.1 `routing.py`: marker, woordelijk-controle, mandaat-controle, bronvermelding
- [x] 1.2 Tests op alle vier: vooral wat NIET mag (toegevoegde instructie, ander
      kanaal, verkeerd type in `routes`)
- [x] 1.3 `bootstrap.py` leest `chat.routes` uit de handbook-definitie
- [x] 1.4 `listener.py` haakt het in — één aanroep; sessie-koppeling eruit naar
      `session_wiring.py` omdat het bestand op zijn regelgrens zat
- [x] 1.5 `session_wiring.py` krijgt een eigen suite (stond alleen indirect getest)
- [x] 2.1 Handbook-PR: `docs/agents/odin.md` — `chat.routes: [bouw]` + sectie
      *Capabilities*. Door Mark gemerged (handbook #19, 2026-09-13 17:03Z).
- [x] 2.2 odin lid van #bouw op de relay — Mark draaide `add-member.py`:
      "b0e20b3080ca… in 1/1 kanalen als bot (via orchestrator)".
- [x] 2.3 De listener ziet `routes: ['bouw']` en draait op de nieuwe code.
      Valkuil daarbij, nu gedocumenteerd in `bootstrap.fetch_def`:
      raw.githubusercontent cachet ~5 minuten, dus vlak na een handbook-merge
      haalt de listener nog de oude definitie op.
- [ ] 2.4 **Nog te doen door Mark, in de chat**: één doorstuur die slaagt en één
      die geweigerd hoort te worden. Dit is het enige wat alleen in een echt
      gesprek te meten is — de code-kant staat vast in `test_routing.py`, maar
      of odin de marker ook daadwerkelijk schrijft blijkt pas uit een beurt.
- [x] 2.5 Change archiveren
