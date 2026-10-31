## Why

The odin coding session, in the channel: *"a tidy-up gap in the factory. Mark: 'the factory tidies up by itself'. Three build issues stayed open after their change was split or archived: wordsworth #305, convergence #80 and #104. I've closed them by hand."* They came into view because the digest now also reads `build:` issues (ratatoskr #217).

Today only one road tidies up: when an archive PR made by the build chain merges, the listener closes the open `propose: <change>` issues (`agents/propose_wiring.py`, `after_merge`). Nothing closes `build: <change>` issues, and nothing reacts when a change leaves `openspec/changes/` another way: archived by hand by a coding session, or split or removed in a PR.

## What Changes

- On a 30-minute tick the listener checks, for each open `build: <change>` or `propose: <change>` issue, whether the change is archived on the issue's repository, and closes the issue if so.
- Each close carries a comment with the archive path (`openspec/changes/archive/<dated-id>`) as pointer.
- A change that left `openspec/changes/` without an archive (removed or split) is never closed by the listener; it is only logged, so a human decides.
- The existing close of `propose:` issues after a chain's own archive PR is part of this, not a second mechanism.
- A test proves it (see `tasks.md`).

## Settled by the architect's three points

- **Detection is stateless.** No snapshot: each tick reads main itself, so it covers the chain's own archive and out-of-chain archives alike and survives a restart.
- **Load.** Only repositories with an open build issue are polled, one pair of calls per repository per tick; a `gh` error or rate limit skips the tick and is logged.
- **The dated archive id is not carried** through `propose_git.archive` or `state.json`; the closer resolves it from the archive listing.

## Open questions

- Whether removal without archive (a split) should later be closed with the superseding PR as pointer. The channel first meant it so; the architect's point makes it log-only for now, because a wrong close is worse than a missed one.
- Whether issues with other title prefixes should be closed too. Not decided; only `build:` and `propose:` are in scope.
