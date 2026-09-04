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
- `bootstrap.py` — opstart-helpers: YAML-lezers + de handbook-def-parser (`fetch_def`).
- `topology.py` — relay-topologie: welke kanalen bestaan (`poll_channels`) en wie
  is waar lid (`members`), gecachet; `is_scoped` (pure union-regel).
- `prompts.py` — context/prompt-bouwers + `mentioned` (woordgrens-match).
- `providers.py` — provider-naad (`claude -p`; een nieuw backend = één tak).
- `test_topology.py` — offline unittests (`cd agents && python3 -m unittest test_topology`).
- `run.sh` — exporteert NSEC_<HANDLE> uit SOPS en start de listener.

De backend is bewust opgesplitst zodat elk bestand ≤200 regels blijft.

Draaien: `bash agents/run.sh` (op agent-lxc; claude+buzz+age-key aanwezig).

## Guardrails
- Identiteit: closed relay (alleen registry-npubs doen mee).
- Definitie: runtime-read uit de handbook → geen lokale kopie om te driften;
  npub-cross-check; `docs/agents/` in de handbook onder CODEOWNERS.

## Nog te doen
- systemd-service (nu nohup, niet reboot-vast).
- habitat-seeds afleiden van de executie-facet + drift-gate (aparte
  habitat-change, proposal-first).
