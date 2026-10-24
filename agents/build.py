# SPDX-License-Identifier: MIT
"""`!build <repo> <change>`: odin starts a habitat build, the listener decides.

Mark, 2026-10-22: "definitely odin may build itself. My repos, whenever
possible or when it makes sense, openspecced, consulted and yes. build I want
traceability, but autonomous" (openspec change odin-runs-the-factory).

The model writes a marker; this module checks it against agents/factory.yml and
GitHub. Every condition is checked here and not in a prompt:

1. the repository is on the factory's list;
2. the OpenSpec change exists on that repository's main;
3. the daily budget is not used up and no other chain is running;
4. there is an issue. A build without one opens one first, so no build runs
   untracked;
5. a given issue number is an open issue, not a pull request and not closed.
   One that fails this opens a fresh issue instead, same as no number at all.

For an agent's answer the marker counts on the FIRST line only, the rule
sessions.py keeps for `!sessie`: text further down can be a quote.
"""
import json
import os
import re
import subprocess
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = re.compile(r"^!build\s+([A-Za-z0-9][A-Za-z0-9._-]{0,99})\s+"
                    r"([a-z0-9][a-z0-9._-]{0,99})(?:\s+#?(\d{1,7}))?\s*$", re.I)


def load(path=os.path.join(HERE, "factory.yml")):
    cfg = yaml.safe_load(open(path)) or {}
    for k in ("logdir", "runs"):
        cfg[k] = os.path.expanduser(cfg.get(k) or "")
    return cfg


def read_marker(text, own=True):
    """(repo, change, issue or 0) or None. `own`: only the first line counts."""
    lines = (text or "").strip().splitlines()
    for ln in (lines[:1] if own else lines):
        m = MARKER.match(ln.strip())
        if m:
            return m.group(1), m.group(2), int(m.group(3) or 0)
    return None


def strip_marker(text):
    lines = (text or "").strip().splitlines()
    return "\n".join(ln for ln in lines if not MARKER.match(ln.strip())).strip()


def canonical_repo(cfg, repo):
    """The listed spelling of `repo` (GitHub names are case-insensitive), or None."""
    return next((r for r in cfg.get("repos") or [] if r.lower() == repo.lower()), None)


def change_exists(owner, repo, change, runner=subprocess.run):
    """("", True) when openspec/changes/<change> is on main, else (reason, False)."""
    try:
        p = runner(["gh", "api", f"repos/{owner}/{repo}/contents/openspec/changes/{change}",
                    "--jq", "length"], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"could not ask GitHub: {e}", False
    if p.returncode != 0:
        return f"no OpenSpec change `{change}` on {owner}/{repo} main", False
    return "", True


def open_issue(owner, repo, number, runner=subprocess.run):
    """True when `number` is an open issue on owner/repo — not a pull request,
    not closed. GitHub serves pull requests through the issues API too, so the
    answer is read for both `pull_request` and `state`."""
    try:
        p = runner(["gh", "api", f"repos/{owner}/{repo}/issues/{number}", "--jq",
                    'if .pull_request then "pr" else .state end'],
                   capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return p.returncode == 0 and p.stdout.strip() == "open"


def builds_today(runs_dir, now=time.time):
    """How many builds started today, from the run files' first lines."""
    if not os.path.isdir(runs_dir):
        return 0
    day = time.strftime("%Y-%m-%d", time.localtime(now()))
    n = 0
    for f in os.listdir(runs_dir):
        try:
            with open(os.path.join(runs_dir, f)) as fh:
                head = json.loads(fh.readline())
        except (OSError, ValueError):
            continue
        n += time.strftime("%Y-%m-%d", time.localtime(head.get("started", 0))) == day
    return n


def check(cfg, repo, change, running, runner=subprocess.run, now=time.time, capped=True):
    """(canonical repo, "") when a build may start, else (None, the reason).
    `capped=False` for a build Mark types himself: the daily budget guards the
    agents' loop, not his own decision (2026-10-24, the 7th build of a day)."""
    name = canonical_repo(cfg, repo)
    if not name:
        return None, f"`{repo}` is not on the factory's list of repositories"
    if len(running) >= int(cfg.get("max_concurrent", 1)):
        return None, "another build is still running; one chain at a time"
    if capped and builds_today(cfg["runs"], now) >= int(cfg.get("builds_per_day", 0)):
        return None, f"today's build budget ({cfg.get('builds_per_day')}) is used up"
    why, ok = change_exists(cfg["owner"], name, change, runner)
    return (name, "") if ok else (None, why)


def clause(handle, hub, cfg):
    """What the hub is told about building; nothing when it may not."""
    if handle != hub or not cfg.get("repos"):
        return ""
    return ("\n\nYou can START A BUILD yourself: put `!build <repo> <openspec-change> "
            "[issue number]` on the FIRST line of your answer. The listener checks it "
            f"(repos: {', '.join(cfg['repos'])}; the change must exist on main; at most "
            f"{cfg.get('builds_per_day')} a day, one at a time), opens an issue when "
            "you give none, and runs habitat's architect, builder, reviewer and security "
            "on it. Every verdict lands on the issue. Build only what has a decided "
            "OpenSpec change; consult @architect first when the design is open.")
