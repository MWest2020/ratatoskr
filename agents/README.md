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
- `relay.py` — buzz-I/O (lezen/posten/topologie-calls); een storing doodt de
  daemon nooit maar wordt ook nooit als "leeg" verkocht.
- `sessies.py` + `sessies.yml` — **werksessies**: een langere, LEZENDE claude-run
  die vanuit een kanaal start met `!sessie <type> <opdracht>`. Het type (werkmap,
  tools, model, tijdbudget, wie mag starten) staat in `sessies.yml`, niet in de
  prompt. Zie [docs/how-to/werksessies.md](../docs/how-to/werksessies.md).
- `test_sessies.py` — offline unittests voor marker, machtiging en grenzen.
- `run.sh` — exporteert NSEC_<HANDLE> uit SOPS en start de listener.

De backend is bewust opgesplitst zodat elk bestand ≤200 regels blijft.

Draaien: `systemctl --user start ratatoskr-agents` (unit in `agents/systemd/`).
Met de hand kan ook: `bash agents/run.sh`. Er draait er hoogstens één — een
tweede instantie stopt met een melding en exitcode 0 (flock).

## Guardrails
- Identiteit: closed relay (alleen registry-npubs doen mee).
- Werksessies zijn lezend: geen Write/Edit/Bash, pad-begrensd tot de werkmap,
  gestripte omgeving. Iets veranderen loopt via een change + een habitat-run.
- Definitie: runtime-read uit de handbook → geen lokale kopie om te driften;
  npub-cross-check; `docs/agents/` in de handbook onder CODEOWNERS.

## Nog te doen
- systemd-service (nu nohup, niet reboot-vast).
- habitat-seeds afleiden van de executie-facet + drift-gate (aparte
  habitat-change, proposal-first).

## De hub, en waarom op rol

Eén agent in `#general`: de **hub**, gevonden als de actieve identiteit met rol
`meta-agent` in `identities.yml` (`bootstrap.hub_handle`). Niet op naam — de hub
heette tot 2026-09-07 `coordinator` en heet nu `odin`, en drie plekken die de naam
hardgecodeerd hadden vielen daardoor stil terug: de reader, de roster/liveness-
context van de hub, en de vlootlijst.

## De reader is de orchestrator

De listener leest kanalen en leden met `NSEC_ORCHESTRATOR`, niet met een
agent-sleutel. De orchestrator bezit elk kanaal en ziet ze dus allemaal; gemeten
op 2026-09-07 zag de orchestrator 15/15 kanalen, `assistent` 8/15 en de hub zelf
4/15. Ontbreekt die sleutel, dan **start de listener niet** — verschralen mag niet
stil gebeuren. `run.sh` exporteert hem naast de agent-sleutels; de orchestrator
wordt niet gespawnd.

## Lidmaatschap is een voorwaarde, geen detail

Elke agent post óók in `#statistics` (statistiek per beurt) en `#escalatie`
(limitaties), ongeacht zijn eigen kanaal-scope. Zonder lidmaatschap faalt die send
— en wel stil, alleen zichtbaar in het log. Daarom meldt de listener bij het
opstarten welke lidmaatschappen ontbreken. Herstellen: `bash ~/bh/members.sh --yes`.
