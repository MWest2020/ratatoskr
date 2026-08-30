"""GitHub-leeslaag voor de PWA (repo/PR-view). Stdlib-only (urllib).

Token uit env GITHUB_TOKEN (tailnet-only .env op de host, nooit in git). Scope
bewust beperkt tot MWest2020's eigen repo's; een hard vangnet filtert alles wat
naar 'conduction' ruikt eruit (werkgever-org blijft buiten beeld).
"""
import json
import os
import urllib.request
import urllib.error

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
OWNER = "MWest2020"


def _forbidden(full_name):
    return "conduction" in (full_name or "").lower()


def _gh(path):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN niet gezet")
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": "token " + TOKEN,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "boomhuis-pwa"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def list_repos(limit=30):
    """Eigen repo's (owner), nieuwste eerst; conduction eruit gefilterd."""
    data = _gh(f"/user/repos?affiliation=owner&sort=updated&per_page={limit}")
    out = []
    for r in data:
        if _forbidden(r.get("full_name")):
            continue
        out.append({
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "private": r.get("private"),
            "open_issues": r.get("open_issues_count", 0),  # PR's + issues
            "updated_at": r.get("updated_at"),
            "description": r.get("description") or "",
        })
    return out


def list_prs(full_name):
    """Open PR's van een repo."""
    if _forbidden(full_name):
        return []
    data = _gh(f"/repos/{full_name}/pulls?state=open&per_page=30")
    return [{
        "number": p.get("number"),
        "title": p.get("title"),
        "author": (p.get("user") or {}).get("login"),
        "head": (p.get("head") or {}).get("ref"),
        "base": (p.get("base") or {}).get("ref"),
        "updated_at": p.get("updated_at"),
        "url": p.get("html_url"),
        "draft": p.get("draft", False),
    } for p in data]


def get_pr(full_name, number):
    """Detail + gewijzigde bestanden (samenvatting) van één PR."""
    if _forbidden(full_name):
        raise RuntimeError("repo buiten scope")
    p = _gh(f"/repos/{full_name}/pulls/{number}")
    files = _gh(f"/repos/{full_name}/pulls/{number}/files?per_page=100")
    return {
        "number": p.get("number"),
        "title": p.get("title"),
        "author": (p.get("user") or {}).get("login"),
        "head": (p.get("head") or {}).get("ref"),
        "base": (p.get("base") or {}).get("ref"),
        "body": (p.get("body") or "")[:4000],
        "url": p.get("html_url"),
        "additions": p.get("additions"),
        "deletions": p.get("deletions"),
        "changed_files": p.get("changed_files"),
        "files": [{"filename": f.get("filename"),
                   "additions": f.get("additions"),
                   "deletions": f.get("deletions"),
                   "status": f.get("status")} for f in files],
    }
