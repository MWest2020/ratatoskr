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

## 2. `ping.sh` `IDENT` — default `bouwer`, mens + niet-actief geweigerd

**Keuze:** `IDENT` (env, default `bouwer` voor compat) selecteert de identiteit;
geweigerd worden de **mens**-identiteit (rol `mens`) en elke **niet-actieve**
identiteit (`status != actief`).

**Verworpen:** (a) geen filter — dan post `IDENT=mark` onder de mens-sleutel
(impersonatie, precies wat we dichten); (b) een allowlist `{sessie, chat-agent}` —
die sluit legitieme agentklassen (`orchestrator`, `coordinator`/meta-agent) stil
uit. Een **denylist op rol `mens`** + de status-check blokkeert precies de mens en
ingetrokken sleutels, houdt compat, en sluit geen agentklasse onbedoeld uit. IDENT
gaat via env naar python (geen broncode-interpolatie → geen injectie).

## 3. Tailnet-adres als relay-URL — verworpen (voor nu)

**Keuze:** `ping.sh` houdt de community-host `ws://192.168.178.60:3000`.

**Verworpen:** `ws://100.80.218.83:3000` (tailnet-IP). De relay is
*community-scoped op de LAN-host*; via het tailnet-IP komt "no community
configured for this host". Een echte tailnet-relay vergt een relay-herconfig —
aparte change. Vanaf tailnet-nodes werkt de LAN-host via de subnet-router.

## Fail-closed secret-hantering

`create-session-identity.py` schrijft de plaintext-secret alleen in een
**gitignored** temp (`secrets/_*.yaml`, mode 0600) die in een `finally` altijd
wordt opgeruimd, en vervangt het git-getrackte `secrets/identities.yaml` pas nadat
de SOPS-output geverifieerd versleuteld is (`sops:` aanwezig + returncode 0). De
secret gaat vóór de publieke registry-entry, en het #general-lidmaatschap moet
lukken (anders exit != 0) — geen halve staat. (create-agent.py heeft ditzelfde
patroon nog niet gehard — aparte follow-up.)

De temp moet in `secrets/` staan (niet `/tmp`) omdat de SOPS-creation-rule
path-based is (`secrets/.*`); daarom gitignore i.p.v. buiten de tree schrijven.
