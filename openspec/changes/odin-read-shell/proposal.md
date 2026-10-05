# Odin reads the state of the work itself

## Why

Mark in #architectuur, 2026-10-05:

- *"@odin , kun jij supervisen of het goedkomt? Updates in #general aub"*
- *"@odin ja, en straks met shell moet je dat wel kunnen"*
- *"@odin hoe ver weg zijn we van jou en een shell?"*

Odin answered that it can only read the deployed listener tree, and that the
state of the work (commits, branches, open changes, PRs, issues, checks) lives
on GitHub, out of its reach. Its own estimate was "a small, well-bounded
read-only shell", and it named the trap itself: a free shell.

## What changes

- **A read shell**: `agents/readshell.py`, a fixed set of six read-only GitHub
  lookups for a repository of `MWest2020`. These are `log`, `branches`,
  `changes`, `prs`, `issues` and `checks`.
- **One Bash rule**: a chat agent may hold exactly
  `Bash(python3 agents/readshell.py:*)` and no other Bash. The listener
  refuses to spawn an agent whose chat facet allows any other Bash entry.
  This is fail-closed, like a missing model.
- **The agent is told**: when its definition allows the read shell, the
  system prompt says so, generated from the definition. This follows the same
  pattern as `session_clause` and `route_clause`, because a capability the
  model is not told about does not exist for it.
- **The mandate is Mark's**: odin gets the rule through its handbook
  definition (`docs/agents/odin.md`). That is a handbook PR, and Mark merges it.
  Until then this change is inert: no agent declares the rule.

## Out of scope

- **Writing.** No push, comment, merge or label. Odin's own estimate was right
  that write access "touches the cage invariants" and is a different decision.
- **A wake-up.** Odin stays reactive; it reads when someone mentions it.
  Periodic supervision needs a trigger, which is a separate change.
- **Posting in #general on its own.** Unchanged.
