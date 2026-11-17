#!/usr/bin/env python3
"""The public overview on westerweel.work/nu/: phase, roadmap and gap per project.

Mark, 2026-10-28: a dedicated overview on his own site, built from facts (build
state, run files, GitHub) with every string through status_scrub, written to
`data/status.json` in a westerweel-work worktree; Cloudflare Pages deploys it.
2026-10-30: the page shows each project's roadmap (status_roadmap) and the gap
to done; what waits on Mark and what is stuck go to a local digest for his
daily mail (status_digest), not on the page.
2026-11-17: the page exposed too much. Per project only name, goal, phase,
progress and plain "next up" lines, in NL and EN, without coordination notes;
private projects and client names left out (status_public, status_site.yml).

It pushes only when the content changed (the generation time aside) and at most
once every two hours: Cloudflare Pages' free tier has a monthly build budget.
"""
import datetime
import glob
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status_digest  # noqa: E402
import status_public  # noqa: E402
import status_roadmap  # noqa: E402
from status_scrub import clean_tree  # noqa: E402

OWNER = "MWest2020"
CONFIG = status_public.load()
BASE = list(CONFIG["projects"])
STATE = os.path.expanduser("~/.local/state/ratatoskr")
SITE = os.path.expanduser(os.environ.get("STATUS_SITE_DIR", "~/.worktrees/westerweel-status"))
DIGEST = os.path.join(STATE, "mark-digest.json")
MIN_GAP_S = 2 * 3600
TZ = ZoneInfo("Europe/Amsterdam")
STAGES = {"proposing": "proposing", "queued": "queued", "running": "building",
          "merging": "merging", "deploying": "deploying"}


def gh(args, run=subprocess.run):
    p = run(["gh", *args], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout or "null")
    except json.JSONDecodeError:
        return None


def repos(now, runs=os.path.join(STATE, "builds")):
    """The base projects plus any repo the factory built for in the last week."""
    seen = list(BASE)
    for path in glob.glob(os.path.join(runs, "*.log")):
        if now.timestamp() - os.path.getmtime(path) < 7 * 86400:
            repo = os.path.basename(path).split("-")[0]
            if repo and repo not in seen:
                seen.append(repo)
    return seen


def stage_of(repo, change, state):
    for key, stage in STAGES.items():
        if any(x.get("repo") == repo and x.get("change") == change for x in state.get(key, [])):
            return stage
    return None


def failed(comments):
    """The last role verdict on a build issue, when it is a FAIL: (role, why, when)."""
    for c in reversed(comments or []):
        body = c.get("body") or ""
        if body.startswith("**") and ": FAIL" in body.split("\n", 1)[0]:
            role = body[2:].split(":", 1)[0]
            first = next((ln[len("- [summary] "):] for ln in body.splitlines()
                          if ln.startswith("- [summary] ")), "")
            return role, first[:220], c.get("createdAt")
        if body.startswith("Merged PR") or "PASS" in body.split("\n", 1)[0]:
            return None
    return None


PREFIXES = ("propose: ", "build: ")


def in_flight(repo, state, run=subprocess.run):
    # A build started from chat gets a `build:` issue, not a `propose:` one
    # (2026-10-31: a 19-hour architect FAIL on a build issue never reached the digest).
    issues = gh(["issue", "list", "--repo", f"{OWNER}/{repo}", "--state", "open", "--limit", "60",
                 "--search", "propose OR build in:title", "--json", "number,title,comments,url"], run) or []
    flight, stuck, seen = [], [], set()
    for i in issues:
        prefix = next((p for p in PREFIXES if i["title"].startswith(p)), None)
        change = i["title"][len(prefix):].strip() if prefix else None
        if not change or change in seen:
            continue
        seen.add(change)
        stage = stage_of(repo, change, state)
        verdict = None if stage else failed(i.get("comments"))
        entry = {"change": change, "issue": i["number"], "url": i["url"]}
        if verdict:
            stuck.append({**entry, "repo": repo, "since": verdict[2],
                          "why": f"{verdict[0]} FAIL: {verdict[1]}".strip()})
        else:
            flight.append({**entry, "stage": stage or "proposed"})
    return flight, stuck


def collect(now, run=subprocess.run, state=None, cfg=None):
    """(page data, digest data): the page is public and high-level, the digest is Mark's.
    Every project feeds the digest; only the ones `status_public.shown` allows reach the
    page, and no page line names one that is left out. The page is None when client
    names are hidden but the local client list is missing."""
    state = state if state is not None else json.load(open(os.path.join(STATE, "builds", "state.json")))
    cfg = cfg or CONFIG
    visible, stuck_all = {}, []
    for repo in repos(now):
        vis = gh(["repo", "view", f"{OWNER}/{repo}", "--json", "visibility"], run) or {}
        visible[repo] = vis.get("visibility") == "PUBLIC"
        stuck_all += in_flight(repo, state, run)[1]
    shown = [r for r in visible if status_public.shown(r, cfg, visible[r])]
    cfg = status_public.hide(cfg, [r for r in visible if r not in shown])
    projects = []
    for repo in shown:
        roadmap = status_roadmap.fetch(OWNER, repo, gh, run)
        row = roadmap and status_public.row(repo, roadmap, cfg, visible[repo], f"https://github.com/{OWNER}/{repo}")
        if row:
            projects.append(row)
    page = clean_tree({"generated": now.isoformat(timespec="seconds"), "schema": 2, "projects": projects})
    if cfg.get("clients_missing") and not cfg["show_client_names"]:
        page = None
    return page, status_digest.digest(now, OWNER, gh, run, stuck_all)


def build(now, run=subprocess.run, state=None):
    return collect(now, run, state)[0]


def same_content(a, b):
    strip = lambda d: {k: v for k, v in (d or {}).items() if k != "generated"}  # noqa: E731
    return strip(a) == strip(b)


def publish(data, site=SITE, run=subprocess.run, now=None, mark=os.path.join(STATE, "status-site.json")):
    """Write and push when changed and at least MIN_GAP_S after the last push."""
    now = now or datetime.datetime.now(TZ)
    git = ["git", "-C", site]
    run(git + ["fetch", "-q", "origin"], check=True)
    run(git + ["reset", "-q", "--hard", "origin/main"], check=True)
    path = os.path.join(site, "data", "status.json")
    old = json.load(open(path)) if os.path.exists(path) else None
    if same_content(old, data):
        return "unchanged"
    last = json.load(open(mark)).get("pushed", 0) if os.path.exists(mark) else 0
    if now.timestamp() - last < MIN_GAP_S:
        return "throttled"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    run(git + ["add", "data/status.json"], check=True)
    run(git + ["-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com", "commit",
               "-q", "-m", f"status: overview {data['generated']} (generated by ratatoskr)"], check=True)
    run(git + ["push", "-q", "origin", "HEAD:main"], check=True)
    os.makedirs(os.path.dirname(mark), exist_ok=True)
    json.dump({"pushed": now.timestamp()}, open(mark, "w"))
    return "pushed"


def main():
    """`--print` shows the page and writes nothing (no digest, no push)."""
    now = datetime.datetime.now(TZ)
    page, digest = collect(now)
    if "--print" in sys.argv:
        print(json.dumps(page, indent=1, ensure_ascii=False))
        return
    status_digest.write(digest, DIGEST)
    if page is None:
        sys.exit("[status-site] refused: client names are hidden but the client list "
                 f"({CONFIG.get('clients_file')}) is missing; nothing published")
    print(f"[status-site] {publish(page)}; digest: {len(digest['waiting'])} waiting, "
          f"{len(digest['impediments'])} impediments")


if __name__ == "__main__":
    main()
