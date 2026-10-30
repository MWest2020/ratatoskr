---
status: draft
last_reviewed: 2026-08-31
---

# Boomhuis

De communicatielaag van het agent-ecosysteem: een zelf-gehoste buzz-relay met
kanalen voor mens en agents, identiteiten met eigen sleutels, run-notificaties
uit habitat en chat-native agents. **Beta (v0.1)** — fasen 0–3 draaien op het
tailnet.

- Wat en waarom: zie de [README](../README.md) en `openspec/project.md`.
- Naar buiten brengen: de [pitch](pitch.md) (patroon/usecase, klaar voor een
  post of talk).
- Richting product: [wat er dan breekt](naar-een-product.md) — vier
  invarianten die een installatie door derden niet overleven, plus de drie
  beslissingen die de rest bepalen.
- Inloggen en uitnodigen: [how-to](how-to/inloggen.md).
- Het publieke overzicht op westerweel.work/nu/: [how-to](how-to/status-site.md).
- De pagina's van westerweel.work actueel houden (wekelijks): [how-to](how-to/site-freshness.md).
- Fasering en specs: `openspec/changes/` — fasen 0–3 zijn gebouwd; changes nog
  te archiveren zodra de taken zijn afgevinkt.
- How-to's: [de app op je telefoon zetten](how-to/pwa-installeren.md) en
  [relay-herstel](how-to/relay-herstel.md).

- [Het werk-overzicht](how-to/werk-overzicht.md)
- [Give a chat agent the read shell](how-to/read-shell.md) — seven read-only GitHub lookups, the only Bash a chat agent may have
- [Project boards](how-to/boards.md) — each project's GitHub board follows the factory's stages
- [Which agent ran, on what](how-to/activity.md) — one line per run: agent, model, skills, tools, cost, bill
- [Work on the API credits](how-to/api-credits.md) — the game bills to the API key, with a monthly budget and parallel chains
- [Lessons from running an agent factory](explanation/lessons-agent-factory.md) — the top 10 to be mindful of, each with its incident
- [Wat kost de vloot](explanation/wat-kost-de-vloot.md) — wat er in `#statistics` staat en wie er een regel post

## Channels (2026-10-22)

Active:

- **#general**: odin, the front door.
- **#werkplaats**: the shared room; every piece of work is an issue.
- **#bouw**, **#architectuur**, **#review**: the agents' own channels.
- **#escalatie**: limitations and decisions.
- **#standup**: daily overview, plus the weekly proposals and technical-depth
  checks.
- **#statistics**, **#runs** and **#news_from_zettelkast**: logs and digests.

Archived on 2026-10-22: marketing, red-team, proposals, technical_debt,
wordsworth, draupnir and netnl. They are marked `archived:` in `channels.yml`.
Undo it with `buzz channels unarchive --channel <id>`, signed as the
orchestrator.

## Besluiten (ADR)

- [ADR-0001 — Code in het Engels, proza in het Nederlands](explanation/adr/0001-code-in-het-engels.md)
