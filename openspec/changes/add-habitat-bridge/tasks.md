# Tasks: add-habitat-bridge

Voorwaarde: fase 0–2 bewezen betrouwbaar; voor deel B ook habitats
`amend-worker-task-ref` toegepast.

## Deel A — findings-terug (uitgaand, geen kooi-amendement)

- [ ] A.1 Orchestrator/notify: lees de reviewer-/security-`findings` uit het
      run-verdict (`worker/schemas/*.json`) en post ze als thread-reply onder de
      run-post in `#runs`/`#review` (severity/location/description)
- [ ] A.2 Best-effort + geheimen-check: geen PAT's/diff-inhoud, alleen findings +
      links; relay plat blokkeert een run nooit
- [ ] A.3 Live smoke: een FAIL-run levert findings zichtbaar in de thread

## Deel B — kanaal → dispatch (Mark poortwachter, vergt habitat-amendement)

- [ ] B.1 Orchestrator: detecteer een dispatch-verzoek in `#bouw`; formuleer een
      dispatch-voorstel in de thread (rol/change/repo) — nooit autonoom dispatchen
- [ ] B.2 Bevestigingspoort: alleen na Marks expliciete 👍 gaat de orchestrator
      verder; anders niets
- [ ] B.3 Taakbestand: orchestrator schrijft het plan in de doelrepo (git,
      commit) en roept `dispatch.sh` aan met `HABITAT_TASK_REF=<pad>`
- [ ] B.4 Kooi-bewijs: geen agent roept `dispatch.sh`; workers houden geen
      relay-toegang; `git diff` op habitats `cage/` leeg
- [ ] B.5 Live smoke: doel in `#bouw` → voorstel → Marks bevestiging → run →
      verdict + findings terug in de thread. Eén volledige lus.
