## Why

`chat/server.py` (311 regels) en `chat/index.html` (499) overschrijden de harde
CLAUDE.md-invariant **"bestanden ≤ 200 regels"**. De habitat-reviewer FAILt elke
change die deze files raakt hierop (gevonden bij `add-unread-counter`, dat na
inhoudelijke goedkeuring bewust gemerged is met deze drift als bekende follow-up).
Pre-existing drift; los het bij de bron op zodat volgende changes clean door de
review landen.

## What Changes

- **`chat/server.py`** opsplitsen: routing dun houden, logica naar modules (bv.
  channel/overview-laag naast het bestaande `github.py`).
- **`chat/index.html`** ontvlechten: de inline `<script>` en `<style>` naar losse,
  door het backend geserveerde bestanden (`app.js`, `app.css`).
- **Geen functionele wijziging** — puur structuur; PWA + endpoints houden identiek
  gedrag. Elk `chat/`-bronbestand komt ≤ 200 regels. (Refactor zonder spec-delta;
  archiveer t.z.t. met `--skip-specs`.)
