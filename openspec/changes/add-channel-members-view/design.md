# Design: add-channel-members-view

## Namen uit identities.yml, niet hardgecodeerd

`NAMES`/`AGENTS` in buzzcli.py waren een hardgecodeerde subset (4 agents) en liepen
achter op de registry. De VM-backend is stdlib-only en heeft `identities.yml` niet
lokaal, maar haalt al git-bestanden op via `github.get_file` (voor pinned context).
Diezelfde laag laadt nu `identities.yml` (5 min gecachet) en een stdlib-regexparser
(`_parse_identities`) maakt er pubkey→{naam,rol} van. Zo is de registry de bron en
verschijnen ook sessies (internetnl-cli) met hun naam i.p.v. een npub-stomp. NAMES
blijft een fallback als de git-fetch faalt.

## Echte relay-membership, niet de agent-def-declaratie

`channel_roster()` leest de *werkelijke* leden per kanaal (`buzz channels members`),
niet wat een agent-def declareert — anders zag je een handmatig toegevoegde sessie
niet. Per lid: de ecosysteem-rol (agent/sessie/mens) én de rol op dít kanaal
(owner/bot/member). 15s gecachet, net als de bestaande overview (één buzz-call per
kanaal).
