---
status: current
last_reviewed: 2026-10-23
---

# Odin has a decided change written

    !propose wordsworth ingest-records-source Provenance at ingest; the published-dossier MVP.

on the **first** line of odin's answer (`agents/propose.py`,
`agents/propose_wiring.py`). The id is lowercase, 3 to 81 characters; the
summary is one line of at most 4000 (raised 2026-10-24: odin's fundament summary for the game ran to 2449 characters and was precise, not padded). A first line that starts with
`!propose` and does not parse is answered with "not understood" (2026-10-24:
two proposals with a 400-character summary were dropped without a word).
Independent changes can be written at once: up to five `!propose` lines as
the first lines of one answer, each its own issue and session (Mark,
2026-10-24: *"if we can do it via graph, go for it"*). Only a leading block
counts; a marker after any other line is quoted text.

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

## Refused writes inside the fence

On 2026-10-24 two amend sessions (wordsworth#214, #218) had every Edit inside
`openspec/changes/<id>/` refused, although the fence allows exactly that, and
the same run again worked. Both had started within a minute of a listener
restart. **Cause, found 2026-10-24 from the debug logs:** the fence was
relative (`Edit(./openspec/changes/<id>/**)`), and `./` resolves against the
session's *current* directory. Every refused session had run
`cd openspec/changes/<id>` first; from there the fence named a path that does
not exist. The fence is now absolute (`Edit(//<worktree>/openspec/changes/<id>/**)`),
proven with a session that `cd`s first, and work sessions' scopes are absolute
the same way (`providers.scoped(..., root=)`). `Write(...)` rules are not
given: Claude Code's file checks only match `Edit(...)`, which covers Write.
The safety net stays as well. The listener now:

- gives each session a debug log in `~/.local/state/ratatoskr/propose-debug/`
  (outside the worktree: `--debug-file` also writes a `latest` symlink, which
  in the worktree failed the fence check, #219) and keeps its stderr in
  `.propose-run.err`;
- counts writes inside the fence that were refused, and when there are any,
  starts the session **once** more with the same decision, saying so on the
  issue;
- names the count in "No PR: …" when the retry is refused too.

## A restart mid-publish

A propose job stays in `state.json` until its publish has finished, so a
listener restart in the middle adopts it and publishes again. Publishing is
idempotent: a change already committed on the session branch is not
committed twice (`check` also counts what the branch has over `origin/main`),
and an existing PR is found from gh's "already exists" answer. On 2026-10-24
a restart cut the convergence `fundament` publish off between commit and
push; the job had already left the state, and the change was stranded until
it was pushed by hand (convergence #8).

## After a build: the next step, and the archive

When a build is merged (and deployed, where its repository has a recipe),
the listener archives the change and wakes the hub with one follow-up turn:
take the assignment's next step. Before 2026-10-24 nothing woke odin after a
build, and the convergence graph stopped after `fundament`.

A change that creates a new capability gets a real Purpose on archive:
openspec writes a "TBD - created by archiving change …" placeholder there,
strict validation refuses it, and `propose_git.fill_purposes` replaces it
with the first sentence of the change's own Why.

When the archive PR merges, every open issue titled `build: <change>` or
`propose: <change>` (the first proposal and any amends) is closed with a
note naming the archive path, so the boards show the change as done and not
as a pile of open proposals.

A change can also leave `openspec/changes/` another way: archived by hand by
a coding session, or split or removed in a PR. A 30-minute tick checks main
itself for every open `build:`/`propose:` issue, detects both cases the same
way as the chain's own archive, and closes the issue the same way. A change
that is gone from `openspec/changes` without an archive directory is never
closed — only logged, so a human decides (`agents/close_on_archive.py`).
