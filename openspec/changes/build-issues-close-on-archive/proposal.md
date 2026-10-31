## Why

The odin coding session, in the channel: *"a tidy-up gap in the factory. Mark: 'the factory tidies up by itself'. Three build issues stayed open after their change was split or archived: wordsworth #305, convergence #80 and #104. I've closed them by hand."* They came into view because the digest now also reads `build:` issues (ratatoskr #217).

Today only one road tidies up: when an archive PR made by the build chain merges, the listener closes the open `propose: <change>` issues (`agents/propose_wiring.py`, `after_merge`). Nothing closes `build: <change>` issues, and nothing reacts when a change leaves `openspec/changes/` another way: archived by hand by a coding session, or split or removed in a PR.

## What Changes

- When a change is archived, or removed from `main` without being archived, the listener closes every open issue titled `build: <change>` or `propose: <change>` on that repository.
- Each close carries a comment with a pointer: the archive path (`openspec/changes/archive/<dated-id>`) when archived, or the PR that removed or superseded the change when not.
- The existing close of `propose:` issues after a chain's own archive PR is part of this, not a second mechanism.
- A test proves it (see `tasks.md`).

## Open questions

- How the listener notices a change that left `main` outside its own archive PR (a hand-archive, a split): by watching merged PRs, or by comparing `openspec/changes/` on `main` per tick. Not decided in the channel; `design.md` records both.
- Whether issues with other title prefixes should be closed too. Not decided; only `build:` and `propose:` are in scope.
