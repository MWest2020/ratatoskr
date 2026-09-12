# SPDX-License-Identifier: EUPL-1.2
"""A fresh git worktree for a writing work session, with a fence in it.

Why a worktree of its own: `~/ratatoskr-listener` runs the listener and the chat
runs from an image. A session writing in a running checkout rebuilds itself while
it works. Two listeners once ran because a restart came out of two different
trees — you do not want that kind of confusion per session as well.

Why a pre-push hook and not a sentence in the prompt: a writing session gets
`Bash` (no git and no tests otherwise), and then "do not push to main" in a prompt
is worth nothing. Anything entering its context — a README, an issue, a fetched
page — can steer that instruction. A hook cannot be steered.
"""
import os
import subprocess
import time

# The fence. `git push` passes every ref on stdin as "<local> <sha> <remote>
# <sha>"; anything not going to its own branch is refused. `main` explicitly too,
# so the message is clear instead of a generic rejection.
HOOK = """#!/bin/sh
# Written by agents/work_tree.py. A writing work session may only push its OWN
# branch: that keeps a pull request the only outcome.
allowed="refs/heads/%s"
while read -r _local _lsha remote _rsha; do
    [ -z "$remote" ] && continue
    if [ "$remote" != "$allowed" ]; then
        echo "pre-push: geweigerd — deze sessie mag alleen $allowed pushen," >&2
        echo "          niet $remote. Open een pull request." >&2
        exit 1
    fi
done
exit 0
"""


def branch_name(session_type, requester, now=None):
    """Recognisable and unique: type, who asked, when."""
    stamp = int(now or time.time())
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in requester)[:24]
    return f"session/{session_type}-{safe or 'unknown'}-{stamp}"


def _run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(" ".join(args[:3]) + ": " + (p.stderr or p.stdout).strip()[:200])
    return p.stdout


def install_hook(worktree, branch):
    """Put the hook in a hooks directory of THIS worktree.

    Why not plain `.git/hooks`: that is the SHARED directory of the whole clone.
    Measured 2026-09-12, painfully: a session's hook therefore blocked my own push
    from another worktree of the same clone — "deze sessie mag alleen
    refs/heads/session/… pushen". Two sessions would also overwrite each other's
    hook.

    Git has a mechanism for this: `extensions.worktreeConfig` sets
    `core.hooksPath` per worktree instead of for the whole repo.
    """
    own = os.path.join(worktree, ".session-hooks")
    os.makedirs(own, exist_ok=True)
    _run(["git", "-C", worktree, "config", "extensions.worktreeConfig", "true"])
    _run(["git", "-C", worktree, "config", "--worktree", "core.hooksPath", own])
    path = os.path.join(own, "pre-push")
    with open(path, "w") as f:
        f.write(HOOK % branch)
    os.chmod(path, 0o755)
    # Not committed along: the fence belongs to the session, not to the branch. In
    # a worktree `.git` is a FILE, not a directory — so ask git for the path.
    exclude = _run(["git", "-C", worktree, "rev-parse", "--git-path",
                    "info/exclude"]).strip()
    if not os.path.isabs(exclude):
        exclude = os.path.join(worktree, exclude)
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with open(exclude, "a") as f:
        f.write("\n.session-hooks/\n")
    return path


def create(repo, base_dir, session_type, requester, now=None):
    """(worktree, branch). Fresh from `origin/main`, with the fence in it.

    `repo` is an existing clone; the worktree goes into `base_dir`, outside every
    running checkout. If anything fails this raises — half a worktree is worse
    than none.
    """
    branch = branch_name(session_type, requester, now)
    target = os.path.join(base_dir, branch.replace("/", "-"))
    os.makedirs(base_dir, exist_ok=True)
    _run(["git", "-C", repo, "fetch", "--quiet", "origin", "main"])
    _run(["git", "-C", repo, "worktree", "add", "-q", "-b", branch, target, "origin/main"])
    install_hook(target, branch)
    return target, branch
