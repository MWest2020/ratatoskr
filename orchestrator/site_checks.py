"""The checks behind the weekly site-freshness job: pure functions over page text.

Mark, 2026-10-30: his projects page still said "Boomhuis" weeks after the
rename; he asked for "a job / service that keeps it up to date". Each check
returns findings: `mechanical` ones (a rename, a moved repository link) the job
fixes in a pull request; `narrative` ones (a claim, a missing project, a stale
description) go to Mark as a question, because the text is his voice.

The old names and the parked projects live in the site's own
`data/renames.yml`, which its smoke test reads too.
"""
import re

import yaml

# A mention right after one of these is history, not a stale name.
FORMERLY = re.compile(r"(eerder|voorheen|formerly|previously|ex-)\W{0,3}$", re.I)
REPO_LINK = re.compile(r"github\.com/MWest2020/([A-Za-z0-9_.-]+?)(?=[/)\s\"'#]|$)")
PRIVATE_CLAIM = re.compile(r"\b(repo|repository|repo's|repositories)\b[^.\n]{0,40}\b(privé|private)\b|"
                           r"\b(privé|private)\b[^.\n]{0,20}\b(repo|repository)\b", re.I)
WORD = re.compile(r"[a-zà-ÿ]{5,}", re.I)


def load_renames(text):
    """(renames as [(old, new)], parked repository names) from data/renames.yml."""
    doc = yaml.safe_load(text) or {}
    renames = [(r["old"], r["new"]) for r in doc.get("renames") or [] if r.get("old")]
    return renames, [str(p) for p in doc.get("parked") or []]


def _finding(check, kind, page, line, message, **extra):
    return {"check": check, "kind": kind, "page": page, "line": line, "message": message, **extra}


def _cased(old, new, found):
    """`new` in the case of the text it replaces: Boomhuis → Ratatoskr, boomhuis → ratatoskr."""
    return new[:1].upper() + new[1:] if found[:1].isupper() else new[:1].lower() + new[1:]


def stale_names(pages, renames):
    """Old names outside a 'formerly' mention: mechanical, the fix is the new name."""
    out = []
    for page, text in pages.items():
        for n, line in enumerate(text.splitlines(), 1):
            for old, new in renames:
                for m in re.finditer(rf"(?<![\w-]){re.escape(old)}(?!\w)", line, re.I):
                    if FORMERLY.search(line[:m.start()]):
                        continue
                    out.append(_finding("stale-name", "mechanical", page, n,
                                        f"'{m.group(0)}' was renamed to {new}",
                                        old=m.group(0), new=_cased(old, new, m.group(0))))
    return out


def sections(text):
    """[(heading, first line number, body)] per `## ` section; the part before
    the first heading is section ''."""
    out, head, start, body = [], "", 1, []
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            out.append((head, start, "\n".join(body)))
            head, start, body = line[3:].strip(), n, []
        else:
            body.append(line)
    out.append((head, start, "\n".join(body)))
    return out


def repos_in(text):
    return {m.group(1).rstrip(".") for m in REPO_LINK.finditer(text)}


def visibility(pages, visible):
    """A section that calls its repository private while every repository it
    links is public (or the reverse claim is absent): narrative, a sentence to
    rewrite. `visible(repo)` gives 'PUBLIC', 'PRIVATE' or None (unknown)."""
    out = []
    for page, text in pages.items():
        for head, start, body in sections(text):
            claim = PRIVATE_CLAIM.search(body)
            linked = repos_in(body)
            if not claim or not linked:
                continue
            states = {visible(r) for r in linked}
            if states == {"PUBLIC"}:
                out.append(_finding("visibility", "narrative", page, start,
                                    f"section '{head}' says the repository is private, "
                                    f"but {', '.join(sorted(linked))} is public",
                                    quote=claim.group(0)))
    return out


def projects(pages, expected, parked, archived):
    """Projects page coverage: a current public project the page never links
    (`expected`), and a parked or archived one it still presents."""
    linked = set()
    for text in pages.values():
        linked |= {r.lower() for r in repos_in(text)}
    out = [_finding("missing-project", "narrative", "", 0,
                    f"{repo} is current work but no page links it")
           for repo in sorted(expected) if repo.lower() not in linked]
    for page, text in pages.items():
        for repo in sorted(repos_in(text)):
            if repo in parked or repo in archived:
                why = "parked" if repo in parked else "archived"
                out.append(_finding("parked-project", "narrative", page, 0,
                                    f"{repo} is {why} but the page still links it"))
    return out


def links(pages, canonical):
    """Repository links whose name moved (mechanical: the new name) or that no
    longer exist (narrative). `canonical(repo)` gives the current name or None."""
    out = []
    for page, text in pages.items():
        for repo in sorted(repos_in(text)):
            now = canonical(repo)
            if now is None:
                out.append(_finding("broken-link", "narrative", page, 0,
                                    f"github.com/MWest2020/{repo} does not exist"))
            elif now != repo:
                out.append(_finding("moved-link", "mechanical", page, 0,
                                    f"github.com/MWest2020/{repo} is now {now}",
                                    old=f"github.com/MWest2020/{repo}",
                                    new=f"github.com/MWest2020/{now}"))
    return out


def _words(text):
    return {w.lower() for w in WORD.findall(text)}


def descriptions(pages, goals, threshold=0.04):
    """A project section that shares almost no words with the project's own
    goal (roadmap.yml, repository description): narrative, worth a look."""
    out = []
    for page, text in pages.items():
        for head, start, body in sections(text):
            for repo in repos_in(body) & set(goals):
                if not head.lower().startswith(repo.lower()[:5]):
                    continue
                first = body.strip().split("\n\n")[0]
                a, b = _words(first), _words(goals[repo])
                if a and b and len(a & b) / len(a | b) < threshold:
                    out.append(_finding("description", "narrative", page, start,
                                        f"section '{head}' and the goal of {repo} share "
                                        f"almost no words; the goal reads: {goals[repo]}"))
    return out


def apply_mechanical(text, findings):
    """The page text with every mechanical fix for it applied."""
    for f in findings:
        if f["kind"] != "mechanical":
            continue
        if f["check"] == "stale-name":
            pat = rf"(?<![\w-]){re.escape(f['old'])}(?!\w)"
            text = re.sub(pat, lambda m: m.group(0) if FORMERLY.search(
                text[:m.start()].rsplit("\n", 1)[-1]) else f["new"], text)
        else:
            text = text.replace(f["old"], f["new"])
    return text
