"""What waits on Mark and what is stuck: the daily digest, by mail, not on the page.

Mark, 2026-10-30: "waiting on Mark I'd rather have daily by mail; stuck is an
impediment? then also in the mail." The generator writes
`~/.local/state/ratatoskr/mark-digest.json` on every run; the coding session
mails it once a day. It goes to Mark alone, so links into private repositories
stay; every string still passes the secrets scrubber.

Impediments: a build whose last verdict is a FAIL and that has not been amended
and rebuilt for more than 12 hours; a build refusal of the last 24 hours (the
breaker's "split it" among them); a waiting-on-mark question open for more than
three days.

Since 2026-11-28 (Mark: "shorter per project, sorted by what we are working
on"): `projects_active` carries the projects the page shows, in activity order,
one line each, and the questions are sorted by that order; none is dropped.
"""
import datetime
import json
import os

from status_scrub import clean_tree

STUCK_AFTER = datetime.timedelta(hours=12)
WAITING_TOO_LONG = datetime.timedelta(days=3)


def _when(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def waiting(owner, gh, run):
    """Open issues labelled waiting-on-mark: the question, a link, the default."""
    items = gh(["search", "issues", "--owner", owner, "--label", "waiting-on-mark", "--state",
                "open", "--limit", "1000", "--json", "number,title,url,body,repository,createdAt"], run)
    if items is None:
        return None   # unreadable, which the digest says; never "no questions"
    out = []
    for i in items:
        default = next((ln.split(":", 1)[1].strip() for ln in (i.get("body") or "").splitlines()
                        if ln.strip().lower().startswith("default:")), "")
        out.append({"repo": i["repository"]["name"], "issue": i["number"], "url": i["url"],
                    "question": i["title"], "default": default, "since": i.get("createdAt")})
    return out


def refusals(since, run):
    p = run(["journalctl", "--user", "-u", "ratatoskr-agents", "--since", since, "--no-pager",
             "-o", "cat"], capture_output=True, text=True)
    return [ln.split("build refused: ", 1)[1][:220] for ln in (p.stdout or "").splitlines()
            if "build refused: " in ln]


def impediments(now, stuck, refused, asks):
    out = []
    for s in stuck:
        since = _when(s.get("since"))
        if since and now - since > STUCK_AFTER:
            out.append({"kind": "build-failed", "repo": s["repo"], "change": s["change"],
                        "why": s["why"], "since": s["since"], "url": s.get("url")})
    for why in refused:
        kind = "breaker" if "without a merge" in why else "refused"
        out.append({"kind": kind, "why": why})
    for a in asks:
        since = _when(a.get("since"))
        if since and now - since > WAITING_TOO_LONG:
            out.append({"kind": "waiting-too-long", "repo": a["repo"], "why": a["question"],
                        "since": a["since"], "url": a["url"]})
    return out


SITE_STATE = os.path.expanduser("~/.local/state/ratatoskr/site-freshness.json")
SITE_FRESH = datetime.timedelta(days=8)


def site_stale(now, path=None):
    """The weekly site-freshness findings (site_freshness.py) as one impediment,
    while that run is recent and found something."""
    try:
        with open(path or SITE_STATE, encoding="utf-8") as fh:   # resolved now: tests patch it
            state = json.load(fh)
    except (OSError, ValueError):
        return []
    since, found = _when(state.get("generated")), state.get("findings") or []
    if not found or not since or now - since > SITE_FRESH:
        return []
    first = "; ".join(f.get("message", "") for f in found[:2])
    return [{"kind": "site-stale", "why": f"{len(found)} finding(s) on westerweel.work: {first}",
             "since": state["generated"], "url": state.get("pr") or state.get("issue")}]


def one_line(p):
    """One project as one line of the mail: phase and progress, in flight, last change."""
    parts = []
    if p.get("phase"):
        parts.append(f"{p['phase']} ({p['progress']['done']}/{p['progress']['total']} done)")
    flight = p.get("in_flight") or []
    if flight:
        more = f" +{len(flight) - 1}" if len(flight) > 1 else ""
        parts.append(f"in flight: {flight[0]['change']} ({flight[0]['stage']}){more}")
    if p.get("recent"):
        parts.append(f"last: {p['recent'].get('title') or p['recent']['kind']} ({p['recent']['date']})")
    return "; ".join(parts) or "activity without a roadmap"


def active(projects, owner):
    """The projects the page shows, in activity order, one line each (Mark 2026-11-28)."""
    return [{"repo": p["name"], "score": p["activity"]["score"], "last": p["activity"]["last"],
             "status": one_line(p), "url": f"https://github.com/{owner}/{p['name']}"} for p in projects]


def by_project(asks, order):
    """Every question stays; those of the busiest projects come first, then by age."""
    pos = {name: i for i, name in enumerate(order)}
    return sorted(asks, key=lambda a: (pos.get(a["repo"], len(pos)), a.get("since") or ""))


def digest(now, owner, gh, run, stuck, site_state=None, active_projects=(), order=(), broken=None):
    """`broken`: why the page could not be built this run (an impediment of its own)."""
    asks = waiting(owner, gh, run)
    unread = [{"kind": "waiting-unreadable", "why": "gh search for waiting-on-mark issues failed"}]
    unread = unread if asks is None else []
    asks = by_project(asks or [], order)
    day_ago = (now - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    found = unread + impediments(now, stuck, refusals(day_ago, run), asks) + site_stale(now, site_state)
    found += [{"kind": "status-unavailable", "why": broken}] if broken else []
    return clean_tree({"generated": now.isoformat(timespec="seconds"),
                       "projects_active": active(active_projects, owner), "waiting": asks,
                       "impediments": found})


def write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
