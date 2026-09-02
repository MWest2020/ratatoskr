# Design: add-session-identities

Niet-voor-de-hand-liggende keuzes met verworpen alternatieven (CLAUDE.md-eis).

## 1. Rol `sessie` — licht, zonder handbook-def en zonder listener-run-lijst

**Keuze:** een sessie-identiteit is puur een sleutelpaar + registry-entry (rol
`sessie`) + relay/#general-lidmaatschap. Geen `docs/agents/<naam>.md` en niet in
`agents/agents.yml run:`.

**Verworpen:** `create-agent.py` hergebruiken. Dat maakt een volwaardige
*chat-agent* (handbook-def + run-lijst), waarna de listener de sessie als
`claude -p`-chat-agent zou proberen te spawnen. Een interactieve Claude-sessie is
géén gespawnde chat-agent — het onderscheid is bewust. Een sessie hoeft alleen
toerekenbaar te posten, niet bestuurd te worden door de listener.

## 2. `ping.sh` `IDENT` — default `bouwer`, gefilterd op rol

**Keuze:** `IDENT` (env, default `bouwer` voor compat) selecteert de identiteit;
alleen rollen `sessie` en `chat-agent` mogen posten.

**Verworpen:** (a) geen filter — dan post `IDENT=mark` onder de mens-sleutel
(impersonatie, precies wat we dichten); (b) alleen `sessie` toestaan — dan breken
de bestaande `bouwer`-pings (recurring jobs, ops). De allowlist `{sessie,
chat-agent}` blokkeert de mens (`mark`, rol `mens`) én houdt compat.

## 3. Tailnet-adres als relay-URL — verworpen (voor nu)

**Keuze:** `ping.sh` houdt de community-host `ws://192.168.178.60:3000`.

**Verworpen:** `ws://100.80.218.83:3000` (tailnet-IP). De relay is
*community-scoped op de LAN-host*; via het tailnet-IP komt "no community
configured for this host". Een echte tailnet-relay vergt een relay-herconfig —
aparte change. Vanaf tailnet-nodes werkt de LAN-host via de subnet-router.

## Fail-closed secret-hantering

`create-session-identity.py` schrijft de secret vóór de publieke registry-entry en
verifieert dat de SOPS-output versleuteld is vóór het git-getrackte bestand te
vervangen — een mislukte encryptie mag nooit een plaintext-sleutel naar git laten
lekken. (create-agent.py heeft ditzelfde patroon nog niet gehard — aparte
follow-up.)
