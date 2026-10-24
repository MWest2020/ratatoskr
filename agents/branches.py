# SPDX-License-Identifier: MIT
"""A finished chain takes its branches with it.

Mark, 2026-10-24: "too many branches ... I expect this to be handled without
human intervention." Each habitat role pushes a branch (`habitat/<role>/<change>-
<run>`), and none was ever deleted: 59 in convergence after one afternoon.

- A chain that passed keeps only its builder branch: that is the PR's head, and
  the repository's delete-branch-on-merge setting removes it on merge.
- A chain that failed keeps none: a rebuild always starts from main, and every
  role's verdict and findings are already on the build issue.
- The branches come from the chain's own run file (`[dispatch] branch=...`), so
  only what this chain pushed is ever deleted.
"""
import re
import subprocess

BRANCH = re.compile(r"^\[dispatch\] branch=(\S+)")


def of_chain(lines):
    """The branches a chain's run file says it pushed, in order."""
    out = []
    for ln in lines:
        m = BRANCH.match(ln)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def delete(owner, repo, names, keep=(), runner=subprocess.run):
    """Delete these branches except `keep`; never main. [(name, error)] for failures."""
    failed = []
    for b in names:
        if b in keep or b in ("main", "master") or not b.startswith(("habitat/", "session/")):
            continue
        p = runner(["gh", "api", "-X", "DELETE", f"repos/{owner}/{repo}/git/refs/heads/{b}"],
                   capture_output=True, text=True)
        if p.returncode != 0 and "Reference does not exist" not in (p.stderr or ""):
            failed.append((b, (p.stderr or p.stdout).strip()[-120:]))
    return failed


def tidy(owner, b, keep=(), log=print, runner=subprocess.run):
    """A chain's branches go once it ends; `b` is the running build (its run file)."""
    try:
        lines = open(b["path"]).read().splitlines()
    except (OSError, KeyError):
        return
    for name, err in delete(owner, b["repo"], of_chain(lines), keep=keep, runner=runner):
        log(f"[listener] branch {name} not deleted: {err}", flush=True)
