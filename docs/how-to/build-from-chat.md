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

A build ends on a branch. Opening the PR and merging it is phase 2.
