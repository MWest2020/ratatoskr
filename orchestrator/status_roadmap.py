"""Per project: the phase, the roadmap and the gap to done.

Mark, 2026-10-30, on westerweel.work/nu/: "what I really want is the phase and
the roadmap, high-level, and what the gap is until it's done." Each project
keeps its roadmap as data in its own repository (`docs/reference/roadmap.yml`:
goal, phases, the current phase and what done means for it, each item with
evidence); this module reads and checks it through GitHub. What the public
page shows of it is `status_public`'s business.

Optional, for the public page (`status_public`): `next`, two to four plain
lines of what comes next (else the open items' headlines), and `nl`, the
Dutch `goal`, `phase` and `next` for the NL page.
"""
import base64

import yaml

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
    _texts(doc.get("next"), "next")
    nl = doc.get("nl")
    if nl is not None:
        if not isinstance(nl, dict) or set(nl) - {"goal", "phase", "next"}:
            raise BadRoadmap("`nl` holds only goal, phase and next")
        for key in ("goal", "phase"):
            if key in nl and not isinstance(nl[key], str):
                raise BadRoadmap(f"`nl.{key}` must be text")
        _texts(nl.get("next"), "nl.next")
    return doc


def _texts(value, key):
    if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
        raise BadRoadmap(f"`{key}` must be a list of lines")


def fetch(owner, repo, gh, run):
    """The parsed roadmap of one repository, or None when it has none (or a bad one)."""
    blob = gh(["api", f"repos/{owner}/{repo}/contents/{PATH}"], run)
    if not blob or "content" not in blob:
        return None
    try:
        return parse(base64.b64decode(blob["content"]).decode("utf-8"))
    except (BadRoadmap, yaml.YAMLError, ValueError):
        return None
