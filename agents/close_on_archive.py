# SPDX-License-Identifier: MIT
"""Closes `build:`/`propose:` issues once their change is archived on main.

Before this, only a chain's own archive PR closed `propose:` issues
(propose_wiring.after_merge). Three build issues stayed open after their
change was archived by hand or split (wordsworth #305, convergence #80, #104)
because nothing else looked. On a 30-minute tick `ticker` reads main itself
for every repository with an open `build:`/`propose:` issue — no snapshot, so
it covers a chain's own archive and a hand-archive alike, and survives a
restart. A change gone from `openspec/changes` without an archive directory
is only logged: a wrong close is worse than a missed one.

`close_change` is the same closer, used right after a chain's own archive PR
merges (propose_wiring.after_merge): it always resolves the dated archive id
from the archive listing, never from `state.json`, so an old `merging` entry
without that field needs no fallback.
"""
import json
import re
import subprocess
import time

import issues as gh_issues

TICK_S = 1800
TITLE = re.compile(r"^(?:build|propose): (.+)$")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")


def _gh(argv, runner):
    try:
        p = runner(argv, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"gh did not finish: {e}"
    if p.returncode != 0:
        return "", (p.stderr.strip().splitlines() or ["gh failed, no reason given"])[-1]
    return p.stdout, ""


def open_changes(owner, repo, runner=subprocess.run):
    """{change: [(number, title)]} for open build:/propose: issues, or ({}, error)."""
    out, err = _gh(["gh", "issue", "list", f"--repo={owner}/{repo}", "--state=open",
                    "--limit=100", "--json=number,title"], runner)
    if err:
        return {}, err
    try:
        rows = json.loads(out or "[]")
    except ValueError:
        rows = []
    by_change = {}
    for r in rows:
        m = TITLE.match(r.get("title", ""))
        if m:
            by_change.setdefault(m.group(1), []).append((r["number"], r.get("title", "")))
    return by_change, ""


def archived(owner, repo, runner=subprocess.run):
    """{change: [dated archive dirs]} from openspec/changes/archive, or ({}, error)."""
    out, err = _gh(["gh", "api", f"repos/{owner}/{repo}/contents/openspec/changes/archive",
                    "--jq", '.[] | select(.type == "dir") | .name'], runner)
    if err:
        return {}, err
    by_change = {}
    for name in out.split():
        m = DATED.match(name)
        if m:
            by_change.setdefault(m.group(1), []).append(name)
    return by_change, ""


def still_on_main(owner, repo, runner=subprocess.run):
    """Change ids under openspec/changes (not the archive dir itself), or (None, error)."""
    out, err = _gh(["gh", "api", f"repos/{owner}/{repo}/contents/openspec/changes", "--jq",
                    '.[] | select(.type == "dir" and .name != "archive") | .name'], runner)
    return (None, err) if err else (set(out.split()), "")


def _close(owner, repo, change, path, numbers, issues, log):
    for number, _title in numbers:
        err = issues.close(repo, number, f"Archived: `{change}` is at `{path}`.")
        if err:
            log(f"[listener] close {owner}/{repo}#{number}: {err}", flush=True)


def tick_repo(owner, repo, issues=gh_issues, runner=subprocess.run, log=print):
    """One tick for one repository: one issue-list call, then at most one pair
    of `gh api` listing calls, only when an open build:/propose: issue exists."""
    by_change, err = open_changes(owner, repo, runner)
    if err:
        return log(f"[listener] close-on-archive {owner}/{repo}: {err}", flush=True)
    if not by_change:
        return
    on_main, err = still_on_main(owner, repo, runner)
    if err:
        return log(f"[listener] close-on-archive {owner}/{repo}: {err}", flush=True)
    by_archive, err = archived(owner, repo, runner)
    if err:
        return log(f"[listener] close-on-archive {owner}/{repo}: {err}", flush=True)
    for change, numbers in by_change.items():
        if change in on_main:
            continue
        dirs = by_archive.get(change, [])
        if len(dirs) != 1:
            log(f"[listener] {owner}/{repo} {change}: left openspec/changes without exactly "
                f"one archive directory ({len(dirs)} found); not closed", flush=True)
            continue
        _close(owner, repo, change, f"openspec/changes/archive/{dirs[0]}", numbers, issues, log)


def ticker(owner, repos, issues=gh_issues, runner=subprocess.run, now=time.time, log=print):
    """`tick()` for the main loop: every TICK_S, once per repository."""
    last = [None]

    def tick():
        if last[0] is not None and now() - last[0] < TICK_S:
            return
        last[0] = now()
        for repo in repos:
            tick_repo(owner, repo, issues, runner, log)
    return tick


def close_change(owner, repo, change, issues=gh_issues, runner=subprocess.run, log=print):
    """Close the build:/propose: issues of `change` right after a chain's own
    archive PR merges. The dated id is resolved here, from the archive
    listing, never carried through state.json."""
    by_archive, err = archived(owner, repo, runner)
    if err:
        return log(f"[listener] close-on-archive {owner}/{repo} {change}: {err}", flush=True)
    dirs = by_archive.get(change, [])
    if len(dirs) != 1:
        return log(f"[listener] close-on-archive {owner}/{repo} {change}: "
                   f"{len(dirs)} archive directories found; not closed", flush=True)
    path = f"openspec/changes/archive/{dirs[0]}"
    for title in (f"build: {change}", f"propose: {change}"):
        numbers = [(n, title) for n in issues.open_titled(repo, title)]
        _close(owner, repo, change, path, numbers, issues, log)
