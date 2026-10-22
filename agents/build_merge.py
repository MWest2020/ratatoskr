# SPDX-License-Identifier: MIT
"""Phase 2 of odin-runs-the-factory: after the cage, after CI, merge.

Mark, 2026-10-22, on merging and deploying without him: "absolutely" (alma
excluded). A chain that passed all four roles is not yet a merge: CI has to
agree. The decision is made from GitHub's own check states, never from a
pipe whose exit code lies (the handbook's grep -qv lesson):

- **merge** when no check is failing, cancelled or pending, and at least one
  passed. Zero checks means nothing verified the branch, so it is not merged;
- **wait** while any check is pending;
- **stop** on a failing or cancelled check, and say which one.

Every call is a fixed gh argv; the PR body goes over stdin.
"""
import json
import re
import subprocess

TIMEOUT_S = 60


def _gh(argv, runner, body=None):
    kw = {"input": body} if body is not None else {}
    try:
        p = runner(argv, capture_output=True, text=True, timeout=TIMEOUT_S, **kw)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"gh did not finish: {e}"
    if p.returncode not in (0, 8):   # 8: `gh pr checks` with checks still pending
        return "", (p.stderr.strip().splitlines() or ["gh failed, no reason given"])[0]
    return p.stdout, ""


def open_pr(owner, repo, branch, change, issue, verdicts, runner=subprocess.run):
    """(pr number, error)."""
    body = (f"Built by habitat for OpenSpec change `{change}`.\n\n"
            + "\n".join(f"- {v}" for v in verdicts)
            + f"\n\nCloses #{issue}\n\nOpened by the ratatoskr listener (factory phase 2); it "
              "merges this once every check passes.")
    out, err = _gh(["gh", "pr", "create", f"--repo={owner}/{repo}", f"--head={branch}",
                    "--base=main", f"--title=build: {change}", "--body-file=-"], runner, body)
    m = re.search(r"/pull/(\d+)", out)
    if err or not m:
        return 0, err or f"no PR url in gh output: {out.strip()[:80]!r}"
    return int(m.group(1)), ""


def checks(owner, repo, pr, runner=subprocess.run):
    """('merge' | 'wait' | 'stop', detail)."""
    out, err = _gh(["gh", "pr", "checks", str(int(pr)), f"--repo={owner}/{repo}",
                    "--json=name,bucket"], runner)
    if err:
        if "no checks reported" in err.lower():
            return "wait", "no checks reported yet"
        return "stop", f"could not read the checks: {err}"
    try:
        rows = json.loads(out or "[]")
    except ValueError:
        return "stop", "the checks were not JSON"
    bad = [r["name"] for r in rows if r.get("bucket") in ("fail", "cancel")]
    if bad:
        return "stop", "failing: " + ", ".join(bad)
    pending = [r["name"] for r in rows if r.get("bucket") == "pending"]
    if pending:
        return "wait", "pending: " + ", ".join(pending)
    if not any(r.get("bucket") == "pass" for r in rows):
        return "wait", "no check has passed yet"
    return "merge", f"{sum(r.get('bucket') == 'pass' for r in rows)} checks passed"


def merge(owner, repo, pr, runner=subprocess.run):
    return _gh(["gh", "pr", "merge", str(int(pr)), f"--repo={owner}/{repo}", "--merge"],
               runner)[1]
