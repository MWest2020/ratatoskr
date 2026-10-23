# SPDX-License-Identifier: MIT
"""Chat agents can read the repositories they are asked to judge.

2026-10-23: odin consulted the reviewer on the wordsworth pilot plan, and the
reviewer answered "LIMIT: I can't read wordsworth": a chat turn's Read, Grep
and Glob are scoped to the listener tree (providers.scoped, `./**`), so it
judged a report about code it could not open.

The listener keeps a shallow clone of main for each repository in
factory.yml `readable` under `<listener>/.repos/<name>/` (gitignored), inside
the scope every turn already has. No new permit, nothing writable: chat
agents have Write and Edit denied. Refreshed at most every REFRESH seconds
from the main loop. `readable` is its own list, not `repos`, so a private
repository is never readable by accident.
"""
import os
import subprocess

DIR = ".repos"
REFRESH = 600


def _git(argv, run):
    try:
        p = run(argv, capture_output=True, text=True, timeout=90)
    except (subprocess.TimeoutExpired, OSError) as e:
        return str(e)[:160]
    return "" if p.returncode == 0 else (p.stderr.strip().splitlines() or ["git failed"])[-1][:160]


def sync(names, owner, root, run=subprocess.run, log=print):
    """Clone or move each repository to its main. {name: "" or the reason}."""
    out = {}
    for name in names:
        path = os.path.join(root, DIR, name)
        if os.path.isdir(os.path.join(path, ".git")):
            err = (_git(["git", "-C", path, "fetch", "-q", "--depth", "1", "origin", "HEAD"], run)
                   or _git(["git", "-C", path, "reset", "-q", "--hard", "FETCH_HEAD"], run))
        else:
            err = _git(["git", "clone", "-q", "--depth", "1",
                        f"https://github.com/{owner}/{name}.git", path], run)
        if err:
            log(f"[listener] read clone {name}: {err}", flush=True)
        out[name] = err
    return out


def ticker(cfg, root, now, run=subprocess.run, log=print):
    """`tick()` for the main loop: a sync when the last one is REFRESH old."""
    last = [None]

    def tick():
        if last[0] is None or now() - last[0] >= REFRESH:
            last[0] = now()
            sync(cfg.get("readable") or [], cfg["owner"], root, run, log)
    return tick


def clause(cfg):
    names = cfg.get("readable") or []
    if not names:
        return ""
    return ("\n\nREPOSITORIES you can read (main, at most ten minutes old): "
            + ", ".join(f"`{DIR}/{n}/`" for n in names) + ". Read the code and docs "
            "there before you judge a plan or a change; say plainly what you did not read.")
