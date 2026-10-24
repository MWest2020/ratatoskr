# SPDX-License-Identifier: MIT
"""`!propose <repo> <change-id> <one line>`: a decided change gets written.

2026-10-23: odin, architect and reviewer decided `ingest-records-source` for
wordsworth in #general, and then nobody could write it. No agent may write to a
repository from a chat turn, and habitat's cage takes no chat text. The coding
session had to write the change by hand.

The propose road: the listener starts a WRITING session in a fresh worktree of
the repository (work_tree.py: its own branch and a pre-push fence). It is told
the decision (the channel's recent messages) and may write ONLY under
`openspec/changes/<change-id>/`, with `openspec validate` as its only command.
Then the listener, not the model, checks the result:

- every changed path is under that directory;
- `openspec validate <id> --strict` passes, by its exit code;

and it commits, pushes the branch and opens a PR. That PR is merged once CI
agrees, by the same road as a build (build_wiring). Chat text reaches a cage
only through git, after review, which is what the habitat-bridge spec says.
"""
import json
import os
import subprocess

import credits
import detach
import providers
import work_tree
from propose_git import BASE, archive, publish  # noqa: F401  (the wiring imports them from here)
from propose_run import cost, refused_writes  # noqa: F401  (same)
from propose_marker import (FANOUT, MARKER, read_marker, read_markers,  # noqa: F401
                            strip_markers, unread)

MAX_S = 900
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
DEBUG_DIR = os.path.expanduser("~/.local/state/ratatoskr/propose-debug")

SYSTEM = """You write ONE OpenSpec change, decided in a chat channel, and nothing else.
Write only under openspec/changes/{cid}/: proposal.md (why, in the people's own
words where quoted, and what changes), design.md (choices and rejected
alternatives), tasks.md (each task names the test or check that proves it) and
specs/<capability>/spec.md with ## ADDED/MODIFIED Requirements in the repo's
style (read openspec/specs/ first; a MODIFIED requirement keeps its existing
scenarios). When the change touches code, tasks.md also names the docs that
describe that behaviour and must change with it (find them with Grep under
docs/; repos here fail CI on code without docs). Write only what was decided; anything open goes into the proposal
as an open question, never as a requirement. Finish by running
`openspec validate {cid} --strict` and fix it until it passes. Do not commit or
push: the listener does that after checking your files."""


AMEND = ("This change ALREADY EXISTS on main: AMEND it in place. Keep what was "
         "decided; settle the open questions the summary settles; fold the named "
         "findings into tasks.md as tasks with their proof. Change nothing else.\n")


def tools(cid, wt=None):
    """Edit fenced to the change's own directory; one command.

    The fence is ABSOLUTE when the worktree is known (2026-10-24, found from
    the debug logs): `./` resolves against the session's CURRENT directory,
    and every refused amend had run `cd openspec/changes/<id>` first, after
    which `./openspec/changes/<id>/**` named a path that does not exist.
    `Edit` rules cover Write too; a `Write(path)` rule is ignored by Claude
    Code's file checks, so it is not given."""
    base = f"/{os.path.normpath(wt)}" if wt else "."
    return ["Read", "Grep", "Glob", f"Edit({base}/openspec/changes/{cid}/**)",
            f"Bash(openspec validate {cid} --strict)"]


def transcript(msgs, pub2name, n=14):
    """The decision as the channel holds it: the last messages, with authors."""
    out = []
    for m in (msgs or [])[-n:]:
        who = pub2name.get(m.get("pubkey"), "someone")
        out.append(f"--- {who}:\n{(m.get('content') or '').strip()[:4000]}")
    return "\n".join(out)


def start(clone, cid, summary, msgs, pub2name, requester, popen=subprocess.Popen,
          create=work_tree.create):
    """(job, "") or (None, reason). The job holds the worktree, branch and process."""
    try:
        wt, branch = create(clone, BASE, f"propose-{cid}", requester)
    except Exception as e:
        return None, f"no worktree: {str(e)[:160]}"
    # 2026-10-24: an existing change is amended, not refused. Its first build
    # stopped on an open question and on reviewer findings, and nothing could
    # put the answers into the change the next build reads.
    amend = os.path.isdir(os.path.join(wt, "openspec", "changes", cid))
    prompt = (f"Change id: {cid}\n" + (AMEND if amend else "")
              + f"What was decided, in one line: {summary}\n\n"
              f"The channel, oldest first:\n{transcript(msgs, pub2name)}")
    out = open(os.path.join(wt, ".propose-run.jsonl"), "w")
    # a debug log and stderr: the refusals of 2026-10-24 came without a reason
    err = open(os.path.join(wt, ".propose-run.err"), "w")
    # outside the worktree: --debug-file also writes a `latest` symlink beside
    # the log, and in the worktree that is a file outside the fence (#219)
    debug = os.path.join(DEBUG_DIR, os.path.basename(os.path.normpath(wt)) + ".log")
    os.makedirs(DEBUG_DIR, exist_ok=True)
    env = detach.env(providers.agent_env())
    if credits.repo_billed(os.path.basename(os.path.normpath(clone))):
        env = credits.env(env)                  # this repo runs on the API credits
    proc = popen(detach.argv([CLAUDE, "-p", "--debug-file", debug,
                  "--output-format", "stream-json", "--verbose",
                  "--permission-mode", "dontAsk", "--model", "sonnet",
                  "--append-system-prompt", SYSTEM.format(cid=cid),
                  "--allowedTools", ",".join(tools(cid, wt)),
                  "--disallowedTools", "Task,KillShell,WebFetch,WebSearch"], env=env),
                 stdin=subprocess.PIPE, stdout=out, stderr=err, text=True,
                 cwd=wt, env=env, start_new_session=True)
    out.close()
    err.close()
    proc.stdin.write(prompt)
    proc.stdin.close()
    return {"amend": amend, "wt": wt, "branch": branch, "change": cid, "proc": proc,
            "summary": summary}, ""


def check(job, run=subprocess.run):
    """'' when the worktree holds a valid change and nothing else, else why not."""
    wt, cid = job["wt"], job["change"]
    g = run(["git", "-C", wt, "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True)
    if g.returncode != 0:
        # 2026-10-23: this failed ("must be run in a work tree") and its empty
        # stdout was read as "wrote nothing"; a failed read is never an empty one.
        return "git status failed: " + (g.stderr or g.stdout).strip()[-200:]
    st = g.stdout
    paths = [ln[3:] for ln in st.splitlines() if ln.strip()
             and not ln[3:].startswith(".propose-run")]
    # and what is already committed on the session branch: a restart can cut a
    # publish off after its commit (2026-10-24, convergence fundament)
    base = run(["git", "-C", wt, "merge-base", "HEAD", "origin/main"], capture_output=True, text=True)
    if base.returncode == 0 and base.stdout.strip():
        d = run(["git", "-C", wt, "diff", "--name-only", base.stdout.strip(), "HEAD"],
                capture_output=True, text=True)
        paths += [x for x in d.stdout.splitlines() if x.strip() and x not in paths]
    if not paths:
        try:
            ran = os.path.getsize(os.path.join(wt, ".propose-run.jsonl")) > 0
        except OSError:
            ran = False
        # 2026-10-24: a session that never started read as one that wrote nothing
        return "the session wrote nothing" if ran else "the session never ran (no output at all)"
    stray = [p for p in paths if not p.startswith(f"openspec/changes/{cid}/")]
    if stray:
        return f"files outside openspec/changes/{cid}/: {stray[:5]}"
    v = run(["openspec", "validate", cid, "--strict"], cwd=wt, capture_output=True, text=True)
    if v.returncode != 0:
        return "openspec validate failed: " + (v.stdout + v.stderr).strip()[-300:]
    return ""


def clause(handle, hub):
    if handle != hub:
        return ""
    return ("\n\nWhen a change is DECIDED (with architect/reviewer where it matters) but "
            "not yet written, have it written: `!propose <repo> <change-id> <what was "
            "decided, one line>` on the FIRST line of your answer. A writing session "
            "turns this channel's decision into an OpenSpec change; the listener checks "
            "it, opens a PR, merges it once CI passes, and then wakes you to build it. "
            "The same marker with an EXISTING change id amends that change: use it when a "
            "build stopped on an open question or on findings that belong in the change "
            "(put the decision and the findings in the summary), then build again. "
            f"Independent changes can be written at once: up to {FANOUT} `!propose` lines, "
            "one per line, as the first lines of your answer.")
