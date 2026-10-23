# SPDX-License-Identifier: MIT
"""A read-only worktree of handbook main for work sessions.

2026-10-23: Mark told odin "read the wordsworth and handbook documentation";
the wordsworth session could not, because its read permit stopped at the repo,
and ~/handbook was 14 commits behind anyway. Sessions now read
`~/.worktrees/handbook-read/docs` (sessions.yml `also_reads`), and this module
moves that worktree to origin/main before every session starts.
"""
import os
import subprocess

REPO = os.path.expanduser("~/handbook")
PATH = os.path.expanduser("~/.worktrees/handbook-read")


def refresh(repo=REPO, path=PATH, run=subprocess.run):
    """"" when the worktree is on handbook main, else the reason it is not."""
    steps = [["git", "-C", repo, "fetch", "-q", "origin"]]
    if os.path.isdir(path):
        steps.append(["git", "-C", path, "checkout", "-q", "-f", "--detach", "origin/main"])
    else:
        steps.append(["git", "-C", repo, "worktree", "add", "-q", "--detach", path,
                      "origin/main"])
    for argv in steps:
        try:
            p = run(argv, capture_output=True, text=True, timeout=60)
        except (subprocess.TimeoutExpired, OSError) as e:
            return f"{argv[3]}: {e}"
        if p.returncode != 0:
            return (p.stderr.strip().splitlines() or ["git failed"])[-1][:160]
    return ""
