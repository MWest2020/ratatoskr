# SPDX-License-Identifier: MIT
"""Which projects we are busy with: an activity score over the last days.

Mark, 2026-11-28, on westerweel.work/nu/ and the daily digest: "keep it shorter
per project and sort daily by what we are working on. Only the top 5 projects;
when we have not worked on one for a while, it drops out of /nu."

Per project, over the last `window` days (default 7): one point per merged PR,
per commit on the default branch and per closed issue, plus one for an open PR
touched in the window and one for a build in the factory right now. A project
with no point drops out, even when fewer than `top` remain. The three
owner-wide searches run once per run (`Activity` caches them); the commits are
one call per repository.
"""
import datetime
import os
import sys

TOP, WINDOW_DAYS = 5, 7
BUILDING = ("queued", "running", "merging", "deploying")
EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
COMMITS_JQ = "[.[] | {date: .commit.committer.date, title: (.commit.message | split(\"\\n\")[0])}]"


class Unavailable(RuntimeError):
    """An owner-wide search failed: no ranking is better than an empty page."""


def settings(env=None):
    """(top, window_days) from STATUS_TOP and STATUS_WINDOW_DAYS."""
    env = os.environ if env is None else env
    try:
        top = int(env.get("STATUS_TOP", TOP))
        days = int(env.get("STATUS_WINDOW_DAYS", WINDOW_DAYS))
    except ValueError as e:
        raise ValueError(f"STATUS_TOP and STATUS_WINDOW_DAYS must be whole numbers: {e}") from None
    if top < 1 or days < 1:
        raise ValueError(f"STATUS_TOP ({top}) and STATUS_WINDOW_DAYS ({days}) must be at least 1")
    return top, days


def _when(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


class Activity:
    """The activity of each project since `now - days`, from cached searches."""

    def __init__(self, owner, gh, run, now, days, state):
        self.owner, self.gh, self.run, self.now, self.state = owner, gh, run, now, state or {}
        self.since = now - datetime.timedelta(days=days)
        self._cache = {}

    def search(self, kind):
        if kind not in self._cache:
            day = self.since.date().isoformat()
            fields = "repository,number,title,closedAt,updatedAt"
            query = {"merged": ["prs", "--merged-at", f">={day}"],
                     "closed": ["issues", "--closed", f">={day}"],
                     "open": ["prs", "--state", "open"]}[kind]
            argv = ["search", *query, "--owner", self.owner, "--limit", "1000", "--json", fields]
            found = self.gh(argv, self.run)
            if found is None:
                found = self.gh(argv, self.run)   # one retry: a transient gh failure
            if not isinstance(found, list):
                raise Unavailable(f"gh search {kind} for {self.owner} failed twice")
            self._cache[kind] = found
        return self._cache[kind]

    def _hits(self, kind, repo, key, since=None):
        since = self.since if since is None else since
        for x in self.search(kind):
            when = _when(x.get(key))
            if x.get("repository", {}).get("name") == repo and when and when >= since:
                yield when, x

    def open_prs(self):
        """Every open PR of the owner as `repo#number` (for "in progress" items)."""
        return {f"{x['repository']['name']}#{x['number']}" for x in self.search("open")}

    def commits(self, repo):
        found = self.gh(["api", f"repos/{self.owner}/{repo}/commits?per_page=100", "--jq", COMMITS_JQ],
                        self.run)
        if not isinstance(found, list):
            print(f"[status-site] {repo}: commits unreadable, counted as none", file=sys.stderr)
            return []
        return [(w, c.get("title") or "") for c in found if (w := _when(c.get("date")))]

    def of(self, repo):
        """{score, last, recent} for one project; `last` is a date, also outside the window."""
        merged = sorted(self._hits("merged", repo, "closedAt"), key=lambda h: h[0])
        closed = list(self._hits("closed", repo, "closedAt"))
        commits = sorted(self.commits(repo))
        recent_commits = [c for c in commits if c[0] >= self.since]
        touched_ever = [w for w, _ in self._hits("open", repo, "updatedAt", since=EPOCH)]
        touched = [w for w in touched_ever if w >= self.since]
        building = any(x.get("repo") == repo for k in BUILDING for x in self.state.get(k, []))
        score = len(merged) + len(closed) + len(recent_commits) + bool(touched) + building
        dates = [w for w, _ in merged + closed] + [w for w, _ in commits] + touched_ever
        dates += [self.now] if building else []
        last = max(dates, default=None)
        recent = None
        if merged:
            recent = {"kind": "merged", "title": merged[-1][1]["title"], "date": merged[-1][0]}
        elif recent_commits:
            recent = {"kind": "commit", "title": recent_commits[-1][1], "date": recent_commits[-1][0]}
        if recent:
            recent["date"] = recent["date"].date().isoformat()
        return {"score": score, "last": last.date().isoformat() if last else None, "recent": recent}


def rank(projects, top):
    """(shown, inactive): the `top` most active projects, the rest by last activity.

    A project with score 0 never shows. Ties go to the most recent activity."""
    def key(p):
        return (-p["activity"]["score"], _neg_date(p["activity"]["last"]), p["name"])
    busy = sorted((p for p in projects if p["activity"]["score"] > 0), key=key)
    rest = sorted(busy[top:] + [p for p in projects if p["activity"]["score"] == 0],
                  key=lambda p: (_neg_date(p["activity"]["last"]), p["name"]))
    return busy[:top], [{"name": p["name"], "last": p["activity"]["last"]} for p in rest]


def _neg_date(day):
    """A sort key that puts newer ISO dates first and no date last."""
    return -datetime.date.fromisoformat(day).toordinal() if day else 0
