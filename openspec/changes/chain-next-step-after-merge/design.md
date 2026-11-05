## Context

`build_wiring.follow_merges` calls `after_merge(m)` for every merged PR, and
`propose_wiring.after_merge` already dispatches on `m["kind"]` (`archive`, `propose`)
and returns early for builds. `try_build` (`build_wiring`) is the one road from a
`!build` marker to a habitat chain: it runs `build.check`, queues a build that has to
wait, opens a build issue when none is given, and refuses a change that is already
building or queued.

The architect's FAIL on #225 (4 Nov) named three gaps, all settled here: how "merged"
is decided, where a build-only flag would travel, and where the wiring fits under the
200-line limit. The build-only flag is taken out of this change altogether.

## Grammar

Read from `proposal.md`, as the existing proposals already write it (`## Depends on`,
`## Deploy precondition` in wordsworth's `originals-ingest-*` changes):

- **Sections, not inline keys.** A section is a line `## <Name>` (level-2 heading, the
  name compared case-insensitively, surrounding whitespace ignored) up to the next
  `## ` line or the end of the file.
- **`## Next`**: the first change id in backticks in the section is the next step. A
  change id is `[a-z0-9][a-z0-9-]*`. No backticked id in the section is a malformed
  section: said in the channel as such, nothing requested.
- **`## Depends on`**: every backticked change id in the section is a parent. Prose
  around them is ignored.
- **`## Deploy precondition`**: the section's presence is the precondition; its text is
  for people.
- Only the first section of each name counts. A missing `## Next` is "no next step
  named".

## Choices

- **Seam: `propose_wiring.after_merge`, logic in two new modules.** `agents/chain_next.py`
  is pure: `parse(text)` returns `next`, `parents`, `precondition`, `malformed`.
  `agents/chain_wiring.py` holds `setup(cfg, hub, say, try_build, runner=subprocess.run,
  log=print)` returning `chain(m)`: read A's proposal, read B's, decide, and either call
  `try_build(f"!build {repo} {B}", hub, cname, cid, own=True)` or say why not.
  `propose_wiring.setup` takes `try_build=None`, builds `chain` when it is given, and its
  `after_merge` calls `chain(m)` where it now returns early for a build (`kind` not
  `propose`/`archive`). `listener.py` passes `try_build=try_build` on the line that
  already calls `propose_wiring.setup` (no new line). Measured 2026-11-05:
  `listener.py` 200, `build_wiring.py` 200, `build.py` 200, `propose_wiring.py` 192;
  the budget is the 8 free lines in `propose_wiring.py`, of which this uses about 4.
  `build_wiring.py` and `build.py` are not touched.
- **One road, continued.** The chain does not dispatch habitat itself; it hands a
  `!build` line to `try_build`, exactly as the hub's own answer does. That keeps every
  gate and the "one road" requirement (MODIFIED in the spec delta, not bypassed).
- **Merged = just merged, or `build: <P>` merged.** `chain_wiring` runs
  `gh pr list --repo <owner>/<repo> --state merged --search "build: <P> in:title"
  --json title` and requires an exact title match `build: <P>`. A test pins the title
  `build_merge.open_pr` writes against this search, so a change to one breaks the other
  loudly.
- **Raw reads.** `gh api repos/<owner>/<repo>/contents/openspec/changes/<c>/proposal.md
  -H "Accept: application/vnd.github.raw+json"`. A body that starts with `{` means the
  header did not take; that is a failed read, never "no next step".
- **Stop in front of a precondition.** The listener cannot check a backup or a snapshot,
  and threading a build-only flag through `begin`/`Builds.start`/`follow_merges` touches
  three modules at the line limit. So this change never requests a step with a
  `## Deploy precondition`; `chain-build-only-precondition` adds the build-only path.
- **Loop guard.** A `## Next` naming a change that is archived on that repository
  (`gh api .../openspec/changes/archive` listing contains `*-<id>`) is refused and said.
- **Channel.** `chain(m)` speaks in `m["cid"]`; when an adopted entry has no `cid`, it
  logs the outcome instead of dropping it.

## Rejected alternatives

- **Odin starts the next step.** Fails on the first-line rule and on odin not being
  awake at the merge: the idle gap being fixed.
- **Reverse lookup (scan every proposal on main for a `Depends on` naming A).** No new
  section needed, but one `gh` read per open change per merge, and prose in `Depends on`
  sections (e.g. "since split into four steps") makes the parents ambiguous.
- **A chain file per sequence.** A second source of truth next to the proposals.
- **The openspec or archive listing as "merged".** Wrong at exactly the moment the chain
  fires (see Grammar and the proposal).
- **Build-only in this change.** It needs state threaded through three modules at the
  line limit; split out as `chain-build-only-precondition`.
- **Bypassing the day cap for chained steps.** The cap bounds the agents' loop; a chain
  is exactly that loop.
