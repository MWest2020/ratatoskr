# SPDX-License-Identifier: MIT
"""The propose road's git half: publish a written change, archive a done one.
Split from propose.py (line limit) on 2026-10-24, when amending was added."""
import glob
import os
import re
import subprocess

import work_tree

BASE = os.path.expanduser("~/.worktrees/propose")


def publish(job, repo, owner, run=subprocess.run):
    """Commit, push the session branch, open the PR. (pr number, error)."""
    wt, cid = job["wt"], job["change"]
    verb = "amend " if job.get("amend") else ""
    # Idempotent, because a restart can cut it off anywhere (2026-10-24): an
    # existing commit is not made again, and an existing PR is found, not failed on.
    p = run(["git", "-C", wt, "add", f"openspec/changes/{cid}"], capture_output=True, text=True)
    if p.returncode != 0:
        return 0, (p.stderr or p.stdout).strip()[-200:]
    staged = run(["git", "-C", wt, "diff", "--cached", "--quiet"], capture_output=True, text=True)
    steps = [["git", "-C", wt, "-c", "user.name=MWest2020", "-c",
              "user.email=mwest2020@hotmail.com", "commit", "-q", "-m",
              f"openspec: {verb}{cid}\n\n{job['summary']}\n\nWritten by a propose session on "
              "odin's decision (ratatoskr agents/propose.py)."]] if staged.returncode else []
    steps.append(["git", "-C", wt, "push", "-q", "-u", "origin", job["branch"]])
    for argv in steps:
        p = run(argv, capture_output=True, text=True)
        if p.returncode != 0:
            return 0, (p.stderr or p.stdout).strip()[-200:]
    p = run(["gh", "pr", "create", f"--repo={owner}/{repo}", f"--head={job['branch']}",
             "--base=main", f"--title=openspec: {verb}{cid}",
             f"--body={job['summary']}\n\nWritten by a propose session on odin's decision; "
             "the listener merges it once every check passes."], capture_output=True, text=True)
    m = re.search(r"/pull/(\d+)", p.stdout + p.stderr)   # "already exists" names the PR too
    return (int(m.group(1)), "") if m else (0, (p.stderr or p.stdout).strip()[-200:])


PLACEHOLDER = re.compile(r"^TBD - created by archiving change (\S+)\. Update Purpose after archive\.$",
                         re.M)


def fill_purposes(wt, change):
    """A capability the change created gets a real Purpose, from the change's
    own Why. 2026-10-24, convergence fundament: openspec writes a "TBD"
    placeholder for a new capability, and strict validation refuses it, so
    every change that created a capability failed to archive."""
    why = ""
    for path in glob.glob(os.path.join(wt, "openspec", "changes", "archive", f"*-{change}",
                                       "proposal.md")):
        text = open(path).read()
        m = re.search(r"^## Why\s*\n+(.+?)(?:\n\n|$)", text, re.M | re.S)
        if m:
            first = " ".join(m.group(1).split())
            why = re.split(r"(?<=[.!?])\s", first, maxsplit=1)[0]
    line = (f"Created by the change `{change}`. {why}".strip() if why
            else f"Created by the change `{change}`; see its archived proposal.")
    for spec in glob.glob(os.path.join(wt, "openspec", "specs", "*", "spec.md")):
        text = open(spec).read()
        if PLACEHOLDER.search(text):
            open(spec, "w").write(PLACEHOLDER.sub(line, text))


def archive(clone, repo, owner, change, create=work_tree.create, run=subprocess.run):
    """Archive a built, merged and (where there is a recipe) deployed change, in
    a fresh fenced worktree; commit, push, PR. (pr number, error)."""
    try:
        wt, branch = create(clone, BASE, f"archive-{change}", "listener")
    except Exception as e:
        return 0, f"no worktree: {str(e)[:160]}"
    p = run(["openspec", "archive", change, "-y"], cwd=wt, capture_output=True, text=True)
    if p.returncode != 0:
        return 0, f"openspec archive: {(p.stderr or p.stdout).strip()[-200:]}"
    fill_purposes(wt, change)
    steps = [["openspec", "validate", "--specs", "--strict"],
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
