## Context

`build_wiring.follow_merges` already knows the moment a build's PR merges, and
`try_build`/`drain_queue` already queue a build that has to wait and start it when
`build.check` allows. The missing link is to turn "this change merged" into "the
next change is requested".

## Choices

- **Hook at the merge, read the proposal from main.** After a successful merge of
  a build (`kind` not `propose` or `archive`), the listener reads
  `openspec/changes/<change>/proposal.md` on the repository's main with `gh api`
  (as `build.change_exists` does) and parses `Next:` / `Depends on` lines in a new
  module `agents/chain_next.py`. Git is the source of truth; no list of chains is
  kept in the listener or in `state.json`.
- **Reuse the queue, not a second path.** The chained step goes through the same
  code as a `!build` and into `builds.queued` when it has to wait. That gives the
  breaker, `max_concurrent`, `builds_per_day`, the "already building or queued"
  check and restart-safe persistence for free.
- **Capped.** The chained build is requested as the hub, so the `builds_per_day`
  budget applies. Only a `!build` typed by Mark is exempt.
- **Build-only flag on the queue entry.** A step whose proposal names a deploy
  precondition is queued with `deploy: false`; `follow_merges` then skips the
  `deploying` hand-off for it and says so in the channel and on the issue. The
  listener cannot check the precondition itself (a backup, a snapshot), so it
  never deploys such a step; a person does.
- **Silence is a bug.** When nothing is chained the reason is said in the channel.
  A `gh` error is logged and said, never an empty result.

## Rejected alternatives

- **Odin starts the next step in its own answer.** Fails on the first-line rule
  (one marker per answer) and on odin not being awake at the merge; that is the
  idle gap being fixed.
- **A chain file per sequence in `agents/`.** A second source of truth next to the
  proposals; it drifts. The proposals already name the order.
- **Deploying the chained step, then checking the precondition.** A deploy that
  needs a backup first cannot be undone by a failed check afterwards.
- **Bypassing the day cap for chained steps.** The cap bounds the agents' loop; a
  chain is exactly that loop.
