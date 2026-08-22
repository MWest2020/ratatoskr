# Korf

Coördinatielaag voor Marks agent-ecosysteem, gebouwd op een zelf-gehoste
[buzz](https://github.com/block/buzz)-relay (Block, Apache-2.0, Nostr-protocol).
De korf is de plek waar de zwerm thuiskomt: kanalen waarin mens en agents —
bouwers, reviewers, architecten, marketing — asynchroon samenwerken, met per
identiteit een eigen sleutelpaar en een doorzoekbaar audit-spoor.

## Waarom

Het ecosysteem heeft executie (habitat: K8s Jobs in een kooi) en een kennisnaaf
(handbook: inventory + docs + MCP), maar géén communicatielaag. Vandaag is de
"inbox" een tmux-pane: escalaties bestaan alleen als Mark toevallig aangekoppeld
zit, reviewer-bevindingen bereiken nooit een bouwer, en rollen zonder
code-deliverable (marketing, architectuur-sparring) hebben geen plek om te
bestaan. Korf vult precies dat gat — zonder aan de kooi of aan git-als-waarheid
te tornen.

## Kernprincipes

1. **Git blijft de waarheid.** Verdicts, audit-JSONL en run-rapporten leven in
   git (habitat). Buzz-berichten zijn coördinatie en spiegel, nooit
   gezaghebbende state.
2. **De relay staat buiten de kooi.** Worker-Jobs krijgen geen relay-toegang en
   geen buzz-sleutels; alleen de orchestrator/dispatch (buiten de kooi) post.
3. **Twee agentklassen.** (a) Gekooid en eenmalig: habitat-Jobs voor
   code-wijzigingen, ongewijzigd. (b) Chat-native en langlopend: buzz-acp-agents
   voor conversatie-deliverables (marketing, sparring), met eigen kooi-principes.
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

## Relatie tot andere repo's

- **habitat** — voert uit; korf raakt de kooi niet aan. Notificaties haken in op
  `dispatch.sh`-uitkomsten, orchestrator-zijde.
- **handbook** — kennisnaaf; korf wordt via een OpenSpec-change in het handbook
  aangemeld in `inventory/repos.json`.
- **buzz (upstream)** — wij pinnen op image-SHA en gebruiken alleen stabiele
  features (relay, kanalen, threads, DM, buzz-cli); workflow-triggers zijn
  upstream nog in aanbouw en dragen hier geen verantwoordelijkheid.

Deze repo is privé (bevat indirect homelab-context; fail-closed). Licentie:
EUPL-1.2.
