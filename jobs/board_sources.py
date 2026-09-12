#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""De bronnen van het werk-overzicht: clones, GitHub en lopende werksessies.

Apart van board.py omdat dit de onzuivere kant is — glob, subprocess, netwerk —
en omdat beide bestanden anders over de 200 regels gaan.

Elke bron die faalt gooit; `board.build` vangt dat en zet het als LEESFOUT in de
momentopname. Stil een lege lijst teruggeven is precies het verschil tussen
"er is niets te doen" en "ik kon niet kijken".
"""
import glob
import json
import os
import subprocess
import time

from board_model import DAY, age_days, pr_column


def repo_url(clone_dir):
    """De GitHub-URL van een clone, uit zijn eigen remote. Niet raden op de
    mapnaam: een kaart die naar een 404 wijst is erger dan een kaart zonder link."""
    try:
        p = subprocess.run(["git", "-C", clone_dir, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    ref = (p.stdout or "").strip()
    if p.returncode != 0 or "github.com" not in ref:
        return ""
    pad = ref.split("github.com", 1)[1].lstrip(":/").removesuffix(".git")
    return "https://github.com/" + pad


def openspec_cards(pattern, now):
    """Elke niet-gearchiveerde change is een voorstel. De ouderdom komt van de
    mtime van proposal.md — dat is wanneer er voor het laatst aan gewerkt is."""
    cards = []
    urls = {}
    for path in glob.glob(pattern):
        if "/archive/" in path:
            continue
        change = os.path.basename(os.path.dirname(path))
        repo = path.split("/home/agent/", 1)[-1].split("/openspec/", 1)[0]
        try:
            ts = os.path.getmtime(path)
        except OSError:
            continue
        clone = path.split("/openspec/", 1)[0]
        if clone not in urls:
            urls[clone] = repo_url(clone)
        # Doorlinken naar de change zelf, niet naar de repo: je wilt de tekst zien,
        # niet de voorpagina. `branch` kan afwijken; main is bij ons de waarheid.
        base = urls[clone]
        url = f"{base}/tree/main/openspec/changes/{change}" if base else ""
        cards.append({"id": f"openspec:{repo}:{change}", "repo": repo,
                      "title": change, "column": "proposal",
                      "age_days": age_days(ts, now), "who": "", "url": url,
                      "source": path.replace("/home/agent/", "~/")})
    return cards


def gh_json(args):
    """`gh` aanroepen. Een fout is een LEESFOUT, geen lege lijst: stil niets
    tonen is niet te onderscheiden van 'er is niets', en dat is precies het
    verschil dat je wilt zien."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:160])
    return json.loads(p.stdout or "[]")


def pr_cards(owner, merged_days, now, ignore=()):
    velden = "repository,number,title,url,isDraft,updatedAt,author"
    rows = gh_json(["search", "prs", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", velden])
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - merged_days * DAY))
    rows += [dict(r, merged=True) for r in gh_json(
        ["search", "prs", f"--owner={owner}", f"merged:>={cutoff}",
         "--limit", "40", "--json", velden])]
    cards = []
    for r in rows:
        if r["repository"]["name"] in ignore:
            continue
        pr = {"merged": r.get("merged", False), "draft": r.get("isDraft")}
        ts = time.mktime(time.strptime(r["updatedAt"][:19], "%Y-%m-%dT%H:%M:%S"))
        cards.append({"id": f"pr:{r['repository']['name']}:{r['number']}",
                      "repo": r["repository"]["name"],
                      "title": f"#{r['number']} {r['title']}",
                      "column": pr_column(pr), "age_days": age_days(ts, now),
                      "who": (r.get("author") or {}).get("login", ""),
                      "url": r.get("url", ""), "source": ""})
    return cards


def session_cards(runs_dir, now):
    """Een werksessie draait nog zolang er geen `result`-regel in het runbestand
    staat. Klaar is klaar: die verdwijnt van het bord, hij staat in het kanaal."""
    cards = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.jsonl"))):
        try:
            inhoud = open(path, errors="ignore").read()
            ts = os.path.getmtime(path)
        except OSError:
            continue
        if '"type":"result"' in inhoud.replace(" ", ""):
            continue
        naam = os.path.basename(path).rsplit("-", 1)[0]
        typ, _, wie = naam.partition("-")
        # Een sessie heeft geen URL maar wel een KANAAL: daar praat hij. De app
        # springt daarheen in plaats van een dode kaart te tonen.
        kanaal = ""
        try:
            eerste = json.loads(inhoud.splitlines()[0])
            if eerste.get("type") == "boomhuis_sessie":
                kanaal, wie = eerste.get("kanaal", ""), eerste.get("requester", wie)
        except (ValueError, IndexError):
            pass
        cards.append({"id": "session:" + os.path.basename(path),
                      "repo": "werksessie", "title": f"{typ} · {wie}",
                      "column": "building", "age_days": age_days(ts, now),
                      "who": wie, "url": "", "channel": kanaal, "source": path})
    return cards
