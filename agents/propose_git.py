# SPDX-License-Identifier: MIT
"""The propose road's git half: publish a written change, archive a done one.
Split from propose.py (line limit) on 2026-10-24, when amending was added."""
import os
import re
import subprocess

import work_tree

BASE = os.path.expanduser("~/.worktrees/propose")


def publish(job, repo, owner, run=subprocess.run):
    """Commit, push the session branch, open the PR. (pr number, error)."""
    wt, cid = job["wt"], job["change"]
    verb = "amend " if job.get("amend") else ""
    steps = [["git", "-C", wt, "add", f"openspec/changes/{cid}"],
             ["git", "-C", wt, "-c", "user.name=MWest2020", "-c",
              "user.email=mwest2020@hotmail.com", "commit", "-q", "-m",
              f"openspec: {verb}{cid}\n\n{job['summary']}\n\nWritten by a propose session on "
              "odin's decision (ratatoskr agents/propose.py)."],
             ["git", "-C", wt, "push", "-q", "-u", "origin", job["branch"]]]
    for argv in steps:
        p = run(argv, capture_output=True, text=True)
        if p.returncode != 0:
            return 0, (p.stderr or p.stdout).strip()[-200:]
    p = run(["gh", "pr", "create", f"--repo={owner}/{repo}", f"--head={job['branch']}",
             "--base=main", f"--title=openspec: {verb}{cid}",
             f"--body={job['summary']}\n\nWritten by a propose session on odin's decision; "
             "the listener merges it once every check passes."], capture_output=True, text=True)
    m = re.search(r"/pull/(\d+)", p.stdout)
    return (int(m.group(1)), "") if m else (0, (p.stderr or p.stdout).strip()[-200:])


def archive(clone, repo, owner, change, create=work_tree.create, run=subprocess.run):
    """Archive a built, merged and (where there is a recipe) deployed change, in
    a fresh fenced worktree; commit, push, PR. (pr number, error)."""
    try:
        wt, branch = create(clone, BASE, f"archive-{change}", "listener")
    except Exception as e:
        return 0, f"no worktree: {str(e)[:160]}"
    steps = [["openspec", "archive", change, "-y"],
             ["openspec", "validate", "--specs", "--strict"],
             ["git", "add", "-A", "openspec"],
             ["git", "-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com",
              "commit", "-q", "-m", f"openspec: archive {change}\n\nBuilt, merged and "
              "deployed by the factory (ratatoskr agents/propose.py)."],
             ["git", "push", "-q", "-u", "origin", branch]]
    for argv in steps:
        p = run(argv, cwd=wt, capture_output=True, text=True)
        if p.returncode != 0:
            return 0, f"{' '.join(argv[:2])}: {(p.stderr or p.stdout).strip()[-200:]}"
    p = run(["gh", "pr", "create", f"--repo={owner}/{repo}", f"--head={branch}", "--base=main",
             f"--title=openspec: archive {change}",
             "--body=The change is built, merged and deployed; archived by the listener."],
            cwd=wt, capture_output=True, text=True)
    m = re.search(r"/pull/(\d+)", p.stdout)
    return (int(m.group(1)), "") if m else (0, (p.stderr or p.stdout).strip()[-200:])
