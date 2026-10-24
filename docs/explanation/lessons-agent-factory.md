---
status: current
last_reviewed: 2026-10-24
---

# Lessons from running an agent factory

What we learned letting agents propose, build, review and ship software on
their own: odin in Ratatoskr conducting chat agents, habitat running the
build roles as Kubernetes Jobs, on real repositories (wordsworth, and the
game convergence on API credits). Each lesson names the incident it comes
from, so it can be checked. Mark, 2026-10-24: *"make sure we keep that as
lessons learned ... like top 10 be mindful about."* Add to it as the factory
teaches more.

## Top 10

### 1. Agents loop without a brake

A change that keeps failing gets amended and rebuilt, and each amend makes it
bigger. gdd-economy went round eight times in one afternoon ($26), failing at
another role each time: every finding was real, the change was simply too
big for one build. **Put a circuit breaker on retries** (three builds of a
change a day, then split it) and give the agent the next move: split, not
retry. (ratatoskr #195)

### 2. An agent cannot decide on what it cannot see

odin held a build twice and asked Mark for "the cause", because the
reviewer's finding was on the issue and odin had no way to read issue
comments; another time the FAIL comment was empty because the verdict JSON
put its key in a different place. **Make every failure legible to the agent
that has to act on it**: findings in the comment, a read tool for where they
live. (ratatoskr #162, #168, #172)

### 3. "Tests that never ran" is not "tests that passed"

Builders said PASS on database tests that skipped (no Postgres in the
worker) and on Node tests they could not run (no `npm install`, so no
lockfile). The reviewer rightly failed them. **Give the build environment
what the tests need**, a throwaway database, the package manager, and make
skipped tests count as unrun. (habitat #37, #41)

### 4. Permissions break in ways that look like something else

A writing session had every edit refused in its own folder: the permission
fence was a relative path, and the session had run `cd` into that folder
first. It looked random for hours. **Write permission fences as absolute
paths**, and keep a debug log of every refusal. (ratatoskr #170, #175)

### 5. One budget for every role starves the one doing the work

Architect, reviewer and security never passed $1.03 a run; the builder hit
the shared $5 cap at 127-138 turns, three times. **Budget per role, by the
work it does.** (habitat #42)

### 6. Restarts happen mid-flight; design for them

A deploy restarted the listener and killed a running build with it; another
restart cut a publish off between commit and push and stranded the change.
**Run long work outside the service's process group, persist state before
side effects, and make every step idempotent** (an existing commit is not
made twice, an existing PR is found). (ratatoskr #161, #167, #185)

### 7. Agents need to be woken for the next step

After a build merged, nothing told odin, and the whole plan stopped. And when
it was told, it sometimes reported "done" for one step and waited. **Wake the
coordinator after every outcome** (merge, failure, CI stop) **and tell it
plainly to take the next step**; stop only for what only a human can give.
(ratatoskr #169, #184, #189)

### 8. Parallel agents need parallel-safe work

Three wave-2 proposals would have collided on one log file and one root
`package.json`; four failed together on a guard that grepped its own
prohibition in the specs. **Give each stream its own directory and its own
files, and scope checks to what they check** (code, not prose). (convergence
`docs/explanation/log/`)

### 9. Cleanup is part of the job

One afternoon left 168 stale branches across six repositories and seven open
proposal issues for one change. **Delete a run's branches when it ends, turn
on delete-branch-on-merge, and allow one proposal per change in flight.**
(ratatoskr #193, #194)

### 10. Keep the human gates human, and the rest automatic

The pilot's ranking questions are written by a person before any result is
seen, the PII read is a person's, a legal question goes to a lawyer, the
anti-bot challenge of a public site is passed by a real browser, never
solved by script. Everything else, including fixing the factory itself, the
agents and the coding session do without asking. **Decide up front which
gates are human, and do not let them leak in either direction.**

## Also worth knowing

- **Billing is a design decision.** Work on API credits runs on its own key,
  with a ledger and a hard monthly stop; a trimmed environment once lost the
  bus address the sandboxing needed, and every billed session died at start.
  (ratatoskr #179, #167)
- **Measure the artefact, not the claim.** The pilot ingest reads each
  document's audit record back and compares the provenance; it caught a
  silent duplicate path before it could happen.
- **Count everything.** Which agent ran, on which model, with which tools, at
  what cost: one line per run (`docs/how-to/activity.md`). Without it, a loop
  like lesson 1 is invisible until the budget is gone.
- **The coding session makes mistakes too.** It merged a PR with a failing
  docs check (fixed forward), polluted the activity log from its own tests,
  and scaffolded docs the gate rejected. The same rules apply to it:
  checks before merge, every fix with a test.
