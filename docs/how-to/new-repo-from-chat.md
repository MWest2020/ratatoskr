---
status: current
last_reviewed: 2026-11-07
---

# A new repository from the chat

    !newrepo <name> <one-line description>

Mark, 2026-11-07: "odin moet dat wel kunnen". The bubbels2 experiment (the
factory builds a game from the same brief a coding session got) stalled at
step one, because nothing in the factory could create a repository.

| who | where the line counts |
|---|---|
| odin | only the **first** line of its answer |
| Mark | anywhere in his own message |

Odin may put `!propose` lines straight under it: the listener handles the
`!newrepo` line first (`agents/agent_turn.py`), so one answer can create the
repository and start writing its first changes.

## What the listener checks (`agents/newrepo.py`)

1. The name is 2-100 characters of letters, digits, `.`, `_`, `-`; it is not
   `alma` and holds no `conduction`.
2. **The repository does not exist.** If GitHub cannot be asked, that is a
   refusal too, never a guess.
3. **At most `new_repos_per_day`** (`agents/factory.yml`, 2) per calendar day.

A refusal is said in the channel (`⛔ repo not created: …`).

## What it does

- **`gh repo create MWest2020/<name> --private`.** Always private: making a
  repository public is Mark's decision, by hand.
- **Bootstrap from `agents/templates/newrepo/`**, pushed over **SSH** (the gh
  OAuth token has no `workflow` scope; SSH pushes are not limited by it):
  README, MIT LICENSE, AGENTS.md, `openspec/` (config, changes, specs),
  `docs/index.md`, `docs/reference/roadmap.yml`, `verify.sh` and the workflows
  `verify` (runs `bash verify.sh`) and `docs-gates`. The merge follower needs
  at least one passing check, so a new repo has one from the start. Habitat
  builders cannot change workflow files (their token has no `workflow` scope
  either); they extend `verify.sh` instead.
- **The labels** `agent-work`, `propose`, `build`, `waiting-on-mark`, because
  the build and propose roads put them on their issues.
- **A local clone in `~/<name>`**, because the propose road writes in a
  worktree of it.
- **On the factory's list.** The name is recorded in
  `~/.local/state/ratatoskr/created_repos.json`, and every recorded name joins
  `repos` and `readable` at start-up and right after the create
  (`merge_known`). `factory.yml` itself is not widened, and odin still cannot
  add an *existing* repository: only a successful create writes the file.
- A line `📦 repo created: MWest2020/<name> (private) …` and a row in the
  activity log (`kind: newrepo`).

When the create works but a later step fails (for example the push), the
repository is still recorded as ours and the line says what is missing.

## Habitat

The worker clones and pushes over HTTPS with `GIT_PAT` from the Secret
`pat-node-01`: an OAuth token with the `repo` scope, so it reaches every
repository of the account, a brand-new private one included. Checked
2026-11-07; nothing to change there.
