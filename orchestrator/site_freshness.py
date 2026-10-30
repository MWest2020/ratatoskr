#!/usr/bin/env python3
"""Keeps westerweel.work's standing pages current: a weekly job.

Mark, 2026-10-30: "I still saw boomhuis somewhere on my website. Can you put a
job / service on it that keeps it up to date." Once a week this reads the
site's standing pages (content/nl/*.md, content/en/*.md; blog posts keep the
name of their day) and checks them against facts (site_checks): old names,
private/public claims, projects missing or parked, links to repositories that
moved, descriptions far from a project's own goal.

- Mechanical fixes (a rename, a moved link) go into ONE open pull request on
  westerweel-work, branch `freshness/<date>`, never merged by the job.
- Everything else is the text in Mark's voice: one open issue labelled
  `waiting-on-mark` with the findings and `Default: the page stays as it is`.
- The findings land in ~/.local/state/ratatoskr/site-freshness.json, which
  status_digest reads into Mark's daily mail.

`--dry-run` prints the findings and touches nothing.
"""
import datetime
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_checks  # noqa: E402
import status_roadmap  # noqa: E402
from status_scrub import clean_tree  # noqa: E402

OWNER = "MWest2020"
SITE_REPO = f"{OWNER}/westerweel-work"
SITE = os.path.expanduser(os.environ.get("SITE_FRESHNESS_DIR", "~/.worktrees/westerweel-freshness"))
STATE = os.path.expanduser("~/.local/state/ratatoskr/site-freshness.json")
PROJECTS = ["wordsworth", "ratatoskr", "habitat", "handbook", "homelab", "convergence"]
ISSUE_TITLE = "Site freshness: text on westerweel.work to look at"
LABEL = "waiting-on-mark"
GIT = ["git", "-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com"]


def sh(args, run=subprocess.run, cwd=None):
    p = run(args, capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def gh_json(args, run=subprocess.run):
    code, out, _ = sh(["gh", *args], run)
    try:
        return json.loads(out) if code == 0 and out else None
    except json.JSONDecodeError:
        return None


def checkout(run=subprocess.run):
    """A clean copy of the site's main branch."""
    if not os.path.isdir(os.path.join(SITE, ".git")):
        sh(["gh", "repo", "clone", SITE_REPO, SITE, "--", "-q"], run)
    for args in (["fetch", "-q", "origin"], ["checkout", "-q", "main"],
                 ["reset", "-q", "--hard", "origin/main"]):
        sh(["git", *args], run, SITE)


def pages():
    out = {}
    for path in sorted(glob.glob(os.path.join(SITE, "content", "*", "*.md"))):
        with open(path, encoding="utf-8") as fh:
            out[os.path.relpath(path, SITE)] = fh.read()
    return out


def repo_facts(names, run=subprocess.run):
    """{repo: {visibility, archived, name}} as GitHub has it now; None = gone."""
    facts = {}
    for repo in names:
        facts[repo] = gh_json(["repo", "view", f"{OWNER}/{repo}", "--json",
                               "name,visibility,isArchived,description"], run)
    return facts


def findings(run=subprocess.run):
    with open(os.path.join(SITE, "data", "renames.yml"), encoding="utf-8") as fh:
        renames, parked = site_checks.load_renames(fh.read())
    texts = pages()
    linked = set().union(*(site_checks.repos_in(t) for t in texts.values())) if texts else set()
    facts = repo_facts(sorted(linked | set(PROJECTS)), run)
    public = [r for r in PROJECTS if (facts.get(r) or {}).get("visibility") == "PUBLIC"]
    goals = {}
    for repo in public:
        road = status_roadmap.fetch(OWNER, repo, lambda a, r: gh_json(a, r), run)
        goals[repo] = " ".join(filter(None, [(road or {}).get("goal"),
                                             (facts.get(repo) or {}).get("description")]))
    archived = {r for r, f in facts.items() if f and f.get("isArchived")}
    return (site_checks.stale_names(texts, renames)
            + site_checks.visibility(texts, lambda r: (facts.get(r) or {}).get("visibility"))
            + site_checks.projects(texts, public, set(parked), archived)
            + site_checks.links(texts, lambda r: (facts.get(r) or {}).get("name"))
            # goals are English: compare them with the English pages only
            + site_checks.descriptions({p: t for p, t in texts.items()
                                        if p.startswith(os.path.join("content", "en"))}, goals))


def open_pr(found, today, run=subprocess.run):
    """Mechanical fixes in one open PR (an existing freshness PR is updated)."""
    mech = [f for f in found if f["kind"] == "mechanical"]
    if not mech:
        return None
    prs = gh_json(["pr", "list", "--repo", SITE_REPO, "--state", "open", "--json",
                   "headRefName,url"], run) or []
    pr = next((p for p in prs if p["headRefName"].startswith("freshness/")), None)
    branch = pr["headRefName"] if pr else f"freshness/{today}"
    sh(["git", "checkout", "-q", "-B", branch], run, SITE)
    for page in sorted({f["page"] for f in mech if f["page"]}):
        path = os.path.join(SITE, page)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        mine = [f for f in mech if f["page"] == page]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(site_checks.apply_mechanical(text, mine))
    code, _, _ = sh(["git", "diff", "--quiet"], run, SITE)
    if code == 0:
        return pr["url"] if pr else None
    msg = "freshness: mechanical fixes (site_freshness.py)\n\n" + "\n".join(
        f"- {f['page']}:{f['line']} {f['message']}" for f in mech)
    sh([*GIT, "commit", "-qam", msg], run, SITE)
    sh(["git", "push", "-q", "-f", "-u", "origin", branch], run, SITE)
    if pr:
        return pr["url"]
    body = ("Weekly site-freshness job (ratatoskr `orchestrator/site_freshness.py`): "
            "mechanical fixes only. Not merged by the job.\n\n" + "\n".join(
                f"- `{f['page']}`:{f['line']} {f['message']}" for f in mech))
    _, out, _ = sh(["gh", "pr", "create", "--repo", SITE_REPO, "--head", branch,
                    "--title", f"freshness: {len(mech)} mechanical fix(es)", "--body", body], run)
    return out.splitlines()[-1] if out else None


def open_issue(found, run=subprocess.run):
    """The narrative findings in one open waiting-on-mark issue (kept up to date)."""
    narr = [f for f in found if f["kind"] == "narrative"]
    issues = gh_json(["issue", "list", "--repo", SITE_REPO, "--state", "open", "--label", LABEL,
                      "--json", "number,title,url"], run) or []
    mine = next((i for i in issues if i["title"] == ISSUE_TITLE), None)
    if not narr:
        if mine:
            sh(["gh", "issue", "close", str(mine["number"]), "--repo", SITE_REPO, "--comment",
                "The weekly check finds nothing to look at any more."], run)
        return None
    body = ("The weekly site-freshness job found text on the site that may no longer be true. "
            "Each line is a suggestion; the wording is yours.\n\n" + "\n".join(
                f"- `{f['page'] or '(site)'}`{':' + str(f['line']) if f['line'] else ''} "
                f"{f['message']}" for f in narr)
            + "\n\nDefault: the page stays as it is.")
    if mine:
        sh(["gh", "issue", "edit", str(mine["number"]), "--repo", SITE_REPO, "--body", body], run)
        return mine["url"]
    sh(["gh", "label", "create", LABEL, "--repo", SITE_REPO, "--color", "D93F0B",
        "--description", "A decision only Mark can take"], run)
    _, out, _ = sh(["gh", "issue", "create", "--repo", SITE_REPO, "--title", ISSUE_TITLE,
                    "--label", LABEL, "--body", body], run)
    return out.splitlines()[-1] if out else None


def main(argv=sys.argv[1:], run=subprocess.run):
    now = datetime.datetime.now(datetime.timezone.utc)
    checkout(run)
    found = clean_tree(findings(run))
    if "--dry-run" in argv:
        print(json.dumps(found, indent=1, ensure_ascii=False))
        return 0
    state = {"generated": now.isoformat(timespec="seconds"), "findings": found,
             "pr": open_pr(found, now.strftime("%Y-%m-%d"), run), "issue": open_issue(found, run)}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, ensure_ascii=False)
    os.replace(STATE + ".tmp", STATE)
    sh(["git", "checkout", "-q", "main"], run, SITE)
    print(f"site freshness: {len(found)} finding(s); pr={state['pr']} issue={state['issue']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
