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
    path = ref.split("github.com", 1)[1].lstrip(":/").removesuffix(".git")
    return "https://github.com/" + path


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
                      "title": change, "column": "proposal", "via": "openspec",
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
    fields = "repository,number,title,url,isDraft,updatedAt,author"
    rows = gh_json(["search", "prs", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", fields])
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - merged_days * DAY))
    rows += [dict(r, merged=True) for r in gh_json(
        ["search", "prs", f"--owner={owner}", f"merged:>={cutoff}",
         "--limit", "40", "--json", fields])]
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


def last_activity(content):
    """De laatste tool-aanroep uit een runbestand, kort. Een lopende sessie die
    alleen "bezig" zegt is een voortgangsbalk zonder balk."""
    last = ""
    for line in content.splitlines():
        if '"tool_use"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        for c in (ev.get("message") or {}).get("content", []):
            if c.get("type") == "tool_use":
                target = ""
                for k in ("file_path", "path", "pattern", "command"):
                    if c.get("input", {}).get(k):
                        target = str(c["input"][k])[-40:]
                        break
                last = f"{c.get('name')} {target}".strip()
    return last


def session_cards(runs_dir, now):
    """Een werksessie draait nog zolang er geen `result`-regel in het runbestand
    staat. Klaar is klaar: die verdwijnt van het bord, hij staat in het kanaal."""
    cards = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.jsonl"))):
        try:
            content = open(path, errors="ignore").read()
            ts = os.path.getmtime(path)
        except OSError:
            continue
        if '"type":"result"' in content.replace(" ", ""):
            continue
        name = os.path.basename(path).rsplit("-", 1)[0]
        typ, _, who = name.partition("-")
        # Een sessie heeft geen URL maar wel een KANAAL: daar praat hij. De app
        # springt daarheen in plaats van een dode kaart te tonen.
        channel, writes = "", False
        try:
            first = json.loads(content.splitlines()[0])
            if first.get("type") == "boomhuis_session":
                channel = first.get("channel", "")
                who = first.get("requester", who)
                writes = bool(first.get("writes"))
        except (ValueError, IndexError):
            pass
        # Waar hij mee bezig is: de laatste tool-aanroep in het runbestand. Zonder
        # dit is een lopende sessie een kaart die niets zegt, en dat is precies
        # wat Mark miste: "tijdens bouwen verwacht ik updates".
        cards.append({"id": "session:" + os.path.basename(path),
                      "repo": "werksessie", "title": f"{typ} · {who}",
                      "column": "building",
                      "via": "session (writes)" if writes else "session",
                      "age_days": age_days(ts, now), "activity": last_activity(content),
                      "who": who, "url": "", "channel": channel, "source": path})
    return cards
