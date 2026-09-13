#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""The sources of the work overview: clones, GitHub and running work sessions.

Separate from board.py because this is the impure side — glob, subprocess,
network — and because otherwise both files would go over 200 lines.

Every source that fails raises; `board.build` catches that and puts it in the
snapshot as a READ ERROR. Silently returning an empty list is exactly the
difference between "there is nothing to do" and "I could not look".
"""
import glob
import json
import os
import subprocess
import time

from board_model import DAY, age_days, pr_column


def repo_url(clone_dir):
    """The GitHub URL of a clone, from its own remote. Do not guess from the
    directory name: a card pointing at a 404 is worse than a card without a link."""
    try:
        p = subprocess.run(["git", "-C", clone_dir, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    ref = (p.stdout or "").strip()
    if p.returncode != 0 or "github.com" not in ref:
        return ""
    path = ref.split("github.com", 1)[1].lstrip(":/").removesuffix(".git")
    return "https://github.com/" + path


def is_worktree(directory):
    """Is this a linked git worktree rather than the clone itself?

    A clone keeps `.git` as a directory; a worktree keeps it as a file pointing
    at the clone. That one-line difference is the whole test.

    Why the board cares: sessions get their own worktree of the same repo, so a
    single change appeared once per worktree — and worse, it kept appearing after
    it had been archived on main, because that worktree still holds the old
    branch. Measured 2026-09-13: five of the seven proposals on the board were
    the same two archived changes, seen from three abandoned worktrees. A board
    that shows work nobody has teaches you to stop reading the board.
    """
    return os.path.isfile(os.path.join(directory, ".git"))


def openspec_cards(pattern, now):
    """Every non-archived change is a proposal. The age comes from the mtime of
    proposal.md — that is when it was last worked on."""
    cards = []
    urls = {}
    for path in glob.glob(pattern):
        if "/archive/" in path:
            continue
        if is_worktree(path.split("/openspec/", 1)[0]):
            continue
        change = os.path.basename(os.path.dirname(path))
        repo = path.split("/home/agent/", 1)[-1].split("/openspec/", 1)[0]
        try:
            ts = os.path.getmtime(path)
        except OSError:
            continue
        clone = path.split("/openspec/", 1)[0]
        if clone not in urls:
            urls[clone] = repo_url(clone)
        # Link through to the change itself, not to the repo: you want the text,
        # not the front page. `branch` may differ; main is the truth here.
        base = urls[clone]
        url = f"{base}/tree/main/openspec/changes/{change}" if base else ""
        cards.append({"id": f"openspec:{repo}:{change}", "repo": repo,
                      "title": change, "column": "proposal", "via": "openspec",
                      "age_days": age_days(ts, now), "who": "", "url": url,
                      "source": path.replace("/home/agent/", "~/")})
    return cards


def gh_json(args):
    """Call `gh`. An error is a READ ERROR, not an empty list: showing nothing
    silently is indistinguishable from 'there is nothing'."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:160])
    return json.loads(p.stdout or "[]")


FIELDS = "repository,number,title,url,isDraft,updatedAt,author"


def open_prs(owner):
    """Wat nog aandacht vraagt — apart van `merged_prs`, want deze kant moet VERS
    zijn. Een gemergede PR die nog in 'review' staat vraagt om niets, en een
    kolom met zulke kaarten lees je niet meer. Gemeten 2026-09-13: #125 stond
    acht minuten na zijn merge nog in review, uit een cache van vlak ervóór."""
    return gh_json(["search", "prs", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", FIELDS])


def merged_prs(owner, merged_days, now):
    """Geschiedenis: verandert alleen naar achteren, mag dus uit een cache."""
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - merged_days * DAY))
    return [dict(r, merged=True) for r in gh_json(
        ["search", "prs", f"--owner={owner}", f"merged:>={cutoff}",
         "--limit", "40", "--json", FIELDS])]


def rows_to_cards(rows, now, ignore=()):
    cards = []
    for r in rows:
        if r["repository"]["name"] in ignore:
            continue
        pr = {"merged": r.get("merged", False), "draft": r.get("isDraft")}
        ts = time.mktime(time.strptime(r["updatedAt"][:19], "%Y-%m-%dT%H:%M:%S"))
        cards.append({"id": f"pr:{r['repository']['name']}:{r['number']}",
                      "repo": r["repository"]["name"],
                      "title": f"#{r['number']} {r['title']}",
                      "column": pr_column(pr), "via": "pull request",
                      "age_days": age_days(ts, now),
                      "who": (r.get("author") or {}).get("login", ""),
                      "url": r.get("url", ""), "source": ""})
    return cards


def pr_cards(owner, merged_days, now, ignore=()):
    """Beide kanten in één keer; het bord haalt ze apart op."""
    return rows_to_cards(open_prs(owner) + merged_prs(owner, merged_days, now),
                         now, ignore)


def last_activity(content):
    """The last tool call from a run file, short. A running session that only says
    "busy" is a progress bar without a bar."""
    last = ""
    for line in content.splitlines():
        if '"tool_use"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        for c in (ev.get("message") or {}).get("content", []):
            if c.get("type") == "tool_use":
                target = ""
                for k in ("file_path", "path", "pattern", "command"):
                    if c.get("input", {}).get(k):
                        target = str(c["input"][k])[-40:]
                        break
                last = f"{c.get('name')} {target}".strip()
    return last


# Een sessie schrijft continu naar zijn runbestand. Gebeurt dat een tijd niet
# meer én staat er geen result-regel in, dan is het proces weg (time-out, kill,
# herstart van de listener) en is de kaart een spook. Gemeten 2026-09-12: twee
# afgekapte reviews stonden uren in `building` — Mark: "building lane update niet
# en ik kan er niet op klikken".
SESSION_STALE = 300


def session_cards(runs_dir, now, stale_after=SESSION_STALE):
    """A work session is still running as long as there is no `result` line in the
    run file. Done is done: it leaves the board, it is in the channel."""
    cards = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.jsonl"))):
        try:
            content = open(path, errors="ignore").read()
            ts = os.path.getmtime(path)
        except OSError:
            continue
        if '"type":"result"' in content.replace(" ", ""):
            continue
        if now - ts > stale_after:
            continue          # dead process, not a running session
        name = os.path.basename(path).rsplit("-", 1)[0]
        typ, _, who = name.partition("-")
        # A session has no URL but it does have a CHANNEL: that is where it
        # talks. The app jumps there instead of showing a dead card.
        channel, writes = "", False
        try:
            first = json.loads(content.splitlines()[0])
            if first.get("type") == "boomhuis_session":
                channel = first.get("channel", "")
                who = first.get("requester", who)
                writes = bool(first.get("writes"))
        except (ValueError, IndexError):
            pass
        # What it is busy with: the last tool call in the run file. Without this a
        # running session is a card that says nothing, and that is exactly what
        # Mark missed: "tijdens bouwen verwacht ik updates".
        cards.append({"id": "session:" + os.path.basename(path),
                      "repo": "work session", "title": f"{typ} · {who}",
                      "column": "building",
                      "via": "session (writes)" if writes else "session",
                      "age_days": age_days(ts, now), "activity": last_activity(content),
                      "who": who, "url": "", "channel": channel, "source": path})
    return cards
