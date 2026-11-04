## Why

The factory sat idle for about 21 hours twice (2 and 3 Nov 2026), each time after a
merge whose next step was ready. The next step was named in the merged change's own
proposal (the `originals-ingest-*` and `particle-names-*` changes), but nothing
started it until a person asked. The coding session, writing to odin on 3 Nov:
*"The factory has been idle since yesterday 11:30, after originals-ingest-seam and
particle-names-rule merged."* and *"After each merge, start the next step in its
line without waiting for me."*

A second cause sits in the road itself: odin's `!build` counts only on the first
line of its answer, so after a merge it can start one build per answer, and an
announcement such as "I'm starting it now" on a later line started nothing.

## What changes

- When a build's PR merges, the listener reads the merged change's `proposal.md`
  for a `Next:` or `Depends on` line that names a step in the same sequence, and
  queues that step's build by itself.
- The queued build goes through the same gates as any other: the circuit breaker
  (`max_builds_per_change_day`), `max_concurrent` and `builds_per_day`. Chaining
  never bypasses a gate and never counts as a build Mark typed himself.
- A step whose own proposal names a deploy precondition is queued for build
  only: its PR merges, but it is never deployed by the listener.
- The channel says what was chained, or why nothing was (no named step, already
  building or queued, proposal unreadable).
- A test pins the chain from merge to queued build, and each gate.

## Out of scope

- Archiving, deploying and the wake-up of odin after a deploy stay as they are.
- `!build` itself is unchanged.

## Open questions

- **Exact marker for a deploy precondition.** The decision is that a proposal
  "names" one; which words or key the listener recognises is not fixed. Default:
  a line starting `Deploy precondition:` in the step's `proposal.md`.
- **A `Depends on` with several parents** (a step that waits on two changes).
  Default: queue the step only when every named parent is merged; otherwise do
  nothing and say so.
