# Boomhuis

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
| 2 | `add-chat-native-agents` | Langlopende buzz-acp-agents: marketing, architectuur-sparring |
| 3 | `add-habitat-bridge` | Verzoek-in-kanaal → dispatch, bevindingen terug in de thread (vergt habitat-amendement) |

Status: greenfield — alle changes staan op *propose*. Rome is niet in één dag
gebouwd; dit loopt over maanden en elke fase is los waardevol.

## Wat er nu leeft (2026-08)

- **Relay** — self-hosted buzz op vm 109 / `192.168.178.60`, closed mode,
  tailnet-only. Reboot-vaste systemd-services: `boomhuis-chat` (relay-VM) en
  `boomhuis-agents` (agent-lxc, user-service).
- **Web-chat** (`chat/`) — Slack/Telegram-achtige interface op
  `http://192.168.178.60:8090/` (desktop-browser + telefoon). Kanalen dynamisch
  uit de relay, **maken/verwijderen in de app**, agents-overzicht, `@mention` +
  thread-continuïteit (doorpraten zonder mention).
- **Kanalen** — `#general` (hub: roep hier elke agent aan), plus `#runs
  #escalatie #bouw #review #architectuur #marketing`.
- **Vier chat-agents** — `assistent` (overal), `architect` (#architectuur),
  `bouwer` (#bouw), `marketing` (#marketing) — allemaal ook in #general. Ze
  draaien via één multi-agent `claude -p`-listener (`agents/`).
- **Eén bron van waarheid voor agent-definities** — canoniek in de **handbook**
  (`docs/agents/<naam>.md`, MCP-leesbaar), met twee facetten (chat voor
  boomhuis, executie voor habitat). De listener leest de chat-facet daarvandaan
  (guardrail: geen bron/npub-mismatch → geen spawn); habitat-seeds worden er
  met een drift-gate uit afgeleid. Een bouwer is overal dezelfde bouwer.
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
