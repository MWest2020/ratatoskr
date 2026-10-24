---
status: current
last_reviewed: 2026-10-24
---

# Project boards

Mark, 2026-10-24: *"perhaps we need to update a board on my github repo ...
to monitor status on it as well. can be done on the individual project, like
wordsworth and the new game."*

Each project has a GitHub Project board, listed in `agents/factory.yml`
`boards:` (`wordsworth` → project 1, `convergence` → project 2). The Status
column holds the factory's stages: Todo, Writing change, Building, CI,
Deployed, Done, Blocked.

**The listener moves the cards.** `agents/board.py` is called from
`issues.create` and `issues.comment`. Every issue the listener opens and every
comment it writes already marks a stage, so no wiring module changes:

| what the listener writes | stage |
|---|---|
| a `propose:` issue | Writing change |
| any other new issue | Todo |
| "Build started …" | Building |
| "PR #n opened …" | CI |
| a role's FAIL, "Not merged", "No PR", "Not deployed", … | Blocked |
| "Merged PR #n …" | Done if the merge closed the issue (a build), Todo if it stayed open (a proposal, next to be built) |
| "Deployed to the homelab …" | Deployed |

The gh calls run in a detached child, so a slow API never holds up the
listener. Field and option ids are cached in
`~/.local/state/ratatoskr/board-fields.json`; delete that file after changing
a board's columns.

The projects' built-in "Item closed" workflow is off and cannot be enabled
through the API, so Done is set by the listener as well. The `gh` token
needs the `project` scope (granted 2026-10-24).

A new board: `gh project create --owner MWest2020 --title <repo>`, link it
(`gh project link <n> --repo MWest2020/<repo>`), set the Status options, and
add `<repo>: <n>` to `boards:`.
