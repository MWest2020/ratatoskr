#!/usr/bin/env python3
"""The public overview on westerweel.work/nu/: what the factory is working on.

Mark, 2026-10-28: a dedicated overview on his own site, built from facts, not
written by a model. This script reads the build state, the run files and GitHub
(proposal issues, merged PRs, issues labelled `waiting-on-mark`), passes every
string through status_scrub, and writes `data/status.json` into a worktree of
MWest2020/westerweel-work. Hugo renders it; Cloudflare Pages deploys on push.

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
from status_scrub import clean_tree, public_url  # noqa: E402

OWNER = "MWest2020"
BASE = ["wordsworth", "convergence", "ratatoskr", "habitat", "handbook", "homelab"]
STATE = os.path.expanduser("~/.local/state/ratatoskr")
SITE = os.path.expanduser(os.environ.get("STATUS_SITE_DIR", "~/.worktrees/westerweel-status"))
HOMELAB = os.path.expanduser("~/homelab")
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
    """The last role verdict on a build issue, when it is a FAIL: (role, why)."""
    for c in reversed(comments or []):
        body = c.get("body") or ""
        if body.startswith("**") and ": FAIL" in body.split("\n", 1)[0]:
            role = body[2:].split(":", 1)[0]
            first = next((ln[len("- [summary] "):] for ln in body.splitlines()
                          if ln.startswith("- [summary] ")), "")
            return role, first[:220]
        if body.startswith("Merged PR") or "PASS" in body.split("\n", 1)[0]:
            return None
    return None


def in_flight(repo, state, run=subprocess.run):
    issues = gh(["issue", "list", "--repo", f"{OWNER}/{repo}", "--state", "open", "--limit", "40",
                 "--search", "propose: in:title", "--json", "number,title,comments,url"], run) or []
    flight, stuck = [], []
    for i in issues:
        if not i["title"].startswith("propose: "):
            continue
        change = i["title"][len("propose: "):].strip()
        stage = stage_of(repo, change, state)
        verdict = None if stage else failed(i.get("comments"))
        entry = {"change": change, "issue": i["number"], "url": i["url"]}
        if verdict:
            stuck.append({**entry, "why": f"{verdict[0]} FAIL: {verdict[1]}".strip()})
        else:
            flight.append({**entry, "stage": stage or "proposed"})
    return flight, stuck


def delivered(repo, since, run=subprocess.run, homelab_log=""):
    prs = gh(["pr", "list", "--repo", f"{OWNER}/{repo}", "--state", "merged", "--limit", "40",
              "--search", f"merged:>={since:%Y-%m-%d}",
              "--json", "number,title,url,mergedAt,mergeCommit"], run) or []
    out = []
    for p in prs:
        t = p["title"]
        if t.startswith("openspec: archive") or t.startswith("openspec: amend"):
            continue
        sha = ((p.get("mergeCommit") or {}).get("oid") or "")[:7]
        deployed = bool(sha) and f"deploy {sha}" in homelab_log
        kind = "spec" if t.startswith("openspec:") else ("deployed" if deployed else "merged")
        out.append({"title": t, "pr": p["number"], "url": p["url"], "when": p["mergedAt"],
                    "kind": kind})
    return sorted(out, key=lambda x: x["when"], reverse=True)[:8]


def refusals(since, run=subprocess.run):
    p = run(["journalctl", "--user", "-u", "ratatoskr-agents", "--since", since, "--no-pager",
             "-o", "cat"], capture_output=True, text=True)
    return [ln.split("build refused: ", 1)[1][:220] for ln in (p.stdout or "").splitlines()
            if "build refused: " in ln]


def waiting(run=subprocess.run):
    items = gh(["search", "issues", "--owner", OWNER, "--label", "waiting-on-mark", "--state",
                "open", "--json", "number,title,url,body,repository"], run) or []
    out = []
    for i in items:
        body = i.get("body") or ""
        default = next((ln.split(":", 1)[1].strip() for ln in body.splitlines()
                        if ln.strip().lower().startswith("default:")), "")
        out.append({"repo": i["repository"]["name"], "issue": i["number"], "url": i["url"],
                    "question": i["title"], "default": default})
    return out


def build(now, run=subprocess.run, state=None, homelab_log=""):
    state = state if state is not None else json.load(open(os.path.join(STATE, "builds", "state.json")))
    since = now - datetime.timedelta(days=7)
    projects, stuck_all = [], []
    for repo in repos(now):
        vis = gh(["repo", "view", f"{OWNER}/{repo}", "--json", "visibility"], run) or {}
        public = vis.get("visibility") == "PUBLIC"
        flight, stuck = in_flight(repo, state, run)
        done = delivered(repo, since, run, homelab_log)
        for x in flight + stuck + done:
            x["url"] = public_url(x.get("url"), public)
        for s in stuck:
            stuck_all.append({**s, "repo": repo})
        if flight or stuck or done:
            projects.append({"name": repo, "public": public, "in_flight": flight, "delivered": done,
                             "url": public_url(f"https://github.com/{OWNER}/{repo}", public)})
    for why in refusals((now - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"), run):
        stuck_all.append({"repo": "", "change": "", "why": f"build refused: {why}", "url": None})
    data = {"generated": now.isoformat(timespec="minutes"), "projects": projects,
            "stuck": stuck_all, "waiting": waiting(run)}
    return clean_tree(data)


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
    now = datetime.datetime.now(TZ)
    log = subprocess.run(["git", "-C", HOMELAB, "log", "--oneline", "-200", "origin/main"],
                         capture_output=True, text=True).stdout
    data = build(now, homelab_log=log)
    if "--print" in sys.argv:
        print(json.dumps(data, indent=1, ensure_ascii=False))
        return
    print(f"[status-site] {publish(data)}")


if __name__ == "__main__":
    main()
