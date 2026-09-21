# Tasks

## 1. Decide
- [ ] **For Mark.** Research spoke on the open web, or a domain allow-list?
      Recommendation: open web, with the marker rem.
- [ ] **For Mark.** The handbook change to odin's mandate is his gate
      (CODEOWNERS). Nothing else in this change touches an agent definition.

## 2. The hub learns it has spokes
- [ ] `docs/agents/odin.md`: delegation as a named capability, next to
      `route_message`. Which types it may start, and that the answer comes back
      in its own voice.
- [ ] Chat facet: the three sentences from `design.md`. No apology for a road
      that exists.
- [ ] Remove the line that is now false: *"conversatie-only, geen shell/repo"*
      describes odin's own hands, not what it may ask for.

## 3. The research spoke
- [ ] A session type `onderzoek` in `sessions.yml`: no repository, a scratch
      workdir, `Read/Grep/Glob/WebFetch`, `starters: [mark, orchestrator, odin]`,
      identity odin.
- [ ] Its system message: report back with the source, say plainly when
      something could not be retrieved.
- [ ] `docs/how-to/werksessies.md`: the type, and that it is the hub's way of
      staying free.

## 4. The rem
- [ ] Markers count only on the first line of an answer.
- [ ] Test: an answer quoting `!sessie`/`!route` starts nothing.

## 5. Explicitly not
- [ ] No `WebFetch` in a chat agent definition, no `Bash`, no credential in
      `ENV_KEEP`, no MCP server, and `!dispatch` stays Mark's.
