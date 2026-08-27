# agents — chat-agent-listener (definities uit de handbook)

De chat-agents draaien via een dunne `claude -p`-listener (sub-first). De
DEFINITIES (mandaat, systemprompt/chat-facet, kanalen, npub) leven NIET hier maar
in de **handbook** — single source of truth: `MWest2020/handbook` →
`docs/agents/<naam>.md`, MCP-leesbaar via `handbook_mcp`.

- `agents.yml` — dunne roster-pointer: WELKE agents deze instantie draait +
  `registry_base` (de handbook-raw-URL). Niet de definitie.
- `listener.py` — haalt per agent de chat-facet uit de handbook, verifieert de
  npub tegen `identities.yml` (guardrail: geen bron of npub-mismatch → geen
  spawn, fail-closed), en draait de loop: `@handle`-mention → `claude -p` met de
  handbook-systemprompt → antwoord terug in het kanaal.
- `run.sh` — exporteert NSEC_<HANDLE> uit SOPS en start de listener.

Draaien: `bash agents/run.sh` (op agent-lxc; claude+buzz+age-key aanwezig).

## Guardrails
- Identiteit: closed relay (alleen registry-npubs doen mee).
- Definitie: runtime-read uit de handbook → geen lokale kopie om te driften;
  npub-cross-check; `docs/agents/` in de handbook onder CODEOWNERS.

## Nog te doen
- systemd-service (nu nohup, niet reboot-vast).
- habitat-seeds afleiden van de executie-facet + drift-gate (aparte
  habitat-change, proposal-first).
