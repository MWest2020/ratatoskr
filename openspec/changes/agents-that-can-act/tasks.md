# Tasks

## 1. Decide
- [x] **For Mark.** Research spoke on the open web, or a domain allow-list?
      **Open web** — Mark, 2026-09-21: *"open web, en bouw het maar"*.
- [ ] **For Mark.** The handbook change to odin's mandate is his gate
      (CODEOWNERS). Nothing else in this change touches an agent definition.
      Prepared as a pull request on MWest2020/handbook.

## 2. The hub learns it has spokes
- [ ] `docs/agents/odin.md`: delegation as a named capability, next to
      `route_message`. Which types it may start, and that the answer comes back
      in its own voice. **Handbook PR, Mark merges.**
- [ ] Chat facet: the three sentences from `design.md`. **Same PR.**
- [ ] Remove the line that is now false: *"conversatie-only, geen shell/repo"*
      describes odin's own hands, not what it may ask for. **Same PR.**

## 3. The research spoke
- [x] A session type `research` in `sessions.yml` (English name, per ADR-0001):
      no repository, scratch workdir `~/research`, `Read/Grep/Glob/WebFetch`,
      `starters: [mark, orchestrator, odin]`, identity odin, 15 minutes.
- [x] Its system message: report back with the source, say plainly when
      something could not be retrieved — including the video case, where a link
      yields a page shell and no transcript.
- [x] `docs/how-to/werksessies.md`: the type, and that it is the hub's way of
      staying free.

## 4. The rem
- [x] Markers count only on the first line of an agent's OWN answer
      (`read_own_marker`); a human message is unchanged, because there the text
      is the person's own. The difference is trust, not syntax.
- [x] Test: an answer quoting `!sessie` starts nothing, and the same text typed
      by a human still does. Checked once with the fix removed.

## 5. Explicitly not
- [x] No `WebFetch` in a chat agent definition, no `Bash`, no credential in
      `ENV_KEEP`, no MCP server, and `!dispatch` stays Mark's. Nothing in this
      change touches any of them.
