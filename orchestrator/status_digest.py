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
                "open", "--json", "number,title,url,body,repository,createdAt"], run) or []
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


def digest(now, owner, gh, run, stuck):
    asks = waiting(owner, gh, run)
    day_ago = (now - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    return clean_tree({"generated": now.isoformat(timespec="seconds"), "waiting": asks,
                       "impediments": impediments(now, stuck, refusals(day_ago, run), asks)})


def write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
