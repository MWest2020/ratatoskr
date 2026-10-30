# Kanaal-kennis: #architectuur

Kernprincipes van het ecosysteem (gebruik deze als vaste grond bij advies):

- **Git is de waarheid.** Verdicts, audit-JSONL en run-rapporten leven in git
  (habitat). Chat/relay is spiegel, nooit gezaghebbende state.
- **De kooi is niet-onderhandelbaar.** Habitat-workers: default-deny egress,
  RBAC per rol, geen relay-toegang, geen push-credential in de agent.
- **Eén bron van waarheid voor agents.** Canonieke defs in de handbook
  (`docs/agents/`), MCP-leesbaar; ratatoskr en habitat lézen, kopiëren niet.
  Drift is een CI-gate, geen hoop.
- **Proposal-first (OpenSpec).** Geen code vóór "apply"; cross-repo via de
  handbook, kooi-rakend via een amendement in habitat.
- **Saai & auditeerbaar boven snel & slim.** Benoem de "clevere valkuil".
- **Twee agentklassen.** Gekooid+eenmalig (habitat-Jobs) vs chat-native
  (`claude -p`-listener, sub-first, géén buzz-acp/API-key).
