---
status: current
last_reviewed: 2026-10-23
---

# Odin has a decided change written

    !propose wordsworth ingest-records-source Provenance at ingest; the published-dossier MVP.

on the **first** line of odin's answer (`agents/propose.py`,
`agents/propose_wiring.py`).

1. **An issue** is opened on the repository (`propose: <id>`).
2. **A writing session** gets a fresh worktree on its own branch, with a
   pre-push fence. It is given the channel's recent messages, which hold the
   decision. It may write **only** under `openspec/changes/<id>/`, and its only
   command is `openspec validate <id> --strict`.
3. **The listener checks the result, not the model.** Every changed path
   must be under that directory, and validation must exit zero. If not, no
   PR, and the issue says why.
4. **PR, CI, merge.** The PR is merged once every check passes, by the same
   follower that merges builds, and it is **not deployed**, because it is
   Markdown.
5. **Odin wakes** with one follow-up turn: "the change is on main, build it",
   and then `!build`.

Why this road: no agent may write to a repository from a chat turn, and
habitat's cage takes no chat text. Chat text reaches a cage only through git,
after review. On 2026-10-23 the decision for wordsworth `ingest-records-source`
had nobody to write it; the coding session wrote it by hand (wordsworth #207).
