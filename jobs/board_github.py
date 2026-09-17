# SPDX-License-Identifier: MIT
"""Wat GitHub het bord vertelt: open en gemergede PR's, en open issues.

Apart van `board_sources` omdat dat bestand drie verschillende werelden bevatte
-- de schijf (OpenSpec-changes), GitHub, en de runbestanden van sessies -- en de
GitHub-kant de enige is die een netwerkaanroep doet en dus een leesfout kent.
Die grens is ook waar de bestandsgrens van 200 regels om vroeg.
"""
from __future__ import annotations

import json
import subprocess
import time

from board_model import DAY, age_days, pr_column

def gh_json(args):
    """Call `gh`. An error is a READ ERROR, not an empty list: showing nothing
    silently is indistinguishable from 'there is nothing'."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:160])
    return json.loads(p.stdout or "[]")


FIELDS = "repository,number,title,url,isDraft,updatedAt,author"


def open_prs(owner):
    """Wat nog aandacht vraagt — apart van `merged_prs`, want deze kant moet VERS
    zijn. Een gemergede PR die nog in 'review' staat vraagt om niets, en een
    kolom met zulke kaarten lees je niet meer. Gemeten 2026-09-13: #125 stond
    acht minuten na zijn merge nog in review, uit een cache van vlak ervóór."""
    return gh_json(["search", "prs", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", FIELDS])


def merged_prs(owner, merged_days, now):
    """Geschiedenis: verandert alleen naar achteren, mag dus uit een cache."""
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - merged_days * DAY))
    return [dict(r, merged=True) for r in gh_json(
        ["search", "prs", f"--owner={owner}", f"merged:>={cutoff}",
         "--limit", "40", "--json", FIELDS])]


ISSUE_FIELDS = "repository,number,title,url,updatedAt,labels"


def issue_rows(owner):
    """De ruwe rijen; apart van het kaartjes maken zodat ze gecacht kunnen
    worden zoals de gemergede PR's. Issues veranderen langzaam en mogen het bord
    niet elke twee minuten een GitHub-aanroep kosten."""
    return gh_json(["search", "issues", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", ISSUE_FIELDS])


def issues_to_cards(rows, now, ignore=()):
    """Open issues: het werk dat nog geen voorstel is.

    Het bord kende tot nu toe alleen dingen die al in beweging waren — een
    voorstel, een PR, een sessie. Wat nog niet begonnen is stond nergens, en dus
    stond de helft van de afspraak ("klein = issue, epic = spec") buiten beeld.

    Het label reist mee in de titel, want het verschil tussen `spec-nodig` en
    `direct` bepaalt wat je met de kaart moet doen en dat wil je zien zonder
    hem open te klikken.
    """
    cards = []
    for r in rows:
        if r["repository"]["name"] in ignore:
            continue
        labels = [l["name"] for l in (r.get("labels") or [])]
        merk = next((l for l in ("spec-nodig", "direct") if l in labels), "")
        ts = time.mktime(time.strptime(r["updatedAt"][:19], "%Y-%m-%dT%H:%M:%S"))
        cards.append({"id": f"issue:{r['repository']['name']}:{r['number']}",
                      "repo": r["repository"]["name"],
                      "title": f"#{r['number']} {r['title']}"
                               + (f"  [{merk}]" if merk else ""),
                      "column": "backlog", "via": "issue",
                      "age_days": age_days(ts, now), "who": "",
                      "url": r.get("url", ""), "source": ""})
    return cards


def rows_to_cards(rows, now, ignore=()):
    cards = []
    for r in rows:
        if r["repository"]["name"] in ignore:
            continue
        pr = {"merged": r.get("merged", False), "draft": r.get("isDraft")}
        ts = time.mktime(time.strptime(r["updatedAt"][:19], "%Y-%m-%dT%H:%M:%S"))
        cards.append({"id": f"pr:{r['repository']['name']}:{r['number']}",
                      "repo": r["repository"]["name"],
                      "title": f"#{r['number']} {r['title']}",
                      "column": pr_column(pr), "via": "pull request",
                      "age_days": age_days(ts, now),
                      "who": (r.get("author") or {}).get("login", ""),
                      "url": r.get("url", ""), "source": ""})
    return cards


def pr_cards(owner, merged_days, now, ignore=()):
    """Beide kanten in één keer; het bord haalt ze apart op."""
    return rows_to_cards(open_prs(owner) + merged_prs(owner, merged_days, now),
                         now, ignore)
