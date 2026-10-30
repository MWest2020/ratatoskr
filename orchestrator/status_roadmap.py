"""Per project: the phase, the roadmap and the gap to done.

Mark, 2026-10-30, on westerweel.work/nu/: "what I really want is the phase and
the roadmap, high-level, and what the gap is until it's done." Each project
keeps its roadmap as data in its own repository (`docs/reference/roadmap.yml`:
goal, phases, the current phase and what done means for it, each item with
evidence); this module reads it through GitHub and turns it into the page's
per-project row. A private repository keeps its names and statuses, never its
links.
"""
import base64

import yaml

from status_scrub import public_url

PATH = "docs/reference/roadmap.yml"
STATUSES = ("done", "open")


class BadRoadmap(ValueError):
    """A roadmap that cannot be shown truthfully: better no row than a wrong one."""


def parse(text):
    """The roadmap as a dict, checked: a current phase that exists, items with a
    known status and an evidence link."""
    doc = yaml.safe_load(text) or {}
    for key in ("project", "goal", "current", "phases", "done_means"):
        if key not in doc:
            raise BadRoadmap(f"missing `{key}`")
    ids = [p.get("id") for p in doc["phases"]]
    if doc["current"] not in ids:
        raise BadRoadmap(f"current phase `{doc['current']}` is not among {ids}")
    for item in doc["done_means"]:
        if item.get("status") not in STATUSES:
            raise BadRoadmap(f"`{item.get('item')}`: status must be one of {STATUSES}")
        if not str(item.get("evidence", "")).startswith("https://"):
            raise BadRoadmap(f"`{item.get('item')}`: evidence must be a link")
    return doc


def fetch(owner, repo, gh, run):
    """The parsed roadmap of one repository, or None when it has none (or a bad one)."""
    blob = gh(["api", f"repos/{owner}/{repo}/contents/{PATH}"], run)
    if not blob or "content" not in blob:
        return None
    try:
        return parse(base64.b64decode(blob["content"]).decode("utf-8"))
    except (BadRoadmap, yaml.YAMLError, ValueError):
        return None


def row(doc, public):
    """What the page shows for one project: goal, the phase strip, progress
    toward done for the current phase, and the gap (the open items)."""
    items = doc["done_means"]
    done = sum(1 for i in items if i["status"] == "done")
    phases, seen_current = [], False
    for p in doc["phases"]:
        current = p["id"] == doc["current"]
        phases.append({"id": p["id"], "name": p.get("name", p["id"]),
                       "summary": p.get("summary", ""),
                       "state": "current" if current else ("next" if seen_current else "past")})
        seen_current = seen_current or current
    return {"goal": doc["goal"], "phases": phases,
            "phase": next(p["name"] for p in phases if p["state"] == "current"),
            "progress": {"done": done, "total": len(items)},
            "gap": [{"item": i["item"], "url": public_url(i["evidence"], public)}
                    for i in items if i["status"] == "open"]}
