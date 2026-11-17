# SPDX-License-Identifier: MIT
"""Which projects reach westerweel.work/nu/, and what one project shows there.

Mark, 2026-11-17: the page exposed too much. Per project it now shows the
name, a one-line goal, the current phase, progress (done/total of what "done"
means for that phase) and two to four plain "next up" lines, in the page's
language: NL at /nu/, EN at /en/now/. No change names, no issue numbers, no
links into the roadmap's evidence.

Which projects: `status_site.yml`. A project marked `private` never shows; a
private GitHub repository shows only with `show_private`; client names are
replaced unless `show_client_names` (default off).

Language: English comes from the roadmap itself. Dutch comes from an optional
`nl:` block in the roadmap (`goal`, `phase`, `next`); without it the NL page
gets a short Dutch template rather than English text: the page shows the
phase number ("fase 2 van 4", from `phase_index`/`phase_count`) and the note
"5 open punten in deze fase; de omschrijving volgt." Nothing is machine-translated: the generator calls
no translation service.
"""
import os

import yaml

from status_scrub import public_url
from status_strip import COORD, headline, mask_clients, plain

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status_site.yml")
NEXT_MAX = 4
LANGS = ("en", "nl")
TEMPLATE = {
    "en": {"open": "{k} open item{s} in this phase.", "done": "Everything in this phase is done."},
    "nl": {"open": "{k} open punt{en} in deze fase; de omschrijving volgt.", "done": "Alles van deze fase is klaar."},
}


def load(path=CONFIG):
    with open(path) as fh:
        cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("projects", {})
    cfg.setdefault("clients", [])
    cfg["show_client_names"] = bool(cfg.get("show_client_names", False))
    return cfg


def shown(name, cfg, github_public):
    """On the page or not: `private` always wins; a private (or unreadable)
    repository needs an explicit `show_private`."""
    p = cfg["projects"].get(name) or {}
    if p.get("private"):
        return False
    return bool(github_public) or bool(p.get("show_private"))


def _clean(texts, cfg, lang, rule):
    out = []
    for t in texts:
        line = rule(mask_clients(t, cfg["clients"], lang, cfg["show_client_names"]))
        if line and line not in out:
            out.append(line)
    return out


def _lang(doc, cfg, lang, open_items):
    """goal, phase, next and a note for one language; a text that is missing
    in this language is None (the page shows the phase number, never English)."""
    src = doc if lang == "en" else (doc.get("nl") or {})
    one = lambda t: (_clean([t], cfg, lang, plain) or [None])[0]  # noqa: E731
    goal = one(src.get("goal"))
    phase_name = next(p.get("name", p["id"]) for p in doc["phases"] if p["id"] == doc["current"])
    phase = one(src.get("phase") if lang == "nl" else phase_name)
    if src.get("next"):
        items = _clean(src["next"], cfg, lang, plain)
    elif lang == "en":
        items = _clean([x["item"] for x in open_items], cfg, lang, headline)
    else:
        items = []
    t, k = TEMPLATE[lang], len(open_items)
    note = None
    if not items:
        note = t["done"] if not k else t["open"].format(k=k, s="" if k == 1 else "s", en="" if k == 1 else "en")
    return {"goal": goal, "phase": phase, "next": items[:NEXT_MAX], "note": note}


def row(name, doc, cfg, public, url):
    """The page's row for one project, or None when a string would leak."""
    items = doc["done_means"]
    open_items = [x for x in items if x["status"] == "open"]
    ids = [p["id"] for p in doc["phases"]]
    i, n = ids.index(doc["current"]) + 1, len(ids)
    out = {"name": name, "url": public_url(url, public),
           "progress": {"done": len(items) - len(open_items), "total": len(items)},
           "phase_index": i, "phase_count": n}
    for lang in LANGS:
        out[lang] = _lang(doc, cfg, lang, open_items)
    return out if not leaks(out) else None


def leaks(tree):
    """True when any string in `tree` still holds a coordination marker."""
    if isinstance(tree, dict):
        return any(leaks(v) for k, v in tree.items() if k != "url")
    if isinstance(tree, list):
        return any(leaks(v) for v in tree)
    return isinstance(tree, str) and bool(COORD.search(tree))
