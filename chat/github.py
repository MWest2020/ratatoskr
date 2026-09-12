"""GitHub read layer for the PWA (repo/PR view). Stdlib only (urllib).

Token from env GITHUB_TOKEN (a tailnet-only .env on the host, never in git). The
scope is deliberately limited to MWest2020's own repos; a hard safety net filters
out everything that smells of the employer org (it stays out of view).
"""
import base64
import json
import re
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


def get_file(path, repo=f"{OWNER}/boomhuis"):
    """File content from a repo (boomhuis by default) through the contents API.
    For the 'pinned context' (knowledge/<channel>.md). Returns "" when missing."""
    if _forbidden(repo):
        return ""
    try:
        d = _gh(f"/repos/{repo}/contents/{path}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise
    if isinstance(d, dict) and d.get("encoding") == "base64":
        return base64.b64decode(d.get("content", "")).decode("utf-8", "replace")
    return ""


# owner/name, GitHub character set. Without this check "boomhuis" (without an
# owner) went through to the API and the 404 came back as a 502 with raw upstream
# text — an input error posing as an outage.
# Every segment starts with an alphanumeric character: otherwise ".." and "."
# slip through and a path-like value ends up in the GitHub URL.
_SEG = r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"
_REPO_RE = re.compile(rf"^{_SEG}/{_SEG}$")


def valid_repo(name):
    return bool(name) and bool(_REPO_RE.match(name))


def list_repos(limit=30):
    """Own repos (owner), newest first; the employer org filtered out."""
    data = _gh(f"/user/repos?affiliation=owner&sort=updated&per_page={limit}")
    out = []
    for r in data:
        if _forbidden(r.get("full_name")):
            continue
        out.append({
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "private": r.get("private"),
            "open_issues": r.get("open_issues_count", 0),  # PRs + issues
            "updated_at": r.get("updated_at"),
            "description": r.get("description") or "",
        })
    return out


def list_prs(full_name):
    """Open PRs of a repo."""
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
    """Detail and changed files (summary) of one PR."""
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
