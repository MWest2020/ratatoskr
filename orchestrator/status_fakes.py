# SPDX-License-Identifier: MIT
"""Shared fakes for the status-site tests: a `gh` that answers from fixtures.

A hermetic stand-in for GitHub, so the tests of status_site, status_activity and
status_digest never reach the network or this host's real state.
"""
import base64
import datetime
import json
import subprocess
from zoneinfo import ZoneInfo

NOW = datetime.datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))


def fake_gh(responses):
    def run(argv, **kw):
        if argv[0] == "journalctl":
            return subprocess.CompletedProcess(argv, 0, stdout="x [listener] build refused: budget\n", stderr="")
        key = " ".join(argv[1:3])
        for k, v in responses.items():
            if key.startswith(k):
                if callable(v):
                    v = v(argv)
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(v), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="no")
    return run


def issues_for(argv):
    repo = argv[argv.index("--repo") + 1]
    if repo.endswith("/wordsworth"):
        return [{"number": 5, "title": "propose: a-change", "url": "https://github.com/MWest2020/wordsworth/issues/5",
                 "comments": []},
                {"number": 6, "title": "propose: broken", "url": "https://github.com/MWest2020/wordsworth/issues/6",
                 "comments": [{"body": "**architect: FAIL** (verdict failed)\n- [summary] gap in spec",
                               "createdAt": "2026-10-27T08:00:00Z"}]},
                {"number": 8, "title": "build: from-chat", "url": "https://github.com/MWest2020/wordsworth/issues/8",
                 "comments": [{"body": "**architect: FAIL** (verdict failed)\n- [summary] seam gap",
                               "createdAt": "2026-10-27T09:00:00Z"}]},
                {"number": 9, "title": "build: a-change", "url": "u9", "comments": []},
                {"number": 10, "title": "Unrelated build question", "url": "u10", "comments": []}]
    if repo.endswith("/convergence"):
        return [{"number": 7, "title": "propose: secret-game", "url": "https://github.com/MWest2020/convergence/issues/7",
                 "comments": []}]
    return []


ROADMAP = """# draft
project: wordsworth
goal: "A privacy-safe corpus"
current: pilot
phases:
  - {id: poc, name: PoC, summary: built}
  - {id: pilot, name: Pilot, summary: one dossier}
  - {id: production, name: Production, summary: later}
done_means:
  - {item: Report filled, status: done, evidence: "https://github.com/MWest2020/wordsworth/pull/284"}
  - {item: Every PDF redacted, status: open, evidence: "https://github.com/MWest2020/wordsworth/issues/259"}
"""


def roadmap_for(argv):
    if "/wordsworth/" in argv[2]:
        return {"content": base64.b64encode(ROADMAP.encode()).decode()}
    if "/convergence/" in argv[2]:
        return {"content": base64.b64encode(ROADMAP.replace("wordsworth", "convergence").encode()).decode()}
    return None


def visibility(argv):
    return {"visibility": "PRIVATE" if argv[3].endswith("/convergence") else "PUBLIC"}


WAITING = [{"number": 196, "title": "Ranking questions", "url": "u", "body": "Question\nDefault: the report stays open",
            "repository": {"name": "wordsworth"}, "createdAt": "2026-10-20T08:00:00Z"},
           {"number": 95, "title": "Legal sign-off", "url": "https://github.com/MWest2020/convergence/issues/95",
            "body": "Default: devnet only", "repository": {"name": "convergence"}, "createdAt": "2026-10-28T08:00:00Z"}]
# Activity in the week before NOW: wordsworth merged a PR (and one too old to
# count), convergence has a commit on main; nothing else moved.
MERGED = [{"repository": {"name": "wordsworth"}, "number": 40, "title": "pilot: the report",
           "closedAt": "2026-10-27T10:00:00Z"},
          {"repository": {"name": "wordsworth"}, "number": 30, "title": "too old", "closedAt": "2026-10-20T10:00:00Z"}]
CLOSED, OPEN_PRS = [], []
COMMITS = {"convergence": [{"date": "2026-10-26T09:00:00Z", "title": "demo: a map"}]}


def api(argv):
    if "/commits" in argv[2]:
        return COMMITS.get(argv[2].split("/")[2], [])
    return roadmap_for(argv)


def responses(merged=None, closed=None, open_prs=None, waiting=None):
    """The fake GitHub; any of the owner-wide searches can be swapped."""
    m, c, o, w = (MERGED if merged is None else merged, CLOSED if closed is None else closed,
                  OPEN_PRS if open_prs is None else open_prs, WAITING if waiting is None else waiting)
    return {"issue list": issues_for, "repo view": visibility, "api": api,
            "search prs": lambda argv: m if "--merged-at" in argv else o,
            "search issues": lambda argv: c if "--closed" in argv else w}
