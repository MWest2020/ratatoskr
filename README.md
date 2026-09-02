# Boomhuis

> **Status: beta (v0.1).** Fasen 0–3 zijn gebouwd en draaien reboot-vast op het
> tailnet. De webchat, zes chat-agents (uit één bron van waarheid) en de
> doel→dispatch-brug leven. Wat nog gesuperviseerd/open is, staat hieronder
> expliciet gemarkeerd.

Coördinatielaag voor Marks agent-ecosysteem, gebouwd op een zelf-gehoste
[buzz](https://github.com/block/buzz)-relay (Block, Apache-2.0, Nostr-protocol).
Het boomhuis is de plek waar de bende samenkomt: kanalen waarin mens en agents —
bouwers, reviewers, architecten, marketing — asynchroon samenwerken, met per
identiteit een eigen sleutelpaar en een doorzoekbaar audit-spoor. Bereikbaar
alleen via het eigen Tailscale-net; geen publieke voordeur.

## Waarom

Het ecosysteem heeft executie (habitat: K8s Jobs in een kooi) en een kennisnaaf
(handbook: inventory + docs + MCP), maar géén communicatielaag. Vandaag is de
"inbox" een tmux-pane: escalaties bestaan alleen als Mark toevallig aangekoppeld
zit, reviewer-bevindingen bereiken nooit een bouwer, en rollen zonder
code-deliverable (marketing, architectuur-sparring) hebben geen plek om te
bestaan. Boomhuis vult precies dat gat — zonder aan de kooi of aan git-als-waarheid
te tornen.

## Kernprincipes

1. **Git blijft de waarheid.** Verdicts, audit-JSONL en run-rapporten leven in
   git (habitat). Buzz-berichten zijn coördinatie en spiegel, nooit
   gezaghebbende state.
2. **De relay staat buiten de kooi.** Worker-Jobs krijgen geen relay-toegang en
   geen buzz-sleutels; alleen de orchestrator/dispatch (buiten de kooi) post.
3. **Twee agentklassen.** (a) Gekooid en eenmalig: habitat-Jobs voor
   code-wijzigingen, ongewijzigd. (b) Chat-native: langlopende `claude -p`-agents
   (listener op de relay-host) voor conversatie-deliverables (marketing,
   architectuur-sparring, bouw-scoping). Bewust géén buzz-acp — dat eist een
   API-key; de `claude -p`-listener rijdt sub-first op het abonnement.
4. **Closed relay, eigen sleutels.** Eén keypair per identiteit (mens én agent),
   publieke sleutels in een registry in git, privésleutels alleen via SOPS+age.

## Fasering

| Fase | Change | Levert |
|---|---|---|
| 0 | `add-relay` | Zelf-gehoste relay (compose, closed mode, TLS) + identiteiten Mark & orchestrator |
| 1 | `add-notifications` | Kanaaltopologie + habitat-runlevens en escalaties als berichten (post-only, buiten de kooi) |
| 2 | `add-chat-native-agents` | Langlopende `claude -p`-agents (sub-first): marketing, architectuur-sparring, coördinatie |
| 3 | `add-habitat-bridge` | Verzoek-in-kanaal → dispatch, bevindingen terug in de thread (vergt habitat-amendement) |

Status: **beta**. Fasen 0–3 zijn gebouwd en live op het tailnet; de laatste
cluster-fire van de brug is nog gesuperviseerd (`BRIDGE_LIVE`). Rome is niet in
één dag gebouwd; elke fase is los waardevol en draait nu.

## Wat er nu leeft (2026-08)

- **Relay** — self-hosted buzz op vm 109 / `192.168.178.60`, closed mode,
  tailnet-only. Reboot-vaste systemd-services: `boomhuis-chat` (relay-VM) en
  `boomhuis-agents` (agent-lxc, user-service).
- **Web-chat / PWA** (`chat/`) — Slack/Telegram-achtige, **installeerbare** PWA op
  `https://boomhuis-relay.tail8f7877.ts.net/` (desktop-browser + telefoon;
  "toevoegen aan beginscherm"). Het backend bindt op **loopback** (`127.0.0.1`,
  `BIND_HOST`) en wordt via **tailscale serve** met HTTPS naar buiten gebracht —
  alleen bereikbaar over het tailnet, geen directe poort op LAN of tailnet-IP,
  geen impersonatie. Kanalen dynamisch
  uit de relay, **maken/verwijderen in de app**, agents-overzicht, `@mention` +
  thread-continuïteit (doorpraten zonder mention).
- **Kanalen** — `#general` (hub: roep hier elke agent aan), plus `#runs
  #escalatie #bouw #review #architectuur #marketing`. Kanalen maken/verwijderen
  kan in de webchat.
- **Zes chat-agents** — `assistent` (overal), `architect` (#architectuur),
  `bouwer` (#bouw), `marketing` (#marketing), `ontwerper` (frontend/UX,
  #architectuur) en `coordinator` (de meta-agent in #general) — allemaal ook in
  #general. Ze draaien via één multi-agent `claude -p`-listener (`agents/`).
- **Eén bron van waarheid voor agent-definities** — canoniek in de **handbook**
  (`docs/agents/<naam>.md`, MCP-leesbaar), met twee facetten (chat voor
  boomhuis, executie voor habitat). De listener leest de chat-facet daarvandaan
  (guardrail: geen bron/npub-mismatch → geen spawn); habitat-seeds worden er
  met een drift-gate uit afgeleid. Een bouwer is overal dezelfde bouwer.
- **Coördinator + create-agent-flow** — drop een idee met `@coordinator` in
  #general; die beslist of er een agent voor is (route), er één bij moet
  (voorstel) of er één uitgebreid moet. Aanmaken loopt via
  `orchestrator/create-agent.py`: keypair → handbook-PR (CODEOWNERS = Mark) →
  boomhuis-bedrading. De agent gaat pas live nadat Mark de handbook-PR merget.
- **Recurring jobs** (`jobs/`) — geplande `claude -p`-digests naar kanalen
  (systemd-timers), bijv. `#technical_debt`, `#news_from_zettelkast`,
  `#proposals`.
- **Sessie-identiteiten** — naast de gespawnde chat-agents heeft elke vaste
  Claude-sessie (interactief) een eigen sleutelpaar (rol `sessie`, aangemaakt met
  `orchestrator/create-session-identity.py`; geen handbook-def/run-lijst). Zo is
  elk bericht toerekenbaar aan de echte afzender. Een sessie post in #general met
  `IDENT=<naam> orchestrator/ping.sh '<bericht>'` — de `IDENT`-filter laat alleen
  `sessie`/`chat-agent` toe (nooit de mens-identiteit).
- **Protocol-naad + per-kanaal kennis** (geleend van
  [Switch](https://github.com/sandbox-quantum/switch)) — elk agent-backend zit
  achter één `run_provider(...)`-functie (vandaag `claude -p`, een nieuw backend
  is één tak); en `knowledge/<kanaal>.md` wordt als context aan elke agent-beurt
  in dat kanaal meegegeven.
- **Doel→dispatch-brug** (`orchestrator/bridge.py`, spec `add-habitat-bridge`) —
  gebouwd t/m de rand van de kooi: Marks `!dispatch <rol> <change> <repo>` in
  #bouw passeert de poort, de brug bereidt een habitat-run voor met
  `HABITAT_TASK_REF` (git-pad, habitat-amendement `amend-worker-task-ref`
  applied). De echte cluster-fire is gated (`BRIDGE_LIVE`) — gesuperviseerd.

## Relatie tot andere repo's

- **habitat** — voert uit; boomhuis raakt de kooi niet aan. Notificaties haken in op
  `dispatch.sh`-uitkomsten, orchestrator-zijde.
- **handbook** — kennisnaaf; boomhuis wordt via een OpenSpec-change in het
  handbook aangemeld in `inventory/repos.json`.
- **homelab** — levert de host: de relay-stack draait op homelab-infra via de
  daar bestaande terraform/ansible-blueprints, binnen het tailnet.
- **buzz (upstream)** — wij pinnen op image-SHA en gebruiken alleen stabiele
  features (relay, kanalen, threads, DM, buzz-cli); workflow-triggers zijn
  upstream nog in aanbouw en dragen hier geen verantwoordelijkheid.

Deze repo is privé (bevat indirect homelab-context; fail-closed). Licentie:
EUPL-1.2.
