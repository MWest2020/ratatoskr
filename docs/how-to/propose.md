---
status: current
last_reviewed: 2026-10-23
---

# Odin has a decided change written

    !propose wordsworth ingest-records-source Provenance at ingest; the published-dossier MVP.

on the **first** line of odin's answer (`agents/propose.py`,
`agents/propose_wiring.py`). The id is lowercase, 3 to 81 characters; the
summary is one line of at most 1500. A first line that starts with
`!propose` and does not parse is answered with "not understood" (2026-10-24:
two proposals with a 400-character summary were dropped without a word).

1. **An issue** is opened on the repository (`propose: <id>`).
2. **A writing session** gets a fresh worktree on its own branch, with a
   pre-push fence. It is given the channel's recent messages, which hold the
   decision. It may write **only** under `openspec/changes/<id>/`, and its only
   command is `openspec validate <id> --strict`. When the change touches
   code, its tasks must name the docs that change with it. The repos gate on
   docs drift, and the first propose-road build was failed by its reviewer
   for exactly that gap.
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

## A restart loses nothing

A running propose session is kept in `~/.local/state/ratatoskr/builds/state.json`
with its pid, worktree, branch and issue, like builds and merges. After a
listener restart (every deploy) the listener adopts it and still publishes its
PR when it finishes. On 2026-10-23 a factory test had to wait for exactly that
reason.

## A failed read is never "nothing written"

On 2026-10-23 the first live propose session wrote its four files, and the
listener reported "the session wrote nothing". `git status` had failed in the
worktree with "must be run in a work tree": `~/ratatoskr` carries
`core.bare=true`, and its empty stdout was read as an empty result. Two fixes:

- **A failing `git status` is now an error with its reason.**
- **Every session worktree gets `core.bare=false`** in its own worktree
  config (`agents/work_tree.py`).

## Amending a change

The same marker with an id that already exists on main amends that change
instead of being refused. Use it when a build stops on something that belongs
in the change: an open question the architect settled, or reviewer findings
the next builder must see. A retry rebuilds from main, so a finding that is
only on the issue never reaches the next builder. The summary carries the
decision and the findings; the session edits the change in place
(`openspec/changes/<id>/` only, as always), and the PR is titled
`openspec: amend <id>`. After the merge odin is woken to build again.

2026-10-24, wordsworth `pilot-ingest-manifest`: the reviewer failed the first
build (scratch files committed, a file over the line limit), the retry's
architect stopped on an open question it had answered but could not write
down, and odin had no road but asking Mark. The git half of the road moved to
`agents/propose_git.py` for the line limit.
