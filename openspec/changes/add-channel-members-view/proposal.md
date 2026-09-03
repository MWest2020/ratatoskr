# Change: add-channel-members-view

## Why

De app toonde alleen *per agent* in welke kanalen hij zit (agents-drawer), en
alleen voor de vier hardgecodeerde chat-agents. Mark kan zo niet zien wie er in een
kanaal zit — zeker niet een sessie als internetnl-cli die net aan #netnl/#marketing
is toegevoegd. De namen-map was bovendien hardgecodeerd en liep achter op
`identities.yml`.

## What Changes

- **Backend**: namen (agents én sessies) worden nu uit `identities.yml` geladen via
  de bestaande git-leeslaag (`github.get_file`, gecachet), i.p.v. hardgecodeerd —
  `author()` en de nieuwe view dekken zo alle identiteiten. Nieuwe route
  `/api/channel-members` → per kanaal de echte relay-leden met naam + rol.
- **Frontend**: de "wie zit waar"-drawer krijgt een toggle **per agent / per
  kanaal**; "per kanaal" toont per kanaal de leden (klikbaar naar het kanaal).

## Impact

- `chat/roster.py` (nieuw: identity_map + chat_agents), `chat/buzzcli.py` (channel_roster, author, ME→gerotenteerde mark-pubkey), `chat/server.py` (route),
  `chat/index.html`, `chat/app-ui.js`, `chat/app.css`. Read-only, additief.
