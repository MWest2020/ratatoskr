---
status: current
last_reviewed: 2026-10-22
---

# Build from the chat

Odin starts habitat builds itself (openspec change `odin-runs-the-factory`,
phase 1). You can also start one yourself with the same line.

    !build <repo> <openspec-change> [issue number]

| who | where the line counts |
|---|---|
| odin | only the **first** line of its answer (a quote further down never starts a build) |
| Mark | anywhere in his own message |

## What the listener checks

The listener checks these, not the model. Limits are in `agents/factory.yml`.

1. **The repository is on `repos`.** alma never is.
2. **`openspec/changes/<change>/` exists on that repository's main.** Build
   only what is decided.
3. **Fewer than `max_concurrent` chains are running** (2 since 2026-10-30; it was 1), and today's budget (`builds_per_day`, 10) is
   not used up. The budget guards the agents' loop: a `!build` Mark types
   himself is not counted against it (2026-10-24, when one more build was
   needed after six that each failed on a real, fixed cause). Only a chain
   that reached the builder counts: an architect FAIL takes minutes and spends
   no slot (2026-10-30: five of six slots had gone to them). The circuit
   breaker (`max_builds_per_change_day`, 3 attempts of one change a day without
   a merge) counts every attempt and applies to every build. A build that
   only has to wait (another chain running, the day cap used up, no slot or
   budget headroom yet) is **queued**, not dropped, and starts by itself when
   it may: after the running chain ends, or after midnight.
4. **There is an issue.** Without a number, the listener opens one (`build:
   <change>`, labels `agent-work` and `build`) before anything runs.
5. **A given number is an open issue.** The listener asks `gh`: not a pull
   request, not closed. When it is not, a fresh build issue is opened as in
   (4), and the channel names both the rejected number and the one in use.

A refusal is said in the channel (`⛔ build not started: …`). It is never
silent.

## What happens next

The listener starts `habitat/dispatch/chain.sh` in the background, so the
chat stays free. It runs architect, builder, reviewer and security as Jobs on
the cluster (`ssh jumpy kubectl`, one-year token), with the pinned worker
image. Each role leaves two traces:

- **a comment on the issue,** with PASS or FAIL, the run report's verdict,
  turns and cost, and the branch. A FAIL also lists the role's own findings,
  blocking first, so the hub can decide between a retry and a fix without
  reading the artifacts (2026-10-23: odin saw only "verdict failed"). A
  verdict without findings, like the architect's, shows its summary and
  risks instead;
- **a line in the channel the build came from:** `✅ architect: PASS …`,
  `❌ builder: FAIL …`, `🏁 Chain passed …`.

The run file with the chain's whole output is in
`~/.local/state/ratatoskr/builds/`. The roles' artifacts are in
`~/.local/state/habitat/run-logs/artifacts/`.

## After the chain: PR and merge

When all four roles pass:

1. **The PR.** The listener opens a PR from the builder branch. Its body
   carries `Closes #<issue>` and the four verdicts.
2. **The checks.** About once a minute the listener reads the PR's checks
   (`gh pr checks --json bucket`):
   - **merge** when nothing is failing, cancelled or pending and at least one
     check passed;
   - **wait** while anything is pending. Zero checks also waits, because
     nothing verified the branch;
   - **stop** on a failing or cancelled check, naming it on the issue and in
     the channel, with the failing lines from the check's log. The stop also
     wakes the hub to decide: rebuild, amend the change (`!propose`, same id),
     or tell Mark (2026-10-24: wordsworth#217 passed every role, failed one
     test in CI, and nobody who could act was told).
3. **The merge closes the issue.**

Mark decided this on 2026-10-22 ("absolutely"). alma is not a repository on
the list, so it is never merged into.

## A restart loses nothing

Running chains and PRs waiting for CI are kept in
`~/.local/state/ratatoskr/builds/state.json`. That covers the pid, how many
events were already reported, and the PR number. After a listener restart
(every deploy), it goes on from there without repeating a comment. A chain
that ended while the listener was down is closed with what its run file says.

The chain itself survives the restart too. It runs in its own transient scope
(`systemd-run --user --scope`, see `agents/detach.py`), because the unit's
`KillMode=control-group` otherwise stops every child with the listener; that
is how the first propose-road build died on 2026-10-23. Propose sessions run
the same way. A scoped child needs `XDG_RUNTIME_DIR` and the D-Bus address to
reach the user bus, so `detach.env()` adds those two (and nothing else) to a
trimmed agent environment. Without them, `systemd-run` failed before claude
ran (2026-10-24, wordsworth#211), and a run file with no output now reads "the
session never ran" instead of "wrote nothing". A chain that has ended leaves the running list before its
failure is reported, so the hub's retry is not refused as "another build is
still running".

A chain that passes every role but leaves no commits (the change needed only a
spec amend that is already merged) has nothing to merge: the listener comments
that on the issue and archives the change, as after a merge (2026-10-31:
convergence demo-zone-travel stalled on "No commits between").

## After the merge: deploy to the homelab

For a repository with a recipe under `deploy:` in `agents/factory.yml`
(wordsworth and convergence), the merge does not end there. The listener takes one step
per round, with each step on the issue and in the channel (`🚚`, then `🚀` or
`⛔`):

| step | what happens |
|---|---|
| image | wait for the image(s) of the merge commit (`sha-<7>`, up to 45 min), read each digest from GitHub's package API |
| push | bump every digest in **every** manifest of the recipe (wordsworth: api **and** init-job, otherwise the migrations do not run), commit to homelab main, push |
| sync | `argocd.argoproj.io/refresh=hard` on the Application, over `ssh jumpy` |
| verify | every image of the recipe runs its new digest, matched by image name, and the rollout is complete (up to 20 min) |

The bump is all or nothing: if one manifest has no line to bump, or one image
of the recipe is in no manifest, nothing is written and the deploy stops.

A recipe names one image (`package` and `image`, wordsworth) or several
(`images:`, a list of `{package, image}`: convergence builds a server and a
web image from one commit). Several images deploy together or not at all:
the deploy waits until every one has the merge commit's tag. A manifest line
may pin a tag before the digest (`<image>:sha-<7>@sha256:…`); the tag is
rewritten with the digest, so the two never name different commits. The deployer works in its own homelab worktree
(`~/.worktrees/homelab-deploy`), never in a shared checkout.

When the deploy is done, odin is woken in the channel the build started in,
to take the next step. The deploy keeps that channel for it; until 2026-10-27
it did not, and odin woke in no channel and stopped after demo-zone-rules.

**alma is never a target.** It is in no recipe, and a manifest path outside
`cluster-config/infra/`, or one that names alma, makes the recipe invalid.

## Budget, and when a role fails

Each role run gets `max_budget_usd` from `agents/factory.yml` (15 dollars),
passed as `HABITAT_MAX_BUDGET_USD`. Habitat's own default of 5 dollars was too
tight for a real change. On 2026-10-23 wordsworth's builder stopped at it after
86 turns (`error_max_budget_usd`) with most of the change already pushed.

When a role fails:

- **The issue comment names the stop reason** from the run report
  ("stopped by `error_max_budget_usd`"), not only FAIL.
- **Odin gets one follow-up turn** to start the build again if the cause is
  gone, or to tell Mark what blocks it. `builds_per_day` caps the retries.

## After the deploy: the change is archived

When a change is merged and, for a repository with a deploy recipe,
deployed, the listener archives it by the same road. It makes a fresh fenced
worktree, runs `openspec archive <id> -y` and `openspec validate --specs
--strict`, then a PR, and merges it once CI passes. That PR is not deployed and
wakes nobody. On 2026-10-23 odin noticed that `ingest-records-source` was
deployed but not archived; the coding session archived it by hand (wordsworth
#210). Now the chain does it.

## The factory tidies up after itself

Mark, 2026-10-24: *"too many branches ... I expect this to be handled without
human intervention."*

- **A chain's branches** (`agents/branches.py`): a chain that passed keeps only
  its builder branch, the PR's head, which the repository's
  delete-branch-on-merge setting removes on merge (on for every factory repo
  since 2026-10-24); a chain that failed keeps only its builder branch, so the
  work survives a failure after the builder (a lost builder branch cost the
  demo-slice a full rebuild); when the change is archived, every habitat
  branch it left goes. Only branches
  the chain's own run file names are deleted, never `main`.
- **One proposal per change**: a `!propose` for a change already being written
  or waiting in CI is answered, not started; an amend or retry comments on the
  open `propose: <change>` issue instead of opening another.
- **Issues of an archived change close by themselves**: a 30-minute tick reads
  `openspec/changes` and its archive on each repository with an open
  `build:`/`propose:` issue, and closes the issue with the archive path once
  the change is archived there — whether that happened through the chain's
  own archive PR or by hand. No snapshot is kept, so a restart loses nothing
  and a hand-archive is found the same way. A change that is gone without an
  archive directory (a split, a removal) is only logged, never closed: a
  wrong close is worse than a missed one (`agents/close_on_archive.py`).

## Where the roles come from

Every habitat role (architect, builder, reviewer, security) is read from the
handbook, `docs/agents/seeds/<role>.md`, at the commit `handbook_ref` in
`agents/factory.yml` pins (habitat #44, handbook #35). One source for every
project; a repository's own `.claude/agents/` is no longer used. To roll out a
role change: merge it in the handbook, then move `handbook_ref`. A pinned commit
without a seed for a role stops that role's run; it never falls back.
