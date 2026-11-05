## Why

The factory sat idle for about 21 hours twice (2 and 3 Nov 2026), each time after a
merge whose next step was ready. The next step was known (the `originals-ingest-*` and
`particle-names-*` changes are split into ordered steps), but nothing started it until
a person asked. The coding session, writing to odin on 3 Nov: *"The factory has been
idle since yesterday 11:30, after originals-ingest-seam and particle-names-rule
merged."* and *"After each merge, start the next step in its line without waiting for
me."* On 4 Nov odin again left two requested builds unstarted.

A second cause sits in the road itself: odin's `!build` counts only on the first line
of its answer, so after a merge it can start one build per answer, and an announcement
such as "I'm starting it now" on a later line started nothing.

## What changes

- When a build's PR merges, the listener reads the merged change's `proposal.md` on
  main. When it has a `## Next` section, the listener requests the build of the step
  named there, through the same road as `!build`: `try_build`, as the hub, with the
  breaker, `max_concurrent`, `builds_per_day`, the "already building or queued" check
  and the "change exists on main" check.
- Before requesting it, the listener reads the next step's own `proposal.md`:
  - every parent in its `## Depends on` section must be merged; otherwise nothing is
    requested and the channel names the missing parent;
  - when it has a `## Deploy precondition` section, nothing is requested and the channel
    says a person starts that step. Building such a step without deploying it is a
    separate change (`chain-build-only-precondition`); until then the chain stops in
    front of it, so the listener never deploys past a precondition.
- "Merged" is decided by one rule: the change that just merged counts as merged; any
  other parent counts as merged when its build PR, titled `build: <parent>` (the title
  `build_merge.open_pr` writes), is merged on that repository. The openspec listing and
  the archive listing are not used: at merge time the just-merged change is still under
  `openspec/changes` and not yet archived, so both would answer wrongly.
- Every read uses `gh api` with the raw `Accept` header, and "read failed", "no next step
  named", "parent not merged", "deploy precondition" and "requested" are distinct
  outcomes, each said in the channel. A missing channel on an adopted entry is at least
  a log line. Silence is the bug this change fixes.
- `propose_wiring.after_done` still wakes odin. The chain requests first, so odin's
  `!build` for the same step is refused as "already building or queued"; the step is
  built once and the breaker is not tripped by the refusal.
- The proposal template convention: a step that has a successor names it in a `## Next`
  section. The proposals that already exist get that section in their own repositories;
  this change does not edit other repositories.

## Out of scope

- Building a step with a deploy precondition without deploying it
  (`chain-build-only-precondition`, a later change).
- Waiting for the merged change's deploy before chaining (see Open questions).
- Archiving, deploying and the wake-up of odin after a deploy stay as they are.
- `!build` itself is unchanged.

## Open questions

- **Deploy gap.** For wordsworth and convergence the chain fires at the merge, while the
  merged change may still be deploying. The next step is therefore built on a main that
  is merged but not necessarily running. Working assumption: fire at the merge and say
  so in the channel line and the how-to; the check for each step is its PR's own CI.
- **Loops.** A `## Next` that points back at an earlier step would loop until the day cap
  or the breaker stops it. Working assumption: a `## Next` naming a change that is
  already archived on that repository is refused and said.
