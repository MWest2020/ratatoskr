# Change: de hernoeming naar Ratatoskr

## Why

De app heet sinds 2026-09-11 Ratatoskr voor wie 'm gebruikt (PR #80). De rest
heet nog boomhuis: de repo, het image, het volume met alle accounts, en elke
`BOOMHUIS_*`-instelling. Half hernoemd is slechter dan niet hernoemd — je zoekt
dan op twee namen en weet nooit welke de echte is.

Mark, 2026-09-11: *"migreer de naam maar."* Nu kan het nog goedkoop: één
gepubliceerd image, één draaiende installatie, nul derden. Na de eerste externe
installatie is dit een migratie die je aan iemand anders moet uitleggen.

## What Changes

- **Repo** `MWest2020/boomhuis` → `MWest2020/ratatoskr`. GitHub laat de oude
  URL's doorverwijzen, dus bestaande clones en remotes blijven werken.
- **Image** `ghcr.io/mwest2020/boomhuis-chat` → `…/ratatoskr-chat`. Het oude
  pakket blijft staan: installaties pinnen op een tag en die moet blijven werken.
- **Instellingen** `BOOMHUIS_*` → `RATATOSKR_*`, via één leesfunctie die de oude
  naam blijft accepteren. Een draaiende installatie valt dus niet om op een
  hernoeming, en een terugrol werkt nog.
- **Volume** `boomhuis-chat-data` → `ratatoskr-chat-data`, met een gedocumenteerd
  kopieerpad voor de bestaande installatie. Accounts en push-abonnees staan
  daarin; die mogen niet stilzwijgend verdampen.
- **De host**: systemd-units en de checkout-map op agent-lxc volgen de naam.
- Docs, README en `openspec/project.md` vertellen het verhaal één keer: Ratatoskr
  is de boodschapper, Yggdrasil het ecosysteem (als verhaal — het is een bestaand
  netwerkproject, zie de sessie-analyse van 2026-09-11).

## Impact

- Gewijzigd: `chat/` (nieuwe `instellingen.py` + alle leesplekken), `deploy/`,
  `.github/workflows/chat-image.yml`, `agents/`, `jobs/`, `orchestrator/`, docs.
- Spec: `webchat-pwa` krijgt één requirement over de naam van instellingen.
- Buiten deze repo: de handbook-agentdefinities en Marks systemd-units. Die
  volgen apart; de repo kan niet wachten tot de handbook mee is.
