## Why

Mark, 2026-09-07: *"ik wil eigenlijk maar met 1 agent spreken: odin (coordinator)
als hub. de rest van de agents zijn spoke."* En: *"hernoem versum naar
odin-worker."*

Zo stond het ervoor. In `#general` — het kanaal waar Mark begint — konden **zeven**
agents antwoorden (assistent, architect, bouwer, marketing, coordinator,
ontwerper, reviewer) plus **vijf sessie-identiteiten** die er hun voortgang
dropten. Eén vraag leverde dus meerdere antwoorden van agents die elkaars context
niet hadden, en de sessies maakten van het hub-kanaal een logboek.

## What Changes

- **`coordinator` → `odin`, de hub.** De bestaande `odin`-identiteit krijgt rol
  `meta-agent`; de `coordinator`-sleutel gaat op `ingetrokken`. De listener-run-
  lijst draait `odin`; de definitie verhuist in de handbook naar `odin.md`
  (PR handbook#16).
- **`versum` → `odin-worker`** in `identities.yml` én in de SOPS-sleutelbundel.
  Zelfde sleutelpaar, andere handle: de geschiedenis blijft toewijsbaar.
- **Sessies uit het hub-kanaal, afgedwongen.** `ping.sh` weigert `CHAN=general`
  voor rol `sessie` (exit 8) en verwijst naar het projectkanaal of `#escalatie`.
  Een afspraak in een README is geen control; deze regel is dat wel.
- **Relay-profielnamen** van `odin` en `odin-worker` gezet, zodat de web-chat de
  nieuwe namen toont in plaats van de oude.
- **Naam-fallback** in `buzzcli.NAMES` kent `odin` én de ingetrokken
  `coordinator`-sleutel, zodat oude berichten leesbaar blijven.

## Impact

- `identities.yml`, `secrets/identities.yaml`, `agents/agents.yml`,
  `orchestrator/ping.sh`, `chat/buzzcli.py`.
- **Volgorde:** de listener mag pas herstarten ná handbook#16, anders vindt hij
  `odin.md` niet en valt de hub fail-closed weg.
- Andere sessies (`hubby`, `hub`, `internetnl-cli`) houden hun naam maar vallen
  wel onder de nieuwe `#general`-regel.
