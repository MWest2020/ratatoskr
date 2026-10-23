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
3. **No other chain is running,** and today's budget (`builds_per_day`) is
   not used up.
4. **There is an issue.** Without a number, the listener opens one (`build:
   <change>`, labels `agent-work` and `build`) before anything runs.

A refusal is said in the channel (`⛔ build not started: …`). It is never
silent.

## What happens next

The listener starts `habitat/dispatch/chain.sh` in the background, so the
chat stays free. It runs architect, builder, reviewer and security as Jobs on
the cluster (`ssh jumpy kubectl`, one-year token), with the pinned worker
image. Each role leaves two traces:

- **a comment on the issue,** with PASS or FAIL, the run report's verdict,
  turns and cost, and the branch;
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
     the channel.
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
the same way. A chain that has ended leaves the running list before its
failure is reported, so the hub's retry is not refused as "another build is
still running".

## After the merge: deploy to the homelab

For a repository with a recipe under `deploy:` in `agents/factory.yml`
(wordsworth so far), the merge does not end there. The listener takes one step
per round, with each step on the issue and in the channel (`🚚`, then `🚀` or
`⛔`):

| step | what happens |
|---|---|
| image | wait for the image of the merge commit (`sha-<7>`, up to 45 min), read its digest from GitHub's package API |
| push | bump that digest in **every** manifest of the recipe (wordsworth: api **and** init-job, otherwise the migrations do not run), commit to homelab main, push |
| sync | `argocd.argoproj.io/refresh=hard` on the Application, over `ssh jumpy` |
| verify | the deployment runs the new digest and its rollout is complete (up to 20 min) |

The bump is all or nothing: if one manifest has no line to bump, nothing is
written and the deploy stops. The deployer works in its own homelab worktree
(`~/.worktrees/homelab-deploy`), never in a shared checkout.

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
